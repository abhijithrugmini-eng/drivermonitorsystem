"""Violation Detection Agent — the edge's own copy of dms-backend's rule engine
(app/rule_agents/violation_rules.py), ported faithfully per
dms-spec/specs/violation-detection/spec.md and
dms-spec/changes/move-violation-detection-to-edge/design.md: same 4 rules, same
"growing violations" behavior (one ACTIVE violation per type, absorbing new
matching events in place rather than spawning a duplicate).

This is what makes "local AI analytics at the edge" real: rules are evaluated
here, against dms-edge/storage/local.db, with no cloud round-trip required.

Single-vehicle scope: this device only ever sees its own history, so windows/
state are keyed by event type alone (no vehicle_id, unlike the backend version).

See .claude/skills/dms-edge-dev/SKILL.md "Violation Detection Agent".
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src import config
from src.events import DMSEvent, EventType
from storage import models
from storage.database import SessionLocal

# DMSEvent.event_type -> rule definition for the two windowed rules — mirrors
# dms-backend/app/rule_agents/violation_rules.py's WINDOWED_RULES.
WINDOWED_RULES = {
    EventType.DROWSINESS: {
        "violation_type": "DROWSINESS_PATTERN",
        "rule_id": "drowsiness_3in2min",
        "rule_name": "3 Drowsiness Events in 2 Minutes",
        "severity": "CRITICAL",
        "window_seconds": config.DROWSINESS_WINDOW_SECONDS,
        "count_threshold": config.DROWSINESS_EVENT_COUNT,
    },
    EventType.DISTRACTION: {
        "violation_type": "DISTRACTION_PATTERN",
        "rule_id": "distraction_2in1min",
        "rule_name": "2 Distraction Events in 1 Minute",
        "severity": "MEDIUM",
        "window_seconds": config.DISTRACTION_WINDOW_SECONDS,
        "count_threshold": config.DISTRACTION_EVENT_COUNT,
    },
}


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _build_recommended_action(*, violation_type: str, event_count: int, window_seconds: float | None) -> str:
    """Ported from dms-backend/app/rule_agents/notification_rules.py's
    build_recommended_action — same templates, minus the waypoint reference
    (dms-edge's Telematics Agent doesn't carry waypoint/distance data yet; see
    .claude/skills/dms-edge-dev/SKILL.md "Telematics Simulator")."""
    window_min = round((window_seconds or 0) / 60, 1)

    if violation_type == "DROWSINESS_PATTERN":
        return f"{_ordinal(event_count)} micro-sleep in {window_min} min. Advise driver to pull over safely."
    if violation_type == "PHONE_USAGE":
        return "Phone usage detected while driving. Advise driver to stop handheld device use immediately."
    if violation_type == "DISTRACTION_PATTERN":
        return (
            f"{event_count} distraction events in {window_min} min. "
            "Advise driver to refocus attention on the road."
        )
    if violation_type == "CONTINUOUS_DRIVE":
        return "Driver has exceeded 4 continuous hours without a break. Advise scheduling a rest stop."
    return "Monitor driver behaviour."


class ViolationDetectionAgent:
    """BaseAgent[DMSEvent, Violation | None]."""

    name = "violation_detection_agent"

    def __init__(self, session_factory=SessionLocal) -> None:
        self._session_factory = session_factory

    def run(self, input_: DMSEvent) -> models.Violation | None:
        event = input_
        db = self._session_factory()
        try:
            local_event = self._store_event(db, event)
            violation = self._evaluate(db, local_event, event)
            db.commit()
            return violation
        finally:
            db.close()

    def _store_event(self, db: Session, event: DMSEvent) -> models.Event:
        local_event = models.Event(
            event_id=event.id,
            timestamp=event.timestamp,
            type=event.event_type.value,
            confidence=float(event.metrics.get("confidence", 1.0)),
            metrics_json=event.metrics,
        )
        db.add(local_event)
        db.flush()
        return local_event

    def _evaluate(self, db: Session, local_event: models.Event, event: DMSEvent) -> models.Violation | None:
        if event.event_type == EventType.PHONE_USAGE:
            return self._evaluate_phone_usage(db, local_event)
        if event.event_type == EventType.CONTINUOUS_DRIVE:
            return self._evaluate_continuous_drive(db, local_event)
        if event.event_type in WINDOWED_RULES:
            return self._evaluate_windowed(db, local_event, WINDOWED_RULES[event.event_type])
        return None

    def _evaluate_windowed(self, db: Session, local_event: models.Event, rule: dict) -> models.Violation | None:
        window_start = local_event.timestamp - rule["window_seconds"]
        window = (
            db.query(models.Event)
            .filter(
                models.Event.type == local_event.type,
                models.Event.timestamp >= window_start,
                models.Event.timestamp <= local_event.timestamp,
            )
            .order_by(models.Event.timestamp)
            .all()
        )
        if len(window) < rule["count_threshold"]:
            return None

        trigger_ids = [e.event_id for e in window]
        return self._upsert_violation(
            db,
            local_event=local_event,
            violation_type=rule["violation_type"],
            rule_id=rule["rule_id"],
            rule_name=rule["rule_name"],
            severity=rule["severity"],
            trigger_event_ids=trigger_ids,
            first_ts=window[0].timestamp,
            last_ts=window[-1].timestamp,
            window_seconds=rule["window_seconds"],
        )

    def _evaluate_phone_usage(self, db: Session, local_event: models.Event) -> models.Violation | None:
        if local_event.confidence is None or local_event.confidence <= config.PHONE_USAGE_CONFIDENCE_THRESHOLD:
            return None
        return self._upsert_violation(
            db,
            local_event=local_event,
            violation_type="PHONE_USAGE",
            rule_id="phone_usage_conf_gt_0.85",
            rule_name="Phone Usage Detected (confidence > 0.85)",
            severity="HIGH",
            trigger_event_ids=[local_event.event_id],
            first_ts=local_event.timestamp,
            last_ts=local_event.timestamp,
            window_seconds=0,
        )

    def _evaluate_continuous_drive(self, db: Session, local_event: models.Event) -> models.Violation | None:
        # src/dms.py (frozen) reports elapsed drive time via "minutes_since_break",
        # not the "drive_duration_hours" key dms-backend's version reads — adapt
        # the field being read, not the >4h threshold itself.
        minutes = (local_event.metrics_json or {}).get("minutes_since_break")
        if minutes is None or (minutes / 60) <= config.CONTINUOUS_DRIVE_HOURS_THRESHOLD:
            return None
        return self._upsert_violation(
            db,
            local_event=local_event,
            violation_type="CONTINUOUS_DRIVE",
            rule_id="continuous_drive_gt_4h",
            rule_name="Continuous Drive Exceeds 4 Hours",
            severity="LOW",
            trigger_event_ids=[local_event.event_id],
            first_ts=local_event.timestamp,
            last_ts=local_event.timestamp,
            window_seconds=0,
        )

    def _upsert_violation(
        self,
        db: Session,
        *,
        local_event: models.Event,
        violation_type: str,
        rule_id: str,
        rule_name: str,
        severity: str,
        trigger_event_ids: list[str],
        first_ts: float,
        last_ts: float,
        window_seconds: float,
    ) -> models.Violation:
        existing = (
            db.query(models.Violation)
            .filter(models.Violation.violation_type == violation_type, models.Violation.status == "ACTIVE")
            .first()
        )

        violation = existing or models.Violation(
            violation_id=f"viol_{uuid.uuid4().hex[:12]}",
            violation_type=violation_type,
            rule_id=rule_id,
            rule_name=rule_name,
            severity=severity,
            status="ACTIVE",
            trigger_event_ids_json=[],
            first_event_timestamp=first_ts,
        )

        merged_ids = list(dict.fromkeys((violation.trigger_event_ids_json or []) + trigger_event_ids))
        violation.trigger_event_ids_json = merged_ids
        violation.event_count = len(merged_ids)
        violation.first_event_timestamp = min(violation.first_event_timestamp or first_ts, first_ts)
        violation.last_event_timestamp = last_ts
        violation.time_window_seconds = window_seconds
        violation.severity_score = round(min(0.99, 0.7 + 0.05 * violation.event_count), 2)
        violation.primary_evidence_event_id = local_event.event_id
        violation.recommended_action_text = _build_recommended_action(
            violation_type=violation_type,
            event_count=violation.event_count,
            window_seconds=violation.time_window_seconds,
        )

        db.add(violation)
        db.flush()
        return violation
