---
name: dms-edge-dev
description: >-
  Use when scaffolding, building, or extending the edge/device side of the
  DriverMonitorPOC ("Driver Monitor System" box in the architecture diagram)
  — an agentic pipeline (Telematics Agent, Behaviour Detection Agent,
  Violation Detection Agent, Alarm Agent, Cloud Hub Agent) that wraps the
  existing `specs/DriverMonitorPOC-main` camera-based behaviour-detection
  app, evaluates violation rules locally against a sliding window in a
  local SQLite store, fires in-cabin alarms, ingests simulated telemetry
  from the Fleet Simulator, and pushes finished events/violations/evidence
  to the dms-backend Inject API. Triggers on requests like "build the edge
  agent", "add the Telematics Agent", "add the violation detection agent to
  the edge", "integrate DriverMonitorPOC-main", "wire up the Cloud Hub
  agent", "push events to the backend from the edge", "dockerize
  dms-edge", "set up the dms-edge folder", or anything about the edge/DMS
  side of the driver monitor POC.
---

# DMS Edge — Driver Monitor System (Edge/Device Side)

Builds the edge-side of the DriverMonitorPOC: the code that runs on the in-vehicle device (board simulating the Renesas R-Car unit, per `https://github.com/raviR-lab/DriverMonitorPOC/blob/main/DEPLOY.md`) inside the "Driver Monitor System" box of `specs/POC_ARCHITECTURE_WORKBENCH.drawio` / `specs/POC_ARCHITECTURE.drawio`.

**This component is this POC's core selling point.** The differentiator being demoed is *local AI analytics and an agentic framework running on the vehicle* — not a camera that streams raw events for a smarter cloud to grade. That's why violation detection (not just behaviour detection) lives here: see "Violation Detection Agent" below and `dms-spec/changes/move-violation-detection-to-edge/` for the full rationale.

**Read `.claude/skills/dms-agentic-architecture/SKILL.md` first.** This component is built as five agents (Telematics Agent, Behaviour Detection Agent, Violation Detection Agent, Alarm Agent, Cloud Hub Agent) conforming to that doc's shared `BaseAgent` contract — the architecture, naming, and boundaries here follow that doctrine and the drawio diagrams directly, not an ad hoc structure invented per-skill.

Unlike `dms-backend`/`dms-ui`, the CV detection logic is **not built from scratch** — a complete, working detection app already exists at `https://github.com/raviR-lab/DriverMonitorPOC/blob/main/`. This skill's job is agentification and integration (wrap it, add local rule evaluation on top, wire it to `dms-backend` and the Fleet Simulator), not reimplementing the CV pipeline.

## Context to read first

Before writing code, skim these files in the repo (paths relative to repo root):
- `.claude/skills/dms-agentic-architecture/SKILL.md` — the shared `BaseAgent` contract, the agent inventory, and why the five-agent split exists
- `dms-spec/changes/move-violation-detection-to-edge/design.md` and `explore.md` — the architecture decision that moved violation detection here, the alternatives considered for the Behaviour Detection ↔ Violation Detection integration mechanism, and the exact `POST /api/violations` contract sketch
- `dms-spec/specs/violation-detection/spec.md` — the precise rule logic to port (drowsiness/phone/distraction/continuous-drive thresholds, the "growing violations" behavior, simulated in-cabin response) — currently documents `dms-backend`'s implementation; port its behavior faithfully, don't redesign the rules
- `specs/POC_ARCHITECTURE_WORKBENCH.drawio` (page 2) / `specs/POC_ARCHITECTURE.drawio` / `specs/Updated_POC_ARCHITECTURE.png` — the box diagrams this skill implements: **Telematics Unit → Telematics Agent**, **Camera → Behaviour Detection Agent**, both → Local Storage / Videos/Images, → **Violation Detection** → **Alarms** + **Cloud Hub** → Inject API / SFTP
- `https://github.com/raviR-lab/DriverMonitorPOC/tree/main/specs/DriverMonitorPOC-main` — the reference implementation this skill vendors in. See the breakdown below before touching anything.
- `dms-backend/app/rule_agents/violation_rules.py`, `notification_rules.py`, `app/schemas.py`, `app/api/inject_api.py` — the **actual, running** rule logic and Inject API contract. More authoritative than `specs/VIOLATION_AND_EVIDENCE_MODELS.md`, which `dms-backend` already deviates from in places.
- `.claude/skills/fleet-simulator-dev/SKILL.md` and `specs/FLEET_SIMULATOR_SPEC.md` — the Telematics Agent's data source. The simulator publishes GPS/telemetry updates *to* this component's Telematics Agent (see "Telematics Agent" below) — it is not a rebuild target here.

