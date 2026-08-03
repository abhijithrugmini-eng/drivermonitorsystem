"""Unit tests for ViolationDetectionAgent — headless, in-memory SQLite (StaticPool
so every SessionLocal() call in agent.run() shares the same in-memory DB).

Run from dms-edge/: pytest tests/
"""
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from agents.violation_detection_agent import ViolationDetectionAgent
from src.events import Audience, DMSEvent, EventType, Severity
from storage.database import Base


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture
def agent(session_factory):
    return ViolationDetectionAgent(session_factory=session_factory)


def _make_event(event_type: EventType, timestamp: float, confidence: float | None = None, **metrics) -> DMSEvent:
    m = dict(metrics)
    if confidence is not None:
        m["confidence"] = confidence
    return DMSEvent(
        event_type=event_type, severity=Severity.HIGH, audience=Audience.DRIVER,
        message="test", metrics=m, timestamp=timestamp,
    )


def test_below_threshold_events_produce_no_violation(agent):
    now = time.time()
    assert agent.run(_make_event(EventType.DROWSINESS, now)) is None
    assert agent.run(_make_event(EventType.DROWSINESS, now + 5)) is None


def test_three_drowsiness_events_in_window_trigger_critical_violation(agent):
    now = time.time()
    agent.run(_make_event(EventType.DROWSINESS, now))
    agent.run(_make_event(EventType.DROWSINESS, now + 10))
    violation = agent.run(_make_event(EventType.DROWSINESS, now + 20))

    assert violation is not None
    assert violation.violation_type == "DROWSINESS_PATTERN"
    assert violation.severity == "CRITICAL"
    assert violation.event_count == 3
    assert "micro-sleep" in violation.recommended_action_text


def test_drowsiness_events_outside_window_do_not_count(agent):
    now = time.time()
    agent.run(_make_event(EventType.DROWSINESS, now))
    agent.run(_make_event(EventType.DROWSINESS, now + 130))  # > 120s window from first
    violation = agent.run(_make_event(EventType.DROWSINESS, now + 140))

    assert violation is None


def test_growing_violation_updates_in_place_not_duplicated(agent):
    now = time.time()
    agent.run(_make_event(EventType.DROWSINESS, now))
    agent.run(_make_event(EventType.DROWSINESS, now + 10))
    first = agent.run(_make_event(EventType.DROWSINESS, now + 20))
    fourth = agent.run(_make_event(EventType.DROWSINESS, now + 30))

    assert first.violation_id == fourth.violation_id
    assert fourth.event_count == 4


def test_phone_usage_above_confidence_threshold_triggers_high(agent):
    violation = agent.run(_make_event(EventType.PHONE_USAGE, time.time(), confidence=0.91))
    assert violation is not None
    assert violation.violation_type == "PHONE_USAGE"
    assert violation.severity == "HIGH"


def test_phone_usage_below_confidence_threshold_no_violation(agent):
    violation = agent.run(_make_event(EventType.PHONE_USAGE, time.time(), confidence=0.5))
    assert violation is None


def test_two_distraction_events_trigger_medium(agent):
    now = time.time()
    agent.run(_make_event(EventType.DISTRACTION, now))
    violation = agent.run(_make_event(EventType.DISTRACTION, now + 5))
    assert violation is not None
    assert violation.violation_type == "DISTRACTION_PATTERN"
    assert violation.severity == "MEDIUM"


def test_continuous_drive_over_four_hours_triggers_low(agent):
    violation = agent.run(
        _make_event(EventType.CONTINUOUS_DRIVE, time.time(), minutes_since_break=241)
    )
    assert violation is not None
    assert violation.violation_type == "CONTINUOUS_DRIVE"
    assert violation.severity == "LOW"


def test_continuous_drive_under_four_hours_no_violation(agent):
    violation = agent.run(
        _make_event(EventType.CONTINUOUS_DRIVE, time.time(), minutes_since_break=120)
    )
    assert violation is None


def test_unrelated_event_type_produces_no_violation(agent):
    assert agent.run(_make_event(EventType.YAWN, time.time())) is None
    assert agent.run(_make_event(EventType.NO_FACE, time.time())) is None
