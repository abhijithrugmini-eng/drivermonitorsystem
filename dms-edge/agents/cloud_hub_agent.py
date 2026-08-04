"""Cloud Hub Agent — maps a DMSEvent + the Telematics Agent's latest vehicle state
into dms-backend's nested Event JSON contract and pushes it over HTTP. Fire-and-
forget by design, matching the reference app's style: log and drop on failure, no
retry queue.

See .claude/skills/dms-edge-dev/SKILL.md "Cloud Hub Agent" / "Data flow contract".
"""
from __future__ import annotations

import time
import uuid

import cv2
import numpy as np
import requests

from src.config import (
    BACKEND_REQUEST_TIMEOUT_SECS,
    BACKEND_URL,
    CAMERA_ID,
    DEVICE_ID,
    DEVICE_MODEL,
    EDGE_VEHICLE_REGISTRATION,
)
from src.events import DMSEvent, EventType
from src.vehicle_config import VehicleConfig
from agents.alarm_agent import Alarm
from agents.telematics_agent import TelematicsAgent, VehicleState
from storage import models

# Event types dms-backend's Violation Detection Agent has rules for (or otherwise
# stores) — forwarded to /api/events. DRIVER_QUESTION/DRIVER_ANSWER/SYSTEM are
# in-cabin-only concepts with no server-side meaning and are dropped.
FORWARDED_EVENT_TYPES = {
    EventType.DROWSINESS,
    EventType.YAWN,
    EventType.DISTRACTION,
    EventType.PHONE_USAGE,
    EventType.NO_FACE,
    EventType.CONTINUOUS_DRIVE,
}

# Event types worth attaching an evidence frame to.
EVIDENCE_EVENT_TYPES = {EventType.PHONE_USAGE, EventType.DROWSINESS}