**Key decisions already made**: this runs on a board/laptop for the POC. No AWS, no cloud DB, no S3. `dms-edge` now has its own local SQLite store for real-time rule evaluation (new); `dms-backend` (SQLite + local evidence folder) remains the fleet-wide persistence/dashboard layer and receives the edge's finished events + violations, plus still runs its own rule engine as a fallback for vehicles with no edge device.

## Reference implementation: `specs/DriverMonitorPOC-main/` (use this, don't rebuild it)

A complete, already-working camera-based DMS built by an AI/CV specialist — MediaPipe Face Mesh + YOLOv8n phone detection, time-based (frame-rate-independent) event windows, per-event cooldowns, template-based alerts, and a Flask+SSE stub UI. **Treat its detection logic as frozen.** If a change to `src/dms.py` or `src/alert_templates.py` seems necessary, stop and confirm with the user first — the Behaviour Detection Agent *wraps* this code, it doesn't modify it.

| File | What it does | Touch it? |
|---|---|---|
| `main.py` | Entry point: opens a video file (or camera — Phase 2, deferred), runs the per-frame loop, starts the SSE UI thread | Adapt minimally to instantiate the agents below and route frames through `BehaviourDetectionAgent` instead of calling `dms.process_frame()` directly, and to register `ViolationDetectionAgent` in the `EventSink` fan-out — integration glue, not core-logic change |
| `src/dms.py` | Core pipeline: `DriverMonitoringSystem.process_frame()` — YOLOv8n phone detection every Nth frame, MediaPipe EAR/MAR/head-pose, time-based `_Window` state machines, per-event cooldowns, `TripStats`, HUD drawing | **Don't touch** |
| `src/events.py` | `DMSEvent` dataclass — the *internal* event shape and `EventType`/`Severity`/`Audience` enums | Don't touch |
| `src/alert_templates.py` | Template-based alert text (no LLM), `severity_for()`/`audience_for()` routing, `speak()` TTS stub — the **immediate, per-event, tier-1** in-cabin alert | Don't touch |
| `src/config.py` | Every detection threshold, model paths, `UI_HOST`/`UI_PORT` | **Extend, don't replace** — new agent config (backend URL, vehicle identity, telematics ingest port, local DB path, violation rule thresholds) goes here too |
| `src/ui_server.py` | Flask + SSE bridge + a minimal stub HTML dashboard | Keep as the local, offline, in-cabin view |
| `models/yolov8n_int8.onnx` (+ fp16/fp32/.pt) | Pre-trained YOLOv8n weights | Copy into `dms-edge/models/` |
| `DEPLOY.md` | Renesas R-Car (ARM64, 4 GB) deployment notes | Applies to the Docker section below too |

## The five agents this skill builds

### Telematics Agent (`agents/telematics_agent.py`)

Implements `BaseAgent[TelemetryUpdate, VehicleState]`. Receives GPS/telemetry updates and holds the **latest known vehicle state** (speed, lat/lon, heading, status) for the Behaviour Detection/Violation Detection/Cloud Hub agents to read — it does not read a real telematics bus in the POC, it's fed by the **Fleet Simulator**.

