"""Inject API — what dms-edge (or scripts/seed_demo.py, standing in for it) pushes events/evidence to."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import config, schemas
from app.api.fleet_api import serialize_alert_summary
from app.api.websocket import manager
from app.db import models
from app.db.database import get_db
from app.db.models import utcnow
from app.notifications import notifier
from app.notifications.notifier import SEVERITY_PRIORITY
from app.rule_agents import violation_rules

router = APIRouter(prefix="/api", tags=["inject"])

# violation_type -> (rule_id, rule_name) for edge-computed violations — matches
# dms-edge/agents/violation_detection_agent.py's own rule_id/rule_name so the
# dashboard shows the same rule identity regardless of which path (edge or
# fallback) produced the violation.
EDGE_RULE_META = {
    "DROWSINESS_PATTERN": ("drowsiness_3in2min", "3 Drowsiness Events in 2 Minutes"),
    "PHONE_USAGE": ("phone_usage_conf_gt_0.85", "Phone Usage Detected (confidence > 0.85)"),
    "DISTRACTION_PATTERN": ("distraction_2in1min", "2 Distraction Events in 1 Minute"),
    "CONTINUOUS_DRIVE": ("continuous_drive_gt_4h", "Continuous Drive Exceeds 4 Hours"),
}


def _get_or_create_vehicle(
    db: Session, ctx: schemas.ContextIn, vehicle_in: schemas.VehicleIn
) -> models.Vehicle:
    vehicle = (
        db.query(models.Vehicle).filter(models.Vehicle.registration == ctx.vehicle_registration).first()
    )
    if vehicle is None:
        vehicle = models.Vehicle(
            registration=ctx.vehicle_registration,
            vehicle_type=vehicle_in.vehicle_type or "18-wheeler box truck",
            region=vehicle_in.region,
            route_default=ctx.route,
        )
        db.add(vehicle)
        db.flush()
    return vehicle


def _get_or_create_driver(db: Session, ctx: schemas.ContextIn) -> models.Driver | None:
    if not ctx.driver_code:
        return None
    driver = db.query(models.Driver).filter(models.Driver.driver_code == ctx.driver_code).first()
    if driver is None:
        driver = models.Driver(driver_code=ctx.driver_code, name=ctx.driver_name)
        db.add(driver)
        db.flush()
    return driver


@router.post("/events", response_model=schemas.EventCreateResponse)
async def receive_event(payload: schemas.EventIn, db: Session = Depends(get_db)):
    existing = db.query(models.Event).filter(models.Event.event_id == payload.event_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="event_id already exists")

    vehicle = _get_or_create_vehicle(db, payload.context, payload.vehicle)
    driver = _get_or_create_driver(db, payload.context)

    vehicle.last_seen_at = utcnow()
    if payload.device.edge_device_status:
        vehicle.edge_device_status = payload.device.edge_device_status
    if payload.device.firmware_version:
        vehicle.firmware_version = payload.device.firmware_version
    if payload.device.device_id:
        vehicle.edge_device_id = payload.device.device_id

    event = models.Event(
        event_id=payload.event_id,
        timestamp=payload.timestamp,
        type=payload.detection.type,
        confidence=payload.detection.confidence,
        metrics_json=payload.detection.metrics,
        vehicle_id=vehicle.id,
        driver_id=driver.id if driver else None,
        trip_id=payload.context.trip_id,
        route=payload.context.route,
        shift_label=payload.context.shift_label,
        trip_started_at=payload.context.trip_started_at,
        elapsed_trip_seconds=payload.context.elapsed_trip_seconds,
        speed_kmh=payload.vehicle.speed_kmh,
        is_moving=payload.vehicle.is_moving,
        lat=payload.context.lat,
        lon=payload.context.lon,
        distance_to_waypoint_km=payload.context.distance_to_waypoint_km,
        waypoint_name=payload.context.waypoint_name,
        camera_id=payload.context.camera_id,
        frame_index=payload.context.frame_index,
        device_id=payload.device.device_id,
        processing_time_ms=payload.device.processing_time_ms,
    )
    db.add(event)
    db.flush()

    # Edge-equipped vehicles already decided violations locally (POST /api/violations,
    # below) — re-deriving here would risk a duplicate/conflicting violation. This is
    # the fallback path now: only vehicles with no edge device get evaluated here.
    violation, is_new = (None, False) if vehicle.edge_device_id is not None else violation_rules.evaluate_event(
        db, event
    )

    violations_triggered: list[str] = []
    alert_payload = None
    if violation is not None:
        notifier.upsert_alarm(db, violation, event, is_new)
        violations_triggered.append(violation.violation_id)
        alert_payload = {
            "type": notifier.build_alert_created_or_updated_type(is_new),
            "alert": serialize_alert_summary(db, violation),
        }

    db.commit()

    if alert_payload:
        await manager.broadcast(alert_payload)

    return schemas.EventCreateResponse(event_id=event.event_id, violations_triggered=violations_triggered)


@router.post("/violations", response_model=schemas.ViolationCreateResponse)
async def receive_violation(payload: schemas.ViolationIn, db: Session = Depends(get_db)):
    """Ingest an already-computed Violation (+ Alarm) from dms-edge's Cloud Hub
    Agent — the primary detection path now. Upserts using the same "growing
    violations" semantics as the fallback rule engine (an update to an existing
    ACTIVE violation of the same type, not a duplicate) and broadcasts exactly
    like the fallback path does today."""
    vehicle = _get_or_create_vehicle(db, payload.context, payload.vehicle)
    vehicle.last_seen_at = utcnow()

    existing = (
        db.query(models.Violation).filter(models.Violation.violation_id == payload.violation_id).first()
    )
    is_new = existing is None

    rule_id, rule_name = EDGE_RULE_META.get(
        payload.violation_type, (f"edge_{payload.violation_type.lower()}", payload.violation_type)
    )
    violation = existing or models.Violation(
        violation_id=payload.violation_id,
        violation_type=payload.violation_type,
        rule_id=rule_id,
        rule_name=rule_name,
    )
    violation.vehicle_id = vehicle.id
    violation.severity = payload.severity
    violation.status = payload.status
    violation.trigger_event_ids_json = payload.trigger_event_ids
    violation.event_count = payload.event_count
    violation.first_event_timestamp = payload.first_event_timestamp
    violation.last_event_timestamp = payload.last_event_timestamp
    violation.recommended_action_text = payload.recommended_action_text
    db.add(violation)
    db.flush()

    alarm = db.query(models.Alarm).filter(models.Alarm.violation_id == violation.violation_id).first()
    alarm = alarm or models.Alarm(
        alarm_id=f"alarm_{uuid.uuid4().hex[:12]}",
        violation_id=violation.violation_id,
        alarm_type=f"{violation.violation_type}_ALERT",
        audience="DRIVER",
    )
    alarm.timestamp = payload.alarm.fired_at
    alarm.severity = violation.severity
    alarm.message = payload.alarm.message
    alarm.priority = SEVERITY_PRIORITY.get(violation.severity, 3)
    alarm.buzzer_fired_at = payload.alarm.fired_at
    alarm.driver_ack_latency_seconds = payload.alarm.driver_ack_latency_seconds
    alarm.speed_before_kmh = payload.alarm.speed_before_kmh
    alarm.speed_after_kmh = payload.alarm.speed_after_kmh
    alarm.status = "PENDING_ACK"
    db.add(alarm)

    db.commit()

    await manager.broadcast(
        {
            "type": notifier.build_alert_created_or_updated_type(is_new),
            "alert": serialize_alert_summary(db, violation),
        }
    )

    return schemas.ViolationCreateResponse(violation_id=violation.violation_id, status="stored")


@router.post("/evidence")
async def upload_evidence(
    event_id: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)
):
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    is_video = ext in {"mp4", "mov", "avi"}
    target_dir = config.EVIDENCE_VIDEOS_DIR if is_video else config.EVIDENCE_IMAGES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    dest_path = target_dir / f"{event_id}.{ext or ('mp4' if is_video else 'jpg')}"

    content = await file.read()
    dest_path.write_bytes(content)

    evidence = db.query(models.Evidence).filter(models.Evidence.event_id == event_id).first()
    if evidence is None:
        evidence = models.Evidence(event_id=event_id, captured_at=event.timestamp)

    if is_video:
        evidence.video_path = str(dest_path)
    else:
        evidence.image_path = str(dest_path)
    evidence.sync_status = "SYNCED"

    db.add(evidence)
    db.commit()

    return {"status": "stored", "filename": dest_path.name}
