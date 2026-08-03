"""Local Event/Violation ORM models — a small subset of dms-backend's schema
(app/db/models.py). Single-vehicle scope: this device only ever sees its own
history, so there's no vehicle_id/driver_id here (unlike the backend version).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String

from storage.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    type = Column(String, nullable=False, index=True)
    confidence = Column(Float, default=0.0)
    metrics_json = Column(JSON, default=dict)

    created_at = Column(DateTime, default=utcnow)


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True)
    violation_id = Column(String, unique=True, nullable=False, index=True)
    violation_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)  # ACTIVE | ACKNOWLEDGED | RESOLVED
    rule_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)

    trigger_event_ids_json = Column(JSON, default=list)
    event_count = Column(Integer, default=1)
    first_event_timestamp = Column(Float, nullable=True)
    last_event_timestamp = Column(Float, nullable=True)
    time_window_seconds = Column(Float, nullable=True)
    severity_score = Column(Float, default=0.0)

    primary_evidence_event_id = Column(String, nullable=True)
    recommended_action_text = Column(String, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