- Exposes a small, dedicated HTTP ingestion endpoint — don't bolt this onto `src/ui_server.py` (that file is frozen); run a minimal Flask/`http.server` listener of its own, e.g. `POST /telemetry` on `TELEMATICS_INGEST_PORT` (new config value, e.g. `5060`).
- Fleet Simulator's `HttpPublisher` (see `fleet-simulator-dev`) targets this endpoint per simulated truck: `http://<edge-host>:5060/telemetry`, using the GPS update schema from `specs/FLEET_SIMULATOR_SPEC.md`.
- Thread-safe latest-state store (a lock-protected dict/dataclass is enough — this is a POC, not a time-series store).
- `run(update)` validates + normalizes the incoming payload, updates the stored latest state, returns it. No history is kept beyond "latest" unless a user asks for more.
- **Vehicle identity correlation**: the truck ID the Fleet Simulator uses for a given truck must equal this edge instance's configured `EDGE_VEHICLE_REGISTRATION` (new `src/config.py` value) — that's how one truck's GPS stream and one edge device's behaviour events end up on the same `dms-backend` vehicle row.

### Telematics Simulator (`agents/telematics_simulator.py`) — new, minimal, `dms-edge`-local

Not one of the five agents above and not a `BaseAgent` pipeline node — it's an alternate, in-process **data source** for the Telematics Agent, standing in for the Fleet Simulator when nothing external is publishing telemetry. It exists for the case the workbench diagram's sticky note on "Telematics Unit" calls out directly: for a laptop/office demo the edge board itself is stationary, not a moving truck, but the Alarm Agent's `recommended_action_text` and the Cloud Hub Agent's location fields still need real-looking GPS/speed to reference.

- Two motion models, selected by whether `--vehicle-config`'s optional `route` block is present: **route model** (from/to lat-lon, avg speed km/h, duration secs) derives GPS position from accumulated speed (haversine total distance + linear interpolation by distance-fraction) — the GPS/speed tandem, so position and speed can never numerically contradict each other; **fallback model** (no `route`) loops a small canned set of lat/lon waypoints along a "highway" with an independent oscillating speed profile. Both call the Telematics Agent's `run()` directly on a timer (e.g. every 1–2s) — no HTTP hop, no second process, nothing extra for a demo operator to start. Also simulates RPM (idle/cruise bands tied to speed).
- Toggle with a `TELEMATICS_SOURCE` config value in `src/config.py`: `"simulator"` (default — this stub drives the Telematics Agent) or `"http"` (a real Fleet Simulator instance is POSTing to `/telemetry` instead). Flipping this one value is the only difference between "demo on a laptop" and "wired to the (simulated) fleet."
- `--vehicle-config <path.json>` (see `src/vehicle_config.py`) supplies the truck ID used by the simulator plus the optional `route` block — see `dms-spec/changes/add-telematics-simulator-and-vehicle-config/design.md`.
- **Do not grow this toward the Fleet Simulator's feature set** (multiple trucks, real geofence logic) — see `dms-agentic-architecture`'s "Telematics data" section. If a demo needs more than one truck simultaneously, that's a signal to stand up `fleet-simulator-dev`, not to expand this stub. The single-truck from/to route interpolation above is still a straight-line stub — not real road routing.

### Behaviour Detection Agent (`agents/behaviour_detection_agent.py`)

Implements `BaseAgent[Frame, list[DMSEvent]]`. A thin wrapper around `DriverMonitoringSystem` (`src/dms.py`) — holds a `DriverMonitoringSystem` instance, `run(frame)` calls `process_frame()` and returns whatever `DMSEvent`s were emitted during that call. No detection logic lives here — it is 100% delegation to the frozen reference code.

Every `DMSEvent` it produces fans out to **multiple sinks** via the existing `EventSink` extension point in `main.py`: the file logger, the SSE sink (unchanged), `CloudHubAgent` (unchanged), and now **`ViolationDetectionAgent`** (new — see below). This fan-out is exactly how the Behaviour Detection Agent and Violation Detection Agent interconnect; see "How Behaviour Detection Agent and Violation Detection Agent talk to each other" for the reasoning.

### Violation Detection Agent (`agents/violation_detection_agent.py`) — **new, core to this POC's story**

