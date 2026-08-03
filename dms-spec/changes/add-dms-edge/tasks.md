# Tasks — add-dms-edge

Check items off as they land (verified working, not just written).

## 1. Vendor reference app

- [x] 1.1 Copy `specs/DriverMonitorPOC-main/{main.py,src,models,scripts,requirements.txt,DEPLOY.md}` into `dms-edge/`
- [x] 1.2 Create `dms-edge/{agents,videos,tests}/`, `agents/__init__.py`

## 2. Config

- [x] 2.1 Append `EDGE_VEHICLE_REGISTRATION`, `BACKEND_URL`, `BACKEND_REQUEST_TIMEOUT_SECS`, `TELEMATICS_INGEST_HOST/PORT`, `DEVICE_ID`, `DEVICE_MODEL`, `CAMERA_ID` to `dms-edge/src/config.py`

## 3. Agents

- [x] 3.1 `agents/base.py` — `BaseAgent` Protocol (per dms-agentic-architecture)
- [x] 3.2 `agents/telematics_agent.py` — `TelematicsUpdate`/`VehicleState` dataclasses, Flask `POST /telemetry` listener, lock-protected latest-state store
- [x] 3.3 `agents/behaviour_detection_agent.py` — thin `DriverMonitoringSystem` wrapper, also usable as an `EventSink`
- [x] 3.4 `agents/cloud_hub_agent.py` — `DMSEvent` + `VehicleState` → backend `EventIn` mapping, `POST /api/events` + `/api/evidence`, drop-on-failure

## 4. Wiring

- [x] 4.1 Adapt `dms-edge/main.py`: instantiate the three agents, start Telematics Agent's listener thread, add `CloudHubAgent` to the existing multi-sink fan-out
- [x] 4.2 `requirements.txt` — add `requests`, `onnxruntime` (the latter was missing from the original vendored app too — the ONNX weights in `models/` need it, discovered during verification)

## 5. Docs / hygiene

- [x] 5.1 `dms-edge/README.md` — run instructions, API surface, config table
- [x] 5.2 Root `.gitignore` — add `dms-edge` entries per skill

## 6. Verification

- [x] 6.1 `python main.py --video <sample> --no-display --no-ui` runs end-to-end without error against a synthetic 40-frame test video (no demo video ships in this repo) — YOLO (ONNX Runtime) + MediaPipe both load and run, events flow through the full agent chain to a live `dms-backend`
- [x] 6.2 `curl -X POST localhost:5060/telemetry -d '{...}'` while `main.py` was running updated the stored vehicle state, confirmed via `curl GET localhost:5060/telemetry`
- [x] 6.3 `pytest tests/` — 8/8 pass, headless (no camera/YOLO)
- [x] 6.4 Synthetic `DMSEvent`s pushed through `CloudHubAgent` against the live (Dockerized) `dms-backend`: `PHONE_USAGE` produced a real `HIGH` violation visible via `GET /api/alerts?status=active`; a `DROWSINESS` event's evidence JPG landed in the backend's evidence volume via `POST /api/evidence`
