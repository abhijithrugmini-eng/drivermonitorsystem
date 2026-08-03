#!/usr/bin/env python3
"""Stands in for dms-edge until it exists: POSTs a scripted event sequence to the backend's own
live /api/events endpoint (one sequence per violation rule, plus under-threshold "noise" events),
uploads a placeholder evidence JPG for each triggering event, then polls /api/alerts to confirm
the whole pipeline (events -> violations -> alarms -> live dashboard) actually works end-to-end.
"""

import json
import sys
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
ASSET_JPG = Path(__file__).parent / "assets" / "placeholder_evidence.jpg"

NOW = time.time()


def make_event(
    *,
    event_type: str,
    confidence: float,
    metrics: dict,
    vehicle_registration: str,
    driver_id: str | None = None,
    driver_name: str | None = None,
    route: str | None = None,
    shift_label: str | None = None,
    speed_kmh: float | None = None,
    waypoint_name: str | None = None,
    distance_to_waypoint_km: float | None = None,
    lat: float | None = None,
    lon: float | None = None,
    ts_offset_seconds: float = 0,
    vehicle_type: str | None = None,
) -> dict:
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "timestamp": NOW - ts_offset_seconds,
        "source": "seed_demo",
        "detection": {"type": event_type, "confidence": confidence, "metrics": metrics},
        "context": {
            "vehicle_registration": vehicle_registration,
            "driver_id": driver_id,
            "driver_name": driver_name,
            "trip_id": f"trip_{vehicle_registration}",
            "route": route,
            "shift_label": shift_label,
            "trip_started_at": NOW - 4 * 3600,
            "elapsed_trip_seconds": 4 * 3600 - ts_offset_seconds,
            "camera_id": "cabin_front",
            "waypoint_name": waypoint_name,
            "distance_to_waypoint_km": distance_to_waypoint_km,
            "lat": lat,
            "lon": lon,
        },
        "vehicle": {
            "speed_kmh": speed_kmh,
            "is_moving": True,
            "vehicle_type": vehicle_type or "18-wheeler box truck",
            "region": "South",
        },
        "device": {
            "device_id": None,
            "device_model": "renesas_rcar",
            "os": "linux",
            "processing_time_ms": 45,
            "edge_device_status": None,
            "firmware_version": None,
        },
    }


def post_event(event: dict) -> dict:
    resp = requests.post(f"{BASE_URL}/api/events", json=event, timeout=5)
    resp.raise_for_status()
    body = resp.json()
    triggered = ", ".join(body["violations_triggered"]) or "no violation"
    print(f"  -> {event['detection']['type']:<16} {event['event_id']}  [{triggered}]")
    return body


def post_evidence(event_id: str) -> None:
    with open(ASSET_JPG, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/api/evidence",
            data={"event_id": event_id},
            files={"file": ("evidence.jpg", f, "image/jpeg")},
            timeout=5,
        )
    resp.raise_for_status()
    print(f"     evidence uploaded for {event_id}")


def run_drowsiness_sequence() -> None:
    print("\n[1/4] Drowsiness pattern -> KA-05-AB-1234 (expect CRITICAL after 3rd event)")
    reg = "KA-05-AB-1234"
    kwargs = dict(
        vehicle_registration=reg,
        driver_id="4521",
        driver_name="R. Kumar",
        route="NH-44, Bengaluru → Hyderabad",
        shift_label="Hour 9 of shift",
        speed_kmh=72,
        waypoint_name="Kolar",
        distance_to_waypoint_km=4,
        lat=12.9716,
        lon=78.2340,
    )
    last_event_id = None
    for i, offset in enumerate([100, 50, 0]):
        event = make_event(
            event_type="DROWSINESS",
            confidence=0.95,
            metrics={"ear": 0.18, "duration_seconds": 0.75, "blink_rate": 8.5},
            ts_offset_seconds=offset,
            **kwargs,
        )
        post_event(event)
        last_event_id = event["event_id"]
        time.sleep(0.1)
    if last_event_id:
        post_evidence(last_event_id)


