"""Unit tests for AlarmAgent — headless, no storage dependency (takes a plain
Violation-shaped object in).

Run from dms-edge/: pytest tests/
"""
from types import SimpleNamespace

from agents.alarm_agent import AlarmAgent


def _make_violation(**overrides):
    defaults = dict(
        violation_id="viol_abc123",
        violation_type="DROWSINESS_PATTERN",
        severity="CRITICAL",
        last_event_timestamp=1000.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_alarm_message_matches_violation_type():
    agent = AlarmAgent()
    alarm = agent.run(_make_violation())
    assert alarm.message == "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY."
    assert alarm.violation_id == "viol_abc123"
    assert alarm.fired_at == 1000.0
    assert alarm.priority == 1  # CRITICAL


def test_alarm_priority_follows_severity():
    agent = AlarmAgent()
    alarm = agent.run(_make_violation(violation_type="PHONE_USAGE", severity="HIGH"))
    assert alarm.priority == 2


def test_alarm_uses_supplied_speed_as_speed_before():
    agent = AlarmAgent()
    alarm = agent.run(_make_violation(), speed_kmh=72.0)
    assert alarm.speed_before_kmh == 72.0
    assert alarm.speed_after_kmh < alarm.speed_before_kmh


def test_unknown_violation_type_falls_back_to_generic_message():
    agent = AlarmAgent()
    alarm = agent.run(_make_violation(violation_type="SOMETHING_NEW", severity="LOW"))
    assert alarm.message == "⚠️ VIOLATION DETECTED."
    assert alarm.priority == 4
