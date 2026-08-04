"""Loads --vehicle-config <path.json>: which truck/driver a demo run represents,
plus an optional route for the GPS/speed tandem (see agents/telematics_simulator.py).

See dms-spec/changes/add-telematics-simulator-and-vehicle-config/design.md.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

REQUIRED_FIELDS = ("vehicle_registration", "vin", "fleet_id", "driver_name", "driver_id")
ROUTE_REQUIRED_FIELDS = (
    "from_lat", "from_lon", "to_lat", "to_lon", "avg_speed_kmh", "duration_secs",
)


@dataclass
class RouteConfig:
    """Optional — drives the GPS/speed tandem. Absent means the Telematics
    Simulator falls back to its canned-waypoint + independent-speed model."""

    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    avg_speed_kmh: float
    duration_secs: float


@dataclass
class VehicleConfig:
    vehicle_registration: str
    vin: str
    fleet_id: str
    driver_name: str
    driver_id: str
    route: RouteConfig | None = None
    route_name: str | None = None  # optional display string, e.g. "Mumbai-Pune Corridor" — distinct from route's GPS coords
    shift_label: str | None = None  # optional display string, e.g. "Day Shift (06:00-14:00)"
    extra: dict = field(default_factory=dict)  # any JSON keys beyond the required 5, "route", "route_name", "shift_label"

    @classmethod
    def from_file(cls, path: str) -> "VehicleConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        missing = [k for k in REQUIRED_FIELDS if not data.get(k)]
        if missing:
            print(f"ERROR: --vehicle-config {path} is missing required field(s): {', '.join(missing)}")
            sys.exit(1)

        route = None
        route_data = data.get("route")
        if route_data is not None:
            missing_route = [k for k in ROUTE_REQUIRED_FIELDS if route_data.get(k) is None]
            if missing_route:
                print(
                    f"ERROR: --vehicle-config {path}'s \"route\" is missing "
                    f"required field(s): {', '.join(missing_route)}"
                )
                sys.exit(1)
            route = RouteConfig(
                from_lat=float(route_data["from_lat"]),
                from_lon=float(route_data["from_lon"]),
                to_lat=float(route_data["to_lat"]),
                to_lon=float(route_data["to_lon"]),
                avg_speed_kmh=float(route_data["avg_speed_kmh"]),
                duration_secs=float(route_data["duration_secs"]),
            )

        extra = {
            k: v
            for k, v in data.items()
            if k not in REQUIRED_FIELDS and k not in ("route", "route_name", "shift_label")
        }
        return cls(
            vehicle_registration=str(data["vehicle_registration"]),
            vin=str(data["vin"]),
            fleet_id=str(data["fleet_id"]),
            driver_name=str(data["driver_name"]),
            driver_id=str(data["driver_id"]),
            route=route,
            route_name=data.get("route_name"),
            shift_label=data.get("shift_label"),
            extra=extra,
        )


def load_vehicle_config(path: str | None) -> VehicleConfig | None:
    if path is None:
        return None
    try:
        return VehicleConfig.from_file(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not load --vehicle-config {path}: {exc}")
        sys.exit(1)
