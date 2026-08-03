"""Server-side violation detection — the 4 rules from specs/VIOLATION_AND_EVIDENCE_MODELS.md.

Stateful, in-memory sliding windows keyed by vehicle_id + event type. Window math uses each
event's own `timestamp` field (not server receipt time) so demo/seed scripts can fabricate
spaced timestamps and trigger rules without waiting on the wall clock.

Violations "grow in place": a single ACTIVE violation per (vehicle, violation_type) absorbs
new matching events (event_count/evidence/recommended_action keep climbing) until it's
acknowledged/resolved, rather than spawning a duplicate row per re-trigger.
"""

import uuid
from collections import defaultdict, deque

from sqlalchemy.orm import Session

from app import config
from app.db import models
from app.rule_agents.notification_rules import build_recommended_action

# event.type -> rule definition. Windowed rules (drowsiness/distraction) require N events
# within a rolling window; the others evaluate a single event's fields directly.
WINDOWED_RULES = {
    "DROWSINESS": {
        "violation_type": "DROWSINESS_PATTERN",
        "rule_id": "drowsiness_3in2min",
        "rule_name": "3 Drowsiness Events in 2 Minutes",
        "severity": "CRITICAL",
        "window_seconds": config.DROWSINESS_WINDOW_SECONDS,
        "count_threshold": config.DROWSINESS_EVENT_COUNT,
    },
    "DISTRACTION": {
        "violation_type": "DISTRACTION_PATTERN",
        "rule_id": "distraction_2in1min",
        "rule_name": "2 Distraction Events in 1 Minute",
        "severity": "MEDIUM",
        "window_seconds": config.DISTRACTION_WINDOW_SECONDS,
        "count_threshold": config.DISTRACTION_EVENT_COUNT,
    },
}

# windows[vehicle_id][event_type] -> deque[(timestamp, event_id, confidence)]
_windows: dict[int, dict[str, deque]] = defaultdict(lambda: defaultdict(deque))


def _prune(window: deque, now_ts: float, window_seconds: float) -> None:
    while window and (now_ts - window[0][0]) > window_seconds:
        window.popleft()


def evaluate_event(db: Session, event: models.Event) -> tuple[models.Violation | None, bool]:
    """Run the rule relevant to this event's type. Returns (violation, is_new) or (None, False)."""
    if event.vehicle_id is None:
        return None, False

    if event.type == "PHONE_USAGE":
        return _evaluate_phone_usage(db, event)
    if event.type == "CONTINUOUS_DRIVE":
        return _evaluate_continuous_drive(db, event)
    if event.type in WINDOWED_RULES:
        return _evaluate_windowed(db, event, WINDOWED_RULES[event.type])
    return None, False


def _evaluate_windowed(db: Session, event: models.Event, rule: dict) -> tuple[models.Violation | None, bool]:
    window = _windows[event.vehicle_id][event.type]
    window.append((event.timestamp, event.event_id, event.confidence))
    _prune(window, event.timestamp, rule["window_seconds"])

    if len(window) < rule["count_threshold"]:
        return None, False

    trigger_ids = [entry[1] for entry in window]
    return _upsert_violation(
        db,
        event=event,
        violation_type=rule["violation_type"],
        rule_id=rule["rule_id"],
        rule_name=rule["rule_name"],
        severity=rule["severity"],
        trigger_event_ids=trigger_ids,
        first_ts=window[0][0],
        last_ts=window[-1][0],
        window_seconds=rule["window_seconds"],
    )


def _evaluate_phone_usage(db: Session, event: models.Event) -> tuple[models.Violation | None, bool]:
    if event.confidence is None or event.confidence <= config.PHONE_USAGE_CONFIDENCE_THRESHOLD:
        return None, False
    return _upsert_violation(
        db,
        event=event,
        violation_type="PHONE_USAGE",
        rule_id="phone_usage_conf_gt_0.85",
        rule_name="Phone Usage Detected (confidence > 0.85)",
        severity="HIGH",
        trigger_event_ids=[event.event_id],
        first_ts=event.timestamp,
        last_ts=event.timestamp,
        window_seconds=0,
    )


def _evaluate_continuous_drive(db: Session, event: models.Event) -> tuple[models.Violation | None, bool]:
    hours = (event.metrics_json or {}).get("drive_duration_hours")
    if hours is None or hours <= config.CONTINUOUS_DRIVE_HOURS_THRESHOLD:
        return None, False
    return _upsert_violation(
        db,
        event=event,
        violation_type="CONTINUOUS_DRIVE",
        rule_id="continuous_drive_gt_4h",
        rule_name="Continuous Drive Exceeds 4 Hours",
        severity="LOW",
        trigger_event_ids=[event.event_id],
        first_ts=event.timestamp,
        last_ts=event.timestamp,
        window_seconds=0,
    )


def _upsert_violation(
    db: Session,
    *,
    event: models.Event,
    violation_type: str,
    rule_id: str,
    rule_name: str,
    severity: str,
    trigger_event_ids: list[str],
    first_ts: float,
    last_ts: float,
    window_seconds: float,
) -> tuple[models.Violation, bool]:
    existing = (
        db.query(models.Violation)
        .filter(
            models.Violation.vehicle_id == event.vehicle_id,
            models.Violation.violation_type == violation_type,
            models.Violation.status == "ACTIVE",
        )
        .first()
    )

    is_new = existing is None
    violation = existing or models.Violation(
        violation_id=f"viol_{uuid.uuid4().hex[:12]}",
        violation_type=violation_type,
        rule_id=rule_id,
        rule_name=rule_name,
        severity=severity,
        status="ACTIVE",
        vehicle_id=event.vehicle_id,
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
    violation.primary_evidence_event_id = event.event_id
    violation.driver_id = event.driver_id or violation.driver_id
    violation.recommended_action_text = build_recommended_action(
        violation_type=violation_type,
        event_count=violation.event_count,
        window_seconds=violation.time_window_seconds,
        event=event,
    )

    db.add(violation)
    db.flush()

    return violation, is_new


def reset_windows() -> None:
    """Used by tests / a fresh demo run to clear in-memory rule state."""
    _windows.clear()
