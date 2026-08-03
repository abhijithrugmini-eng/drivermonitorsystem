"""Unit tests for dms-edge/agents/ — headless, no camera/YOLO/mediapipe dependency.

Run from dms-edge/: pytest tests/
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agents.cloud_hub_agent import CloudHubAgent, FORWARDED_EVENT_TYPES
from agents.telematics_agent import TelematicsAgent, TelemetryUpdate
from src.events import Audience, DMSEvent, EventType, Severity


# ─── TelematicsAgent ─────────────────────────────────────────────────────────

def test_telematics_agent_run_updates_latest_state():
    agent = TelematicsAgent()
    update = TelemetryUpdate(
        truck_id="EDGE-DEMO-001", latitude=34.05, longitude=-118.25,
        speed=72.0, heading=180.0, status="MOVING",
    )

    state = agent.run(update)

    assert state.lat == 34.05
    assert state.lon == -118.25
    assert state.speed_kmh == 72.0
    assert state.is_moving is True
    assert agent.get_latest_state() == state


def test_telematics_agent_stopped_status_is_not_moving():
    agent = TelematicsAgent()
    agent.run(TelemetryUpdate(truck_id="T1", latitude=0.0, longitude=0.0, status="STOPPED"))
    assert agent.get_latest_state().is_moving is False


def test_telematics_agent_http_endpoint_updates_state():
    agent = TelematicsAgent()
    client = agent._app.test_client()

    resp = client.post(
        "/telemetry",
        json={"truckId": "EDGE-DEMO-001", "latitude": 1.0, "longitude": 2.0,
              "speed": 50.0, "heading": 90.0, "status": "MOVING"},
    )
    assert resp.status_code == 200

    debug_resp = client.get("/telemetry")
    assert debug_resp.status_code == 200
    body = debug_resp.get_json()
    assert body["lat"] == 1.0
    assert body["lon"] == 2.0


def test_telematics_agent_http_endpoint_rejects_missing_fields():
    agent = TelematicsAgent()
    client = agent._app.test_client()
    resp = client.post("/telemetry", json={"truckId": "T1"})  # missing lat/lon
    assert resp.status_code == 400


# ─── CloudHubAgent ───────────────────────────────────────────────────────────

def _make_event(event_type: EventType, confidence: float | None = None) -> DMSEvent:
    metrics = {} if confidence is None else {"confidence": confidence}
    return DMSEvent(
        event_type=event_type, severity=Severity.HIGH, audience=Audience.ADMIN,
        message="test", metrics=metrics, frame_index=42,
    )


def test_cloud_hub_agent_maps_event_and_posts_to_backend():
    telematics = TelematicsAgent()
    telematics.run(TelemetryUpdate(truck_id="EDGE-DEMO-001", latitude=10.0, longitude=20.0,
                                    speed=60.0, heading=0.0, status="MOVING"))
    agent = CloudHubAgent(telematics)
    event = _make_event(EventType.PHONE_USAGE, confidence=0.91)

    with patch("agents.cloud_hub_agent.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        agent.run(event)

    assert mock_post.call_count == 1
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert payload["event_id"] == event.id
    assert payload["detection"]["type"] == "PHONE_USAGE"
    assert payload["detection"]["confidence"] == 0.91
    assert payload["context"]["lat"] == 10.0
    assert payload["vehicle"]["speed_kmh"] == 60.0


def test_cloud_hub_agent_drops_undeliverable_event_types():
    telematics = TelematicsAgent()
    agent = CloudHubAgent(telematics)
    event = _make_event(EventType.SYSTEM)

    with patch("agents.cloud_hub_agent.requests.post") as mock_post:
        agent.run(event)

    mock_post.assert_not_called()


def test_cloud_hub_agent_logs_and_drops_on_request_failure(capsys):
    import requests

    telematics = TelematicsAgent()
    agent = CloudHubAgent(telematics)
    event = _make_event(EventType.DROWSINESS)

    with patch("agents.cloud_hub_agent.requests.post", side_effect=requests.RequestException("boom")):
        agent.run(event)  # must not raise

    assert "failed to push event" in capsys.readouterr().out


def _make_violation_and_alarm():
    violation = SimpleNamespace(
        violation_id="viol_abc123",
        violation_type="DROWSINESS_PATTERN",
        severity="CRITICAL",
        status="ACTIVE",
        event_count=3,
        trigger_event_ids_json=["e1", "e2", "e3"],
        first_event_timestamp=100.0,
        last_event_timestamp=120.0,
        recommended_action_text="3rd micro-sleep in 2.0 min. Advise driver to pull over safely.",
    )
    alarm = SimpleNamespace(
        fired_at=120.0,
        message="⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
        driver_ack_latency_seconds=5.2,
        speed_before_kmh=70.0,
        speed_after_kmh=45.0,
    )
    return violation, alarm


def test_cloud_hub_agent_pushes_violation_to_new_endpoint():
    telematics = TelematicsAgent()
    telematics.run(TelemetryUpdate(truck_id="EDGE-DEMO-001", latitude=10.0, longitude=20.0,
                                    speed=60.0, heading=0.0, status="MOVING"))
    agent = CloudHubAgent(telematics)
    violation, alarm = _make_violation_and_alarm()

    with patch("agents.cloud_hub_agent.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        agent.push_violation(violation, alarm)

    assert mock_post.call_count == 1
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/api/violations")
    payload = kwargs["json"]
    assert payload["violation_id"] == "viol_abc123"
    assert payload["violation_type"] == "DROWSINESS_PATTERN"
    assert payload["event_count"] == 3
    assert payload["trigger_event_ids"] == ["e1", "e2", "e3"]
    assert payload["context"]["lat"] == 10.0
    assert payload["vehicle"]["speed_kmh"] == 60.0
    assert payload["alarm"]["message"] == "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY."
    assert payload["alarm"]["driver_ack_latency_seconds"] == 5.2


def test_cloud_hub_agent_push_violation_logs_and_drops_on_failure(capsys):
    import requests

    telematics = TelematicsAgent()
    agent = CloudHubAgent(telematics)
    violation, alarm = _make_violation_and_alarm()

    with patch("agents.cloud_hub_agent.requests.post", side_effect=requests.RequestException("boom")):
        agent.push_violation(violation, alarm)  # must not raise

    assert "failed to push violation" in capsys.readouterr().out


def test_forwarded_event_types_matches_skill_contract():
    assert FORWARDED_EVENT_TYPES == {
        EventType.DROWSINESS, EventType.YAWN, EventType.DISTRACTION,
        EventType.PHONE_USAGE, EventType.NO_FACE, EventType.CONTINUOUS_DRIVE,
    }
