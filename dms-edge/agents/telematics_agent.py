"""Telematics Agent — receives GPS/telemetry updates pushed by the Fleet Simulator
(or a manual curl, until fleet-simulator exists) and holds the latest known vehicle
state for the Behaviour Detection / Cloud Hub agents to read.

See .claude/skills/dms-edge-dev/SKILL.md "Telematics Agent" and
.claude/skills/fleet-simulator-dev/SKILL.md for the GPS update schema this ingests.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from flask import Flask, jsonify, request

from src.config import TELEMATICS_INGEST_HOST, TELEMATICS_INGEST_PORT


@dataclass
class TelemetryUpdate:
    """Input — matches fleet-simulator-dev's GPS update JSON schema."""

    truck_id: str
    latitude: float
    longitude: float
    speed: float = 0.0
    heading: float = 0.0
    status: str = "STOPPED"  # "MOVING" | "STOPPED" | "IDLE"
    timestamp: str | None = None

    @classmethod
    def from_json(cls, payload: dict) -> "TelemetryUpdate":
        return cls(
            truck_id=str(payload["truckId"]),
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
            speed=float(payload.get("speed", 0.0)),
            heading=float(payload.get("heading", 0.0)),
            status=str(payload.get("status", "STOPPED")),
            timestamp=payload.get("timestamp"),
        )


@dataclass
class VehicleState:
    """Output — latest normalized vehicle state, read by the Cloud Hub Agent."""

    lat: float | None = None
    lon: float | None = None
    speed_kmh: float | None = None
    heading: float | None = None
    is_moving: bool = False
    last_updated: float | None = None


class TelematicsAgent:
    """BaseAgent[TelemetryUpdate, VehicleState]. Fed by the Fleet Simulator's
    HttpPublisher (primary path) via POST /telemetry — not a real telematics bus."""

    name = "telematics_agent"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = VehicleState()
        self._app = self._build_app()

    def run(self, input_: TelemetryUpdate) -> VehicleState:
        state = VehicleState(
            lat=input_.latitude,
            lon=input_.longitude,
            speed_kmh=input_.speed,
            heading=input_.heading,
            is_moving=input_.status == "MOVING",
            last_updated=time.time(),
        )
        with self._lock:
            self._state = state
        print(f"[{self.name}] updated vehicle state from truck={input_.truck_id}: {state}")
        return state

    def get_latest_state(self) -> VehicleState:
        with self._lock:
            return self._state

    def _build_app(self) -> Flask:
        app = Flask(f"{self.name}_listener")

        @app.route("/telemetry", methods=["POST"])
        def telemetry():
            payload = request.get_json(force=True, silent=True)
            if not payload:
                return jsonify({"error": "invalid or missing JSON body"}), 400
            try:
                update = TelemetryUpdate.from_json(payload)
            except (KeyError, TypeError, ValueError) as exc:
                return jsonify({"error": f"invalid telemetry payload: {exc}"}), 400
            state = self.run(update)
            return jsonify(vars(state)), 200

        @app.route("/telemetry", methods=["GET"])
        def telemetry_debug():
            return jsonify(vars(self.get_latest_state())), 200

        return app

    def start_listener(self) -> None:
        """Blocking — call from a daemon thread. See main.py."""
        print(
            f"[{self.name}] listening on "
            f"http://{TELEMATICS_INGEST_HOST}:{TELEMATICS_INGEST_PORT}/telemetry"
        )
        self._app.run(
            host=TELEMATICS_INGEST_HOST,
            port=TELEMATICS_INGEST_PORT,
            threaded=True,
            use_reloader=False,
        )