class CloudHubAgent:
    """BaseAgent[DMSEvent, None]. Reads the Telematics Agent's latest VehicleState
    and pushes to dms-backend's Inject API."""

    name = "cloud_hub_agent"

    def __init__(self, telematics_agent: TelematicsAgent, vehicle_config: VehicleConfig | None = None) -> None:
        self._telematics_agent = telematics_agent
        self._vehicle_config = vehicle_config
        # One trip per edge process run — no ignition-cycle/trip-boundary detection
        # in this POC, see dms-spec/changes/display-trip-details-in-ui/design.md.
        self._trip_id = f"trip_{uuid.uuid4().hex[:12]}"
        self._trip_started_at = time.time()

    def _vehicle_registration(self) -> str:
        return self._vehicle_config.vehicle_registration if self._vehicle_config else EDGE_VEHICLE_REGISTRATION

    def _identity_context(self) -> dict:
        """vehicle/driver identity fields sourced from --vehicle-config when given,
        else None (matches today's behavior of not sending them at all)."""
        vc = self._vehicle_config
        return {
            "vehicle_vin": vc.vin if vc else None,
            "vehicle_fleet_id": vc.fleet_id if vc else None,
            "driver_id": vc.driver_id if vc else None,
            "driver_name": vc.driver_name if vc else None,
            "vehicle_meta": (vc.extra or None) if vc else None,
        }

    def _trip_context(self) -> dict:
        """route/shift sourced from --vehicle-config when given; trip_id/trip_started_at/
        elapsed_trip_seconds are generated once per process run (this agent's lifetime)."""
        vc = self._vehicle_config
        return {
            "route": vc.route_name if vc else None,
            "shift_label": vc.shift_label if vc else None,
            "trip_id": self._trip_id,
            "trip_started_at": self._trip_started_at,
            "elapsed_trip_seconds": time.time() - self._trip_started_at,
        }

    def _map_event(self, event: DMSEvent, vehicle_state: VehicleState) -> dict:
        return {
            "event_id": event.id,
            "timestamp": event.timestamp,
            "source": "dms-edge",
            "detection": {
                "type": event.event_type.value,
                "confidence": float(event.metrics.get("confidence", 1.0)),
                "metrics": event.metrics,
            },
            "context": {
                "vehicle_registration": self._vehicle_registration(),
                **self._identity_context(),
                **self._trip_context(),
                "frame_index": event.frame_index,
                "camera_id": CAMERA_ID,
                "lat": vehicle_state.lat,
                "lon": vehicle_state.lon,
            },
            "vehicle": {
                "speed_kmh": vehicle_state.speed_kmh,
                "is_moving": vehicle_state.is_moving,
                "rpm": vehicle_state.rpm,
            },
            "device": {
                "device_id": DEVICE_ID,
                "device_model": DEVICE_MODEL,
            },
        }

    def run(self, input_: DMSEvent, evidence_frame: np.ndarray | None = None) -> None:
        event = input_
        if event.event_type not in FORWARDED_EVENT_TYPES:
            return

        vehicle_state = self._telematics_agent.get_latest_state()
        payload = self._map_event(event, vehicle_state)

        try:
            resp = requests.post(
                f"{BACKEND_URL}/api/events", json=payload, timeout=BACKEND_REQUEST_TIMEOUT_SECS
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[{self.name}] failed to push event {event.id} ({event.event_type.value}): {exc}")
            return

        print(f"[{self.name}] pushed event {event.id} ({event.event_type.value}) to {BACKEND_URL}")

        if event.event_type in EVIDENCE_EVENT_TYPES and evidence_frame is not None:
            self._push_evidence(event.id, evidence_frame)

    def _map_violation(self, violation: models.Violation, alarm: Alarm, vehicle_state: VehicleState) -> dict:
        return {
            "violation_id": violation.violation_id,
            "violation_type": violation.violation_type,
            "severity": violation.severity,
            "status": violation.status,
            "event_count": violation.event_count,
            "trigger_event_ids": violation.trigger_event_ids_json or [],
            "first_event_timestamp": violation.first_event_timestamp,
            "last_event_timestamp": violation.last_event_timestamp,
            "recommended_action_text": violation.recommended_action_text,
            "context": {
                "vehicle_registration": self._vehicle_registration(),
                **self._identity_context(),
                **self._trip_context(),
                "lat": vehicle_state.lat,
                "lon": vehicle_state.lon,
            },
            "vehicle": {
                "speed_kmh": vehicle_state.speed_kmh,
                "is_moving": vehicle_state.is_moving,
                "rpm": vehicle_state.rpm,
            },
            "alarm": {
                "fired_at": alarm.fired_at,
                "message": alarm.message,
                "driver_ack_latency_seconds": alarm.driver_ack_latency_seconds,
                "speed_before_kmh": alarm.speed_before_kmh,
                "speed_after_kmh": alarm.speed_after_kmh,
            },
        }

    def push_violation(self, violation: models.Violation, alarm: Alarm) -> None:
        """Called after the Violation Detection Agent + Alarm Agent produce a
        new-or-updated Violation — see design.md's POST /api/violations contract."""
        vehicle_state = self._telematics_agent.get_latest_state()
        payload = self._map_violation(violation, alarm, vehicle_state)

        try:
            resp = requests.post(
                f"{BACKEND_URL}/api/violations", json=payload, timeout=BACKEND_REQUEST_TIMEOUT_SECS
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[{self.name}] failed to push violation {violation.violation_id}: {exc}")
            return

        print(
            f"[{self.name}] pushed violation {violation.violation_id} "
            f"({violation.violation_type}) to {BACKEND_URL}"
        )

    def _push_evidence(self, event_id: str, frame: np.ndarray) -> None:
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            print(f"[{self.name}] failed to encode evidence frame for {event_id}")
            return
        try:
            resp = requests.post(
                f"{BACKEND_URL}/api/evidence",
                data={"event_id": event_id},
                files={"file": (f"{event_id}.jpg", buf.tobytes(), "image/jpeg")},
                timeout=BACKEND_REQUEST_TIMEOUT_SECS,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[{self.name}] failed to push evidence for {event_id}: {exc}")
