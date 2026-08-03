"""Tests for POST /api/violations (dms-edge's primary detection path) and the
edge_device_id gating that turns POST /api/events' rule evaluation into a
fallback-only path — see dms-spec/changes/move-violation-detection-to-edge/.

Run from dms-backend/: pytest tests/
"""
import time


def _event_payload(event_id: str, event_type: str, timestamp: float, device_id: str | None, **detection_extra):
    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "detection": {"type": event_type, **detection_extra},
        "context": {"vehicle_registration": "EDGE-DEMO-001"},
        "device": {"device_id": device_id} if device_id else {},
    }


def _violation_payload(violation_id: str = "viol_edge_001"):
    return {
        "violation_id": violation_id,
        "violation_type": "DROWSINESS_PATTERN",
        "severity": "CRITICAL",
        "status": "ACTIVE",
        "event_count": 3,
        "trigger_event_ids": ["e1", "e2", "e3"],
        "first_event_timestamp": time.time() - 20,
        "last_event_timestamp": time.time(),
        "recommended_action_text": "3rd micro-sleep in 2.0 min. Advise driver to pull over safely.",
        "context": {"vehicle_registration": "EDGE-DEMO-001"},
        "vehicle": {"speed_kmh": 68.0, "is_moving": True},
        "alarm": {
            "fired_at": time.time(),
            "message": "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
            "driver_ack_latency_seconds": 5.2,
            "speed_before_kmh": 68.0,
            "speed_after_kmh": 40.0,
        },
    }


def test_receive_violation_creates_alert_visible_on_fleet_api(client):
    resp = client.post("/api/violations", json=_violation_payload())
    assert resp.status_code == 200
    assert resp.json() == {"violation_id": "viol_edge_001", "status": "stored"}

    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["id"] == "viol_edge_001"
    assert alerts[0]["violation_type"] == "DROWSINESS_PATTERN"
    assert alerts[0]["severity"] == "CRITICAL"


def test_receive_violation_upserts_growing_violation_not_duplicate(client):
    client.post("/api/violations", json=_violation_payload())
    payload = _violation_payload()
    payload["event_count"] = 4
    payload["trigger_event_ids"] = ["e1", "e2", "e3", "e4"]
    resp = client.post("/api/violations", json=payload)
    assert resp.status_code == 200

    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["event_count"] == 4


def test_receive_violation_detail_includes_in_cabin_response(client):
    client.post("/api/violations", json=_violation_payload())
    detail = client.get("/api/alerts/viol_edge_001").json()
    assert detail["in_cabin_response"]["driver_ack_latency_seconds"] == 5.2
    assert detail["in_cabin_response"]["alarm_message"] == "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY."
    assert detail["recommended_action"]["text"].startswith("3rd micro-sleep")


def test_events_from_edge_equipped_vehicle_do_not_trigger_fallback_rule_engine(client):
    now = time.time()
    for i in range(3):
        resp = client.post(
            "/api/events",
            json=_event_payload(f"ev{i}", "DROWSINESS", now + i * 10, device_id="edge-001"),
        )
        assert resp.status_code == 200
        assert resp.json()["violations_triggered"] == []

    assert client.get("/api/alerts").json() == []


def test_events_from_edge_less_vehicle_still_trigger_fallback_rule_engine(client):
    now = time.time()
    for i in range(3):
        resp = client.post(
            "/api/events",
            json=_event_payload(f"fb{i}", "DROWSINESS", now + i * 10, device_id=None),
        )
        assert resp.status_code == 200

    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["violation_type"] == "DROWSINESS_PATTERN"
