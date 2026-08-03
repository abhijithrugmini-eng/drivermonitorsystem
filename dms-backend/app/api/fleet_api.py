"""Fleet API — REST endpoints the dms-ui dashboard consumes (vehicles, alerts, actions, evidence)."""

import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import config, schemas
from app.api.websocket import manager
from app.db import models
from app.db.database import get_db

router = APIRouter(prefix="/api", tags=["fleet"])

VIOLATION_ICON = {
    "DROWSINESS_PATTERN": "😴",
    "PHONE_USAGE": "📱",
    "DISTRACTION_PATTERN": "👀",
    "CONTINUOUS_DRIVE": "🕐",
}

VIOLATION_LABEL = {
    "DROWSINESS_PATTERN": "Drowsiness",
    "PHONE_USAGE": "Phone usage",
    "DISTRACTION_PATTERN": "Distraction",
    "CONTINUOUS_DRIVE": "Continuous drive",
}


def _primary_event(db: Session, violation: models.Violation) -> models.Event | None:
    if not violation.primary_evidence_event_id:
        return None
    return (
        db.query(models.Event)
        .filter(models.Event.event_id == violation.primary_evidence_event_id)
        .first()
    )


def _evidence_urls(event: models.Event | None) -> dict:
    if event is None or event.evidence is None:
        return {"image_url": None, "video_url": None, "sync_status": "PENDING"}
    ev = event.evidence
    return {
        "image_url": f"/api/evidence/{Path(ev.image_path).name}" if ev.image_path else None,
        "video_url": f"/api/evidence/{Path(ev.video_path).name}" if ev.video_path else None,
        "sync_status": ev.sync_status,
    }


def _time_ago(timestamp: float | None) -> str:
    if not timestamp:
        return "—"
    delta = max(0, time.time() - timestamp)
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta // 60)} min ago"
    return f"{int(delta // 3600)}h ago"


def serialize_alert_summary(db: Session, violation: models.Violation) -> dict:
    event = _primary_event(db, violation)
    vehicle = violation.vehicle
    return {
        "id": violation.violation_id,
        "violation_type": violation.violation_type,
        "label": VIOLATION_LABEL.get(violation.violation_type, violation.violation_type),
        "icon": VIOLATION_ICON.get(violation.violation_type, "⚠"),
        "severity": violation.severity,
        "status": violation.status,
        "vehicle_registration": vehicle.registration if vehicle else None,
        "route": (event.route if event else None) or (vehicle.route_default if vehicle else None),
        "event_count": violation.event_count,
        "last_event_timestamp": violation.last_event_timestamp,
        "time_ago": _time_ago(violation.last_event_timestamp),
        "acknowledged": violation.status != "ACTIVE",
        "driver_ack_latency_seconds": violation.alarm.driver_ack_latency_seconds if violation.alarm else None,
    }


def serialize_alert_detail(db: Session, violation: models.Violation) -> dict:
    event = _primary_event(db, violation)
    vehicle = violation.vehicle
    driver = violation.driver
    alarm = violation.alarm

    return {
        **serialize_alert_summary(db, violation),
        "trip_details": {
            "driver_name": driver.name if driver and driver.name else "Unknown driver",
            "driver_id": driver.driver_id if driver else None,
            "route": (event.route if event else None) or (vehicle.route_default if vehicle else None),
            "shift_label": event.shift_label if event else None,
            "speed_at_event_kmh": event.speed_kmh if event else None,
            "trip_started_at": event.trip_started_at if event else None,
            "elapsed_trip_seconds": event.elapsed_trip_seconds if event else None,
        },
        "evidence": {
            **_evidence_urls(event),
            "severity": violation.severity,
            "frame_window": (
                f"{violation.event_count} events / "
                f"{round((violation.time_window_seconds or 0) / 60, 1)} min"
            ),
            "captured_at": event.timestamp if event else None,
        },
        "location": {
            "lat": event.lat if event else None,
            "lon": event.lon if event else None,
            "waypoint_name": event.waypoint_name if event else None,
            "distance_to_waypoint_km": event.distance_to_waypoint_km if event else None,
        },
        "vehicle_details": {
            "registration": vehicle.registration if vehicle else None,
            "vehicle_type": vehicle.vehicle_type if vehicle else None,
            "edge_device_status": vehicle.edge_device_status if vehicle else None,
            "firmware_version": vehicle.firmware_version if vehicle else None,
        },
        "in_cabin_response": {
            "buzzer_fired_at": alarm.buzzer_fired_at if alarm else None,
            "driver_ack_latency_seconds": alarm.driver_ack_latency_seconds if alarm else None,
            "speed_before_kmh": alarm.speed_before_kmh if alarm else None,
            "speed_after_kmh": alarm.speed_after_kmh if alarm else None,
            "alarm_message": alarm.message if alarm else None,
        },
        "recommended_action": {
            "text": violation.recommended_action_text,
            "advisory_sent_at": (
                violation.advisory_sent_at.isoformat() if violation.advisory_sent_at else None
            ),
            "advisory_message": violation.advisory_message,
        },
    }


@router.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(models.Vehicle).all()
    return [
        {
            "id": v.id,
            "registration": v.registration,
            "vehicle_type": v.vehicle_type,
            "region": v.region,
            "edge_device_status": v.edge_device_status,
        }
        for v in vehicles
    ]


@router.get("/alerts")
def list_alerts(status: str = "active", db: Session = Depends(get_db)):
    query = db.query(models.Violation)
    if status == "active":
        query = query.filter(models.Violation.status == "ACTIVE")
    elif status != "all":
        query = query.filter(models.Violation.status == status.upper())
    violations = query.order_by(models.Violation.updated_at.desc()).all()
    return [serialize_alert_summary(db, v) for v in violations]


@router.get("/alerts/{violation_id}")
def get_alert(violation_id: str, db: Session = Depends(get_db)):
    violation = db.query(models.Violation).filter(models.Violation.violation_id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return serialize_alert_detail(db, violation)


@router.post("/alerts/{violation_id}/acknowledge")
async def acknowledge_alert(
    violation_id: str, payload: schemas.AcknowledgeIn, db: Session = Depends(get_db)
):
    violation = db.query(models.Violation).filter(models.Violation.violation_id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="alert not found")

    violation.status = "ACKNOWLEDGED"
    violation.acknowledged_at = datetime.now(timezone.utc)
    violation.acknowledged_by = payload.acknowledged_by
    db.commit()

    await manager.broadcast({"type": "alert_updated", "alert": serialize_alert_summary(db, violation)})
    return serialize_alert_detail(db, violation)


@router.post("/alerts/{violation_id}/advisory")
async def send_advisory(violation_id: str, payload: schemas.AdvisoryIn, db: Session = Depends(get_db)):
    violation = db.query(models.Violation).filter(models.Violation.violation_id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="alert not found")

    violation.advisory_sent_at = datetime.now(timezone.utc)
    violation.advisory_message = payload.message or violation.recommended_action_text
    db.commit()

    await manager.broadcast({"type": "alert_updated", "alert": serialize_alert_summary(db, violation)})
    return serialize_alert_detail(db, violation)


@router.get("/evidence/{filename}")
def get_evidence(filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    target_dir = config.EVIDENCE_VIDEOS_DIR if ext in {"mp4", "mov", "avi"} else config.EVIDENCE_IMAGES_DIR
    path = target_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="evidence not found")
    return FileResponse(path)
