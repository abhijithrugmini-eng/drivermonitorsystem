"""Telematics Simulator — drives the Telematics Agent directly (no HTTP hop) so a
demo run has plausible-looking GPS/speed/RPM with no second process to start.

Two motion models:
  - route (VehicleConfig.route present): GPS position is derived from accumulated
    speed, not generated independently — see _next_route_update(). This is the
    GPS/speed tandem: the two can never numerically contradict each other.
  - fallback (no route): a canned waypoint loop + independent oscillating speed,
    for a quick demo where an exact route doesn't matter.

Toggle with TELEMATICS_SOURCE in src/config.py ("simulator" default | "http").
See .claude/skills/dms-edge-dev/SKILL.md "Telematics Simulator" and
dms-spec/changes/add-telematics-simulator-and-vehicle-config/design.md.
"""
from __future__ import annotations

import math
import random
import time

from src.config import (
    TELEMATICS_SIM_INTERVAL_SECS,
    TELEMATICS_SIM_RPM_CRUISE,
    TELEMATICS_SIM_RPM_IDLE,
)
from src.vehicle_config import RouteConfig
from agents.telematics_agent import TelematicsAgent, TelemetryUpdate

EARTH_RADIUS_KM = 6371.0

# Canned highway loop for the fallback model (no route supplied) — a few km apart,
# arbitrary plausible coordinates, looped indefinitely.
_FALLBACK_WAYPOINTS = [
    (37.7749, -122.4194),
    (37.7849, -122.4094),
    (37.7949, -122.3994),
    (37.8049, -122.3894),
    (37.7949, -122.3794),
    (37.7849, -122.3894),
    (37.7749, -122.3994),
    (37.7649, -122.4094),
]


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _interpolate(lat1: float, lon1: float, lat2: float, lon2: float, fraction: float) -> tuple[float, float]:
    """Straight-line (linear) interpolation — adequate for the short/medium demo
    distances this simulates; not true great-circle spherical interpolation."""
    fraction = max(0.0, min(1.0, fraction))
    return (
        lat1 + (lat2 - lat1) * fraction,
        lon1 + (lon2 - lon1) * fraction,
    )


class TelematicsSimulator:
    """Not a BaseAgent — plain in-process driver for TelematicsAgent.run(). See
    .claude/skills/dms-agentic-architecture/SKILL.md for why this isn't a sixth agent."""

    name = "telematics_simulator"

    def __init__(
        self, telematics_agent: TelematicsAgent, truck_id: str, route: RouteConfig | None = None
    ) -> None:
        self._agent = telematics_agent
        self._truck_id = truck_id
        self._route = route
        self._t0 = time.time()
        self._last_tick = self._t0
        self._distance_km = 0.0
        self._total_distance_km = 0.0
        if route is not None:
            self._total_distance_km = _haversine_distance_km(
                route.from_lat, route.from_lon, route.to_lat, route.to_lon
            )

    def _rpm_for_speed(self, speed_kmh: float, is_moving: bool) -> float:
        if not is_moving:
            lo, hi = TELEMATICS_SIM_RPM_IDLE
            return random.uniform(lo, hi)
        lo, hi = TELEMATICS_SIM_RPM_CRUISE
        # Scale within the cruise band proportional to speed (clamp to a plausible
        # top-end reference of 100 km/h), plus jitter for realism.
        scale = max(0.0, min(1.0, speed_kmh / 100.0))
        base = lo + (hi - lo) * scale
        return max(lo, base + random.uniform(-50, 50))

    def _next_update(self) -> TelemetryUpdate:
        now = time.time()
        elapsed = now - self._t0
        if self._route is not None:
            return self._next_route_update(now, elapsed)
        return self._next_fallback_update(elapsed)

    def _next_route_update(self, now: float, elapsed: float) -> TelemetryUpdate:
        route = self._route
        if elapsed >= route.duration_secs:
            return TelemetryUpdate(
                truck_id=self._truck_id, latitude=route.to_lat, longitude=route.to_lon,
                speed=0.0, heading=0.0, status="STOPPED",
                rpm=self._rpm_for_speed(0.0, False),
            )

        dt_hours = (now - self._last_tick) / 3600.0
        self._last_tick = now
        speed = max(0.0, route.avg_speed_kmh + route.avg_speed_kmh * 0.2 * math.sin(elapsed / 60))
        self._distance_km += speed * dt_hours

        fraction = (
            min(1.0, self._distance_km / self._total_distance_km) if self._total_distance_km > 0 else 1.0
        )
        lat, lon = _interpolate(route.from_lat, route.from_lon, route.to_lat, route.to_lon, fraction)
        is_moving = speed > 5.0
        return TelemetryUpdate(
            truck_id=self._truck_id, latitude=lat, longitude=lon,
            speed=speed, heading=0.0,
            status="MOVING" if is_moving else "STOPPED",
            rpm=self._rpm_for_speed(speed, is_moving),
        )

    def _next_fallback_update(self, elapsed: float) -> TelemetryUpdate:
        idx = int(elapsed // TELEMATICS_SIM_INTERVAL_SECS)
        lat, lon = _FALLBACK_WAYPOINTS[idx % len(_FALLBACK_WAYPOINTS)]
        speed = max(0.0, 65 + 25 * math.sin(elapsed / 180))
        is_moving = speed > 5.0
        return TelemetryUpdate(
            truck_id=self._truck_id, latitude=lat, longitude=lon,
            speed=speed, heading=0.0,
            status="MOVING" if is_moving else "STOPPED",
            rpm=self._rpm_for_speed(speed, is_moving),
        )

    def run_forever(self) -> None:
        """Blocking — call from a daemon thread. See main.py."""
        print(
            f"[{self.name}] simulating telemetry for truck={self._truck_id} "
            f"({'route' if self._route else 'fallback'} model), every "
            f"{TELEMATICS_SIM_INTERVAL_SECS}s"
        )
        while True:
            self._agent.run(self._next_update())
            time.sleep(TELEMATICS_SIM_INTERVAL_SECS)