Implements `BaseAgent[DMSEvent, Violation | None]`. This is the agent that makes "local AI analytics at the edge" a real, demoable claim instead of a slide bullet — it evaluates the same rule set `dms-backend` used to run, but locally, in real time, with no cloud round-trip required to know a violation occurred.

Port the rule logic from `dms-backend/app/rule_agents/violation_rules.py`, faithfully matching `dms-spec/specs/violation-detection/spec.md`'s Requirement blocks — same 4 rules, same "growing violations, not duplicates" behavior (one `ACTIVE` violation per type per vehicle; new matching events update `event_count`/`trigger_event_ids`/`recommended_action_text` in place rather than creating a duplicate), same simulated-on-first-alarm in-cabin response fields. This is a *port*, not a redesign — don't invent new thresholds or severities.

Needs a **sliding time window per event type** (e.g. "3 DROWSINESS events in the last 120 seconds") and **persistent ACTIVE-violation state** across calls — both require the new local storage below; don't try to hold this in a bare in-memory list, since a demo-crashing restart would silently reset the window.

### Alarm Agent (`agents/alarm_agent.py`) — **new**

Implements `BaseAgent[Violation, Alarm]`. On a new-or-updated `Violation` from the Violation Detection Agent, builds an `Alarm` (severity-appropriate message + `recommended_action_text`, same deterministic-template approach `dms-backend` uses today — no LLM) and fires it. This is the **escalation tier**: distinct from `src/dms.py`'s existing `speak()` stub, which is the **immediate tier** (fires on the very first qualifying detection, independent of pattern evaluation, and stays exactly as-is — frozen). Two tiers, both local:

