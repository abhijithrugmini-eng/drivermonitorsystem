"""Turns a violation into an Alarm row + simulated driver-response telemetry + a logged notification.

No real edge device exists to report buzzer/ack telemetry, so in-cabin response fields are
simulated at violation create/update time for demo polish (see plan's "Decisions" section).
"""

import logging
import random
import uuid

from sqlalchemy.orm import Session

from app.db import models

logger = logging.getLogger("dms_backend.notifications")

ALARM_MESSAGES = {
    "DROWSINESS_PATTERN": "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
    "PHONE_USAGE": "⚠️ PHONE USAGE DETECTED. EYES ON THE ROAD.",
    "DISTRACTION_PATTERN": "⚠️ DISTRACTION DETECTED. STAY FOCUSED.",
    "CONTINUOUS_DRIVE": "⚠️ CONTINUOUS DRIVING > 4 HOURS. TAKE A BREAK.",
}

SEVERITY_PRIORITY = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}


def upsert_alarm(db: Session, violation: models.Violation, event: models.Event, is_new: bool) -> models.Alarm:
    existing = db.query(models.Alarm).filter(models.Alarm.violation_id == violation.violation_id).first()

    alarm = existing or models.Alarm(
        alarm_id=f"alarm_{uuid.uuid4().hex[:12]}",
        violation_id=violation.violation_id,
        alarm_type=f"{violation.violation_type}_ALERT",
        audience="DRIVER",
    )

    alarm.timestamp = violation.last_event_timestamp or event.timestamp
    alarm.severity = violation.severity
    alarm.message = ALARM_MESSAGES.get(violation.violation_type, "⚠️ VIOLATION DETECTED.")
    alarm.priority = SEVERITY_PRIORITY.get(violation.severity, 3)
    alarm.buzzer_fired_at = alarm.timestamp
    alarm.status = "PENDING_ACK"

    # Simulated in-cabin response — no real edge feedback channel exists for this POC.
    if is_new or alarm.driver_ack_latency_seconds is None:
        alarm.driver_ack_latency_seconds = round(random.uniform(3, 12), 1)
        speed_before = event.speed_kmh if event.speed_kmh is not None else round(random.uniform(60, 90), 1)
        alarm.speed_before_kmh = speed_before
        alarm.speed_after_kmh = round(speed_before * random.uniform(0.55, 0.75), 1)

    db.add(alarm)
    db.flush()

    logger.info(
        "[SIMULATED SMS/EMAIL] %s -> %s | %s",
        alarm.audience,
        violation.vehicle.registration if violation.vehicle else violation.vehicle_id,
        alarm.message,
    )

    return alarm


def build_alert_created_or_updated_type(is_new: bool) -> str:
    return "alert_created" if is_new else "alert_updated"
