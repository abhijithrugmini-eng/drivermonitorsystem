from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    JSON,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)
    registration = Column(String, unique=True, nullable=False, index=True)
    vin = Column(String, nullable=True)
    fleet_id = Column(String, nullable=True)
    vehicle_type = Column(String, default="18-wheeler box truck")
    region = Column(String, nullable=True)
    route_default = Column(String, nullable=True)
    edge_device_id = Column(String, nullable=True)
    edge_device_status = Column(String, default="Online")
    firmware_version = Column(String, default="v2.3")
    extra_metadata = Column(JSON, nullable=True)
    last_seen_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    events = relationship("Event", back_populates="vehicle")
    violations = relationship("Violation", back_populates="vehicle")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    # Fleet-system driver ID (from --vehicle-config's required "driver_id" field) —
    # replaces the old driver_code, which was never populated by any real code path.
    driver_id = Column(String, unique=True, nullable=True, index=True)
    name = Column(String, nullable=True)
    extra_metadata = Column(JSON, nullable=True)

    events = relationship("Event", back_populates="driver")
    violations = relationship("Violation", back_populates="driver")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    type = Column(String, nullable=False, index=True)
    confidence = Column(Float, default=0.0)
    metrics_json = Column(JSON, default=dict)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)

    trip_id = Column(String, nullable=True)
    route = Column(String, nullable=True)
    shift_label = Column(String, nullable=True)
    trip_started_at = Column(Float, nullable=True)
    elapsed_trip_seconds = Column(Float, nullable=True)

    speed_kmh = Column(Float, nullable=True)
    rpm = Column(Float, nullable=True)
    is_moving = Column(Boolean, default=True)

    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    distance_to_waypoint_km = Column(Float, nullable=True)
    waypoint_name = Column(String, nullable=True)

    camera_id = Column(String, nullable=True)
    frame_index = Column(Integer, nullable=True)
    device_id = Column(String, nullable=True)
    processing_time_ms = Column(Float, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    vehicle = relationship("Vehicle", back_populates="events")
    driver = relationship("Driver", back_populates="events")
    evidence = relationship("Evidence", back_populates="event", uselist=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, ForeignKey("events.event_id"), unique=True, nullable=False)
    image_path = Column(String, nullable=True)
    video_path = Column(String, nullable=True)
    captured_at = Column(Float, nullable=True)
    uploaded_at = Column(DateTime, default=utcnow)
    sync_status = Column(String, default="SYNCED")

    event = relationship("Event", back_populates="evidence")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True)
    violation_id = Column(String, unique=True, nullable=False, index=True)
    violation_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)  # ACTIVE | ACKNOWLEDGED | RESOLVED
    rule_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)

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

    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    advisory_sent_at = Column(DateTime, nullable=True)
    advisory_message = Column(String, nullable=True)

    vehicle = relationship("Vehicle", back_populates="violations")
    driver = relationship("Driver", back_populates="violations")
    alarm = relationship("Alarm", back_populates="violation", uselist=False)


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True)
    alarm_id = Column(String, unique=True, nullable=False, index=True)
    violation_id = Column(String, ForeignKey("violations.violation_id"), unique=True, nullable=False)
    timestamp = Column(Float, nullable=False)
    alarm_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(String, nullable=False)
    audience = Column(String, default="DRIVER")
    priority = Column(Integer, default=1)

    buzzer_fired_at = Column(Float, nullable=True)
    driver_ack_latency_seconds = Column(Float, nullable=True)
    speed_before_kmh = Column(Float, nullable=True)
    speed_after_kmh = Column(Float, nullable=True)

    status = Column(String, default="PENDING_ACK")

    violation = relationship("Violation", back_populates="alarm")