1. **Immediate** (`src/dms.py`'s `speak()`, unchanged): "eyes just closed" — fires the instant `DriverMonitoringSystem` detects it, before any agent above even runs.
2. **Escalation** (this agent, new): "3rd micro-sleep in 2 minutes — pull over" — fires once the Violation Detection Agent confirms a genuine pattern, carries the same `recommended_action_text` style the backend generates today (e.g. referencing a waypoint from the Telematics Agent's latest vehicle state).

### Cloud Hub Agent (`agents/cloud_hub_agent.py`)

Implements `BaseAgent[DMSEvent, None]` (fire-and-forget by design, matching the reference app's style) — **plus** a second responsibility now: pushing finished violations. On each `DMSEvent`:
1. Reads the Telematics Agent's latest vehicle state.
2. Maps `DMSEvent` + vehicle state → `dms-backend`'s nested Event JSON (see Data flow contract below).
3. `POST {BACKEND_URL}/api/events`, short timeout (~0.5s) so a slow/down backend never blocks frame processing. This push is now primarily an **audit trail** (and future Phase 3 analytics input) — `dms-backend` skips re-running its own rule evaluation for events from vehicles with an edge device (see `dms-backend-dev`).
4. For events worth an evidence frame (`PHONE_USAGE`, `DROWSINESS`), also `POST {BACKEND_URL}/api/evidence` (multipart, `event_id` + `file`).

On each new-or-updated `Violation` from the Alarm Agent:
5. `POST {BACKEND_URL}/api/violations` (new endpoint — see `dms-spec/changes/move-violation-detection-to-edge/design.md` for the exact payload shape), same short-timeout, fire-and-forget style, so `dms-ui` shows what the edge already decided.

On failure (either push): log and drop for the POC — don't build a retry queue speculatively.

## How Behaviour Detection Agent and Violation Detection Agent talk to each other

This was an open design question (see `dms-spec/changes/move-violation-detection-to-edge/explore.md` for the full comparison) — resolved as follows, and this is the mechanism to actually build:

**Default: in-process `EventSink` registration.** `ViolationDetectionAgent` registers as one more sink in `main.py`'s existing multi-sink fan-out — the same extension point the file logger, SSE sink, and Cloud Hub Agent already use. A `DMSEvent` becomes a direct, synchronous function call (`violation_detection_agent.run(event)`), same process, no new port, no new server to start for a demo. This is the right default for a POC: lowest latency, zero new infrastructure, and it's exactly the pattern this codebase already uses for every other sink.

**Documented upgrade path, not built now: local HTTP loopback.** If `ViolationDetectionAgent` ever needs to run as its own independently-restartable process (e.g. to demo it as a standalone "agent service," or because it's moved to a separate container), swap the in-process call for a `POST http://127.0.0.1:<port>/internal/events` call — same short-timeout, fire-and-forget style already used for the Cloud Hub Agent's push to `dms-backend`, so the *pattern* is already proven in this codebase even though it isn't used for this particular link yet. Don't build this unless asked; it's strictly more moving parts (one more process, one more port, one more failure mode) for the same behavior a function call already gives you at this scale.

**Not chosen: a local message queue/broker.** Considered and rejected in `explore.md` — real overkill for a single-camera, single-process POC; this repo's own philosophy is explicit about not adding infrastructure a demo doesn't need.

## New: Local Storage (`storage/`)

A small SQLite store, local to this edge device — the edge equivalent of `dms-backend/storage/dms.db`, same tech (SQLAlchemy + SQLite) so nothing new to learn. Needed because the Violation Detection Agent's rules require history a single incoming event can't carry on its own:

- **`events` table**: every `DMSEvent` the Behaviour Detection Agent has produced (type, confidence, metrics, timestamp), indexed on `(type, timestamp)` — this is what makes "3 DROWSINESS events in the last 120 seconds" a fast, simple query instead of something held awkwardly in memory.
- **`violations` table**: mirrors the relevant fields of `dms-backend`'s `Violation` model closely enough to port the "growing violations" logic verbatim (`violation_type`, `status`, `event_count`, `trigger_event_ids`, timestamps, `recommended_action_text`) — this is what lets a 4th matching event update the existing `ACTIVE` violation instead of creating a duplicate.

Single-vehicle scope only — this is not a fleet-wide store (that's still `dms-backend`'s job), so the schema is much smaller than the backend's. Gitignore the generated `.db` file, same convention as everywhere else in this repo.

## Telematics & GPS — where the data actually originates

GPS and telematics (speed, heading, engine state, geofences) are meant to be *generated* by the standalone **Fleet Simulator** (`.claude/skills/fleet-simulator-dev/SKILL.md`) long-term — `dms-edge` doesn't read a real telematics bus. But that component doesn't exist on disk yet, and per the workbench diagram's sticky note, the edge board is typically stationary during demos anyway — so day to day, the in-process **Telematics Simulator** (`agents/telematics_simulator.py`, see above) is what actually drives it. Either way, `dms-edge` **does** have a Telematics Agent per the drawio: its job is to *receive* updates (over HTTP from the Fleet Simulator, or in-process from the Telematics Simulator) and make the latest vehicle state available to the rest of the edge pipeline, exactly like it would if a real telematics unit were connected. This is what lets the Alarm Agent's `recommended_action_text` reference a real (simulated) waypoint/distance, and the Cloud Hub Agent attach real (simulated) speed/GPS to events and violations instead of leaving those fields empty.

## Architecture this skill implements

```
Fleet Simulator (standalone, not yet built) ──HTTP──▶┐
Telematics Simulator (in-process, dms-edge-local,     ├─▶ Telematics Agent ──┐
  default until Fleet Simulator exists) ─────────────▶┘   (agents/telematics_agent.py)      │ latest vehicle state
                                                                                               │ (read, not pushed)
https://github.com/raviR-lab/DriverMonitorPOC/main, vendored, unmodified                            │
┌──────────────────────────────────────────────────────────────────┐        │
│ main.py ─▶ Behaviour Detection Agent ─▶ DriverMonitoringSystem      │        │
│            (agents/behaviour_detection_agent.py)   (src/dms.py)     │        │
│                    │ DMSEvent (EventSink fan-out, in-process)       │        │
│        ┌───────────┼───────────────────┬─────────────────┐         │        │
│        ▼           ▼                   ▼                 ▼         │        │
│  file logger   SSE/local UI   Violation Detection Agent   Cloud Hub Agent ◀──┘
│                                (agents/violation_detection_agent.py)│
│                                        │ read/write                │
│                                        ▼                            │
│                              Local Storage (storage/local.db)       │
│                                        │ Violation (new/updated)    │
│                                        ▼                            │
│                                  Alarm Agent (agents/alarm_agent.py)│
│                                        │ in-cabin alarm (tier 2)    │
│                                        ▼                            │
│                                     Driver          also ──▶ Cloud Hub Agent
└───────────────────────────────────────────────────────────────────┘  │
                                                                          ▼
                                                          dms-backend Inject API
                                                    POST /api/events (audit trail)
                                                    POST /api/evidence
                                                    POST /api/violations (NEW)
```

- **Behaviour Detection + immediate local alarm**: `src/dms.py` + `src/alert_templates.py`, wrapped by `BehaviourDetectionAgent`. The `speak()` stub is the tier-1 "immediate local in-cabin alarm, independent of the cloud round-trip" — it fires before any other agent runs.
- **Violation Detection + escalation alarm**: the tier-2 story, and the actual selling point — see the two sections above.

## Folder structure to create

Scaffold this inside the repo root (sibling to `specs/`) by **vendoring `https://github.com/raviR-lab/DriverMonitorPOC/tree/main` in as the `src/` tree**, then adding the agentic layer on top:

```
dms-edge/
├── main.py                       # copied from DriverMonitorPOC-main, minimally adapted (see table above)
├── src/                          # vendored, unmodified except config.py extensions
│   ├── __init__.py
│   ├── config.py                 # copied + extended: EDGE_VEHICLE_REGISTRATION, BACKEND_URL, TELEMATICS_INGEST_PORT, LOCAL_DB_PATH, violation rule thresholds
│   ├── events.py                 # copied, unchanged
│   ├── alert_templates.py        # copied, unchanged
│   ├── dms.py                    # copied, unchanged
│   └── ui_server.py              # copied, unchanged
├── agents/                       # the agentic layer this skill builds (see dms-agentic-architecture)
│   ├── __init__.py
│   ├── base.py                   # BaseAgent Protocol (see parent skill) — duplicated here, not imported cross-repo
│   ├── telematics_agent.py       # HTTP ingest from Fleet Simulator, holds latest vehicle state
│   ├── telematics_simulator.py   # NEW — in-process synthetic GPS/speed loop, default TELEMATICS_SOURCE until Fleet Simulator exists
│   ├── behaviour_detection_agent.py  # thin wrapper around src/dms.py's DriverMonitoringSystem
│   ├── violation_detection_agent.py  # NEW — ported rule engine, reads/writes storage/
│   ├── alarm_agent.py                # NEW — Violation -> Alarm, escalation-tier in-cabin alert
│   └── cloud_hub_agent.py        # DMSEvent + Violation + vehicle state -> dms-backend; POST /api/events, /api/evidence, /api/violations
├── storage/                       # NEW — local SQLite for the sliding-window rule state
│   ├── __init__.py
│   ├── database.py                # SQLite engine + session (SQLAlchemy) — same pattern as dms-backend
│   ├── models.py                  # local Event/Violation ORM models (small subset of dms-backend's schema)
│   └── local.db                   # gitignored, generated
├── models/                       # copied from DriverMonitorPOC-main/models/ (yolov8n_int8.onnx etc.)
├── scripts/                      # copied: run_demo.sh, bench_yolo.py, extract_frames.py, report.py
├── videos/                       # demo input, e.g. dataset.mp4 — gitignore the actual video file
├── data/calib/                   # int8 calibration set, if present — copied
├── logs/                         # events.jsonl — gitignore
├── output/                       # annotated output videos + benchmarks — gitignore
├── tests/
├── requirements.txt              # DriverMonitorPOC-main's requirements.txt + `requests` + `sqlalchemy` (+ `flask` already present)
├── Dockerfile                    # optional — see "Optional: Docker" below
├── .dockerignore                 # optional
├── DEPLOY.md                     # copied from DriverMonitorPOC-main — board deployment notes still apply
└── README.md
```

Run once when scaffolding (copy the reference app, don't recreate it):
```bash
mkdir -p dms-edge
cp -r https://github.com/raviR-lab/DriverMonitorPOC/tree/main/main.py https://github.com/raviR-lab/DriverMonitorPOC/tree/main/src https://github.com/raviR-lab/DriverMonitorPOC/tree/main/models \
      https://github.com/raviR-lab/DriverMonitorPOC/tree/main/scripts https://github.com/raviR-lab/DriverMonitorPOC/tree/main/requirements.txt \
      https://github.com/raviR-lab/DriverMonitorPOC/tree/main/DEPLOY.md dms-edge/
mkdir -p dms-edge/agents dms-edge/storage dms-edge/videos dms-edge/tests
touch dms-edge/agents/__init__.py dms-edge/storage/__init__.py
```

Add to (or create) the repo `.gitignore`:
```
dms-edge/.venv/
dms-edge/__pycache__/
dms-edge/logs/
dms-edge/output/dms_out_*.mp4
dms-edge/data/calib/
dms-edge/videos/*.mp4
dms-edge/storage/local.db
```

## Tech stack

Same as `https://github.com/raviR-lab/DriverMonitorPOC/tree/main/requirements.txt` — `opencv-python`, `numpy`, `mediapipe==0.10.14` (pinned — the legacy `solutions.face_mesh` API was removed in 0.10.20+), `ultralytics`, `flask` (already a dependency — reuse it for the Telematics Agent's tiny listener instead of adding a second web framework) — plus `requests` for the Cloud Hub Agent and `sqlalchemy` for the new local store (same ORM `dms-backend` already uses — one pattern to know, not two).

## Data flow contract (Cloud Hub Agent)

`dms-backend`'s actual Inject API (`dms-backend/app/schemas.py`) expects a **nested** Event shape; `DMSEvent` is **flat**. The Cloud Hub Agent's mapping:

| `dms-backend` field | From | Notes |
|---|---|---|
| `event_id` | `DMSEvent.id` | |
| `timestamp` | `DMSEvent.timestamp` | |
| `detection.type` | `DMSEvent.event_type.value` | Forward `DROWSINESS`, `PHONE_USAGE`, `DISTRACTION`, `CONTINUOUS_DRIVE` (the 4 types the Violation Detection Agent has rules for) and optionally `YAWN`/`NO_FACE` (stored, no violation triggered). **Drop** `DRIVER_QUESTION`/`DRIVER_ANSWER`/`SYSTEM` |
| `detection.confidence` | `DMSEvent.metrics.get("confidence", 1.0)` | Only `PHONE_USAGE` carries a real confidence; default `1.0` elsewhere |
| `detection.metrics` | `DMSEvent.metrics` | Pass through |
| `context.vehicle_registration` | `EDGE_VEHICLE_REGISTRATION` config | **Required** by `dms-backend`; must match the Fleet Simulator's truck ID for this vehicle |
| `context.frame_index`, `context.camera_id` | `DMSEvent.frame_index`, static config | |
| `context.lat` / `lon` / `route` / `waypoint_name` / `distance_to_waypoint_km` | **Telematics Agent's latest vehicle state** | |
| `vehicle.speed_kmh`, `vehicle.is_moving` | **Telematics Agent's latest vehicle state** | |
| `device.device_id`, `device.device_model`, etc. | static config | e.g. `"renesas_rcar"` — `dms-backend` stores this as `vehicle.edge_device_id`, which is exactly what tells it this vehicle has an edge device and to skip its own fallback rule evaluation |

**New — Violation push**: when the Alarm Agent produces a new-or-updated `Violation`, `CloudHubAgent` maps it to the `ViolationIn`/`AlarmIn` shape defined in `dms-spec/changes/move-violation-detection-to-edge/design.md` (`violation_id`, `violation_type`, `severity`, `status`, `event_count`, `trigger_event_ids`, timestamps, `recommended_action_text`, reused `context`/`vehicle` shapes, plus a nested `alarm` object with `fired_at`/`message`/simulated ack+speed fields) and `POST`s it to `POST {BACKEND_URL}/api/violations`.

Push flow:
1. `BehaviourDetectionAgent` emits a `DMSEvent` (via the `EventSink` fan-out — file logger, SSE sink, `ViolationDetectionAgent`, `CloudHubAgent`, all in-process).
2. `ViolationDetectionAgent.run(event)` writes the event to local storage, evaluates the rules against the sliding window, returns a `Violation` if one triggered/updated.
3. If a `Violation` came back, `AlarmAgent.run(violation)` builds the `Alarm`, fires the escalation-tier in-cabin alert, and hands the `Violation`+`Alarm` to `CloudHubAgent`.
4. `CloudHubAgent` maps and pushes: `POST /api/events` (always, audit trail), `POST /api/evidence` if applicable, `POST /api/violations` (only when a violation came back from step 2–3).
5. Log and drop on failure — durability queue only if explicitly requested.

## When building

- Reuse `https://github.com/raviR-lab/DriverMonitorPOC/tree/main` file-for-file inside `src/`; the new code is `dms-edge/agents/` (now five agents) and `dms-edge/storage/`.
- Port the Violation Detection Agent's rules from `dms-backend/app/rule_agents/violation_rules.py` and `dms-spec/specs/violation-detection/spec.md` faithfully — same thresholds, same growing-violations behavior. This is a port, not a chance to redesign the rules.
- Build and verify the Telematics Agent's ingestion endpoint against a *manual* `curl -X POST` before wiring the real Fleet Simulator to it.
- Start with `--video path/to/dataset.mp4`, not a live camera — `main.py` already gates `--camera` as Phase 2.
- Ship the events-only path first (`POST /api/events`), verify against a running `dms-backend`, then add local violation detection, then `/api/violations`, then `/api/evidence`.
- Default the Behaviour Detection ↔ Violation Detection integration to the in-process `EventSink` registration (see above) — don't reach for the local-HTTP alternative unless the user specifically wants Violation Detection Agent independently deployable/restartable.
- See `.claude/skills/dms-agentic-architecture/SKILL.md` for the shared `BaseAgent` shape, naming conventions, and why nothing here should depend on a message broker or `langgraph` yet.

## Optional: Docker

The primary/default workflow is the local venv, per `DEPLOY.md`. Docker is an **optional alternative** — build it only if asked, not speculatively. Per the current deployment design: **dockerize `dms-edge` as its own image/service, grouped under the `dms-edge` name, targeting deployment on the on-board device (OBD/board)** — not just the dev laptop.

- `Dockerfile`: install `ffmpeg`, `libgl1`, `libglib2.0-0` (native deps for `opencv-python`/`mediapipe`/`ultralytics`) before `pip install -r requirements.txt`. For an ARM64 target board (per `DEPLOY.md`), build/pull an `arm64` base image or use `docker buildx`; prefer `models/yolov8n_int8.onnx` over `.pt`.
- No display in a container — always `--no-display` (headless).
- Bind-mount `videos/` read-only for the demo input; mount `storage/` as a volume so the local SQLite DB survives container restarts; don't build live-camera device passthrough unless moving to Phase 2.
- `.dockerignore`: exclude `.venv/`, `__pycache__/`, `logs/`, `output/`, `data/calib/`.
- Expose both the app's own port and `TELEMATICS_INGEST_PORT` if the Fleet Simulator needs to reach this container.
- Pairs with the root `docker-compose.yml` as a `dms-edge` service for an all-in-one laptop demo (point `BACKEND_URL` at `http://backend:8000`, the docker-network service name); remember the real deployment target is the board, not the laptop.
- Pass `BACKEND_URL`, `EDGE_VEHICLE_REGISTRATION`, `TELEMATICS_INGEST_PORT`, and `LOCAL_DB_PATH` as environment variables at run/compose time, not baked into the image.
