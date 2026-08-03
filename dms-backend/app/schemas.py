"""Pydantic request models — the Inject API's input contract from dms-edge (or the seed script)."""

from typing import Any

from pydantic import BaseModel, Field


class DetectionIn(BaseModel):
    type: str
    confidence: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict)


class ContextIn(BaseModel):
    vehicle_registration: str
    vehicle_vin: str | None = None
    vehicle_fleet_id: str | None = None
    driver_id: str | None = None  # fleet-system driver ID; replaces the old driver_code
    driver_name: str | None = None
    vehicle_meta: dict[str, Any] | None = None  # opaque passthrough from --vehicle-config
    driver_meta: dict[str, Any] | None = None  # reserved — unpopulated by dms-edge today
    trip_id: str | None = None
    route: str | None = None
    shift_label: str | None = None
    trip_started_at: float | None = None
    elapsed_trip_seconds: float | None = None
    frame_index: int | None = None
    camera_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    waypoint_name: str | None = None
    distance_to_waypoint_km: float | None = None


class VehicleIn(BaseModel):
    speed_kmh: float | None = None
    rpm: float | None = None
    is_moving: bool = True
    vehicle_type: str | None = None
    region: str | None = None


class DeviceIn(BaseModel):
    device_id: str | None = None
    device_model: str | None = None
    os: str | None = None
    processing_time_ms: float | None = None
    edge_device_status: str | None = None
    firmware_version: str | None = None


class EventIn(BaseModel):
    event_id: str
    timestamp: float
    source: str | None = None
    detection: DetectionIn
    context: ContextIn
    vehicle: VehicleIn = Field(default_factory=VehicleIn)
    device: DeviceIn = Field(default_factory=DeviceIn)


class EventCreateResponse(BaseModel):
    event_id: str
    violations_triggered: list[str]


class AlarmIn(BaseModel):
    """Nested in ViolationIn — dms-edge's Alarm Agent output. See
    dms-spec/changes/move-violation-detection-to-edge/design.md."""

    fired_at: float
    message: str
    driver_ack_latency_seconds: float | None = None
    speed_before_kmh: float | None = None
    speed_after_kmh: float | None = None


class ViolationIn(BaseModel):
    """POST /api/violations — an already-computed Violation (+ Alarm) pushed by
    dms-edge's Cloud Hub Agent, the primary detection path now. See
    dms-spec/changes/move-violation-detection-to-edge/design.md."""

    violation_id: str
    violation_type: str  # DROWSINESS_PATTERN | PHONE_USAGE | DISTRACTION_PATTERN | CONTINUOUS_DRIVE
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    status: str = "ACTIVE"
    event_count: int
    trigger_event_ids: list[str]
    first_event_timestamp: float
    last_event_timestamp: float
    recommended_action_text: str
    context: ContextIn
    vehicle: VehicleIn = Field(default_factory=VehicleIn)
    alarm: AlarmIn


class ViolationCreateResponse(BaseModel):
    violation_id: str
    status: str


class AcknowledgeIn(BaseModel):
    acknowledged_by: str = "dispatcher"


class AdvisoryIn(BaseModel):
    message: str | None = None