def run_phone_usage() -> None:
    print("\n[2/4] Phone usage -> TN-09-CD-4521 (expect HIGH, single event confidence>0.85)")
    event = make_event(
        event_type="PHONE_USAGE",
        confidence=0.92,
        metrics={"phone_detected": True, "hand_on_phone": True, "eye_contact_lost": True},
        vehicle_registration="TN-09-CD-4521",
        driver_id="7788",
        driver_name="S. Iyer",
        route="NH-8",
        shift_label="Hour 3 of shift",
        speed_kmh=64,
        waypoint_name="Vellore",
        distance_to_waypoint_km=12,
        lat=12.9165,
        lon=79.1325,
    )
    post_event(event)
    post_evidence(event["event_id"])


def run_distraction_sequence() -> None:
    print("\n[3/4] Distraction pattern -> KA-01-GH-9012 (expect MEDIUM after 2nd event)")
    reg = "KA-01-GH-9012"
    kwargs = dict(
        vehicle_registration=reg,
        driver_id="3345",
        driver_name="P. Nair",
        route="NH-44",
        shift_label="Hour 5 of shift",
        speed_kmh=58,
        waypoint_name="Hosur",
        distance_to_waypoint_km=9,
        lat=12.7409,
        lon=77.8253,
    )
    last_event_id = None
    for offset in [30, 0]:
        event = make_event(
            event_type="DISTRACTION",
            confidence=0.88,
            metrics={"head_yaw_degrees": 35, "gaze_duration": 1.2},
            ts_offset_seconds=offset,
            **kwargs,
        )
        post_event(event)
        last_event_id = event["event_id"]
        time.sleep(0.1)
    if last_event_id:
        post_evidence(last_event_id)


def run_continuous_drive() -> None:
    print("\n[4/4] Continuous drive -> AP-16-EF-7788 (expect LOW, drive_duration_hours>4)")
    event = make_event(
        event_type="CONTINUOUS_DRIVE",
        confidence=0.9,
        metrics={"drive_duration_hours": 4.3, "last_break_minutes": 260},
        vehicle_registration="AP-16-EF-7788",
        driver_id="9012",
        driver_name="V. Reddy",
        route="NH-16",
        shift_label="Hour 11 of shift",
        speed_kmh=68,
        waypoint_name="Chittoor",
        distance_to_waypoint_km=6,
        lat=13.2172,
        lon=79.1003,
    )
    post_event(event)
    post_evidence(event["event_id"])


def run_noise_events() -> None:
    print("\n[noise] Under-threshold events that should NOT create a violation")
    post_event(
        make_event(
            event_type="DROWSINESS",
            confidence=0.8,
            metrics={"ear": 0.19, "duration_seconds": 0.6},
            vehicle_registration="TN-22-JK-3345",
            driver_id="1111",
            driver_name="K. Das",
            route="NH-48",
            speed_kmh=55,
        )
    )
    post_event(
        make_event(
            event_type="DISTRACTION",
            confidence=0.75,
            metrics={"head_yaw_degrees": 32, "gaze_duration": 1.1},
            vehicle_registration="TN-22-JK-3345",
            driver_id="1111",
            driver_name="K. Das",
            route="NH-48",
            speed_kmh=55,
        )
    )


def print_summary() -> None:
    resp = requests.get(f"{BASE_URL}/api/alerts", params={"status": "active"}, timeout=5)
    resp.raise_for_status()
    alerts = resp.json()
    print(f"\n=== {len(alerts)} active alert(s) ===")
    for alert in alerts:
        print(
            f"  {alert['severity']:<9} {alert['label']:<14} {alert['vehicle_registration']:<16} "
            f"events={alert['event_count']}  {alert['time_ago']}"
        )
    print()


def main() -> None:
    try:
        requests.get(BASE_URL, timeout=3).raise_for_status()
    except requests.RequestException as exc:
        print(f"Backend not reachable at {BASE_URL} — start it first (scripts/start_backend.sh)")
        print(f"  {exc}")
        sys.exit(1)

    print(f"Seeding demo data against {BASE_URL} ...")
    run_drowsiness_sequence()
    run_phone_usage()
    run_distraction_sequence()
    run_continuous_drive()
    run_noise_events()
    print_summary()


if __name__ == "__main__":
    main()
