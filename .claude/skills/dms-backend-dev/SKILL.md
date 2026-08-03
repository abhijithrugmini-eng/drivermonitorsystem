---
name: dms-backend-dev
description: >-
  Use when scaffolding, building, or extending the DriverMonitorPOC backend
  ("DMS Back End" box in the architecture diagram) that runs locally on a
  laptop — the FastAPI Inject API that ingests events, evidence, and
  edge-computed violations, an SFTP or upload receiver for video/image
  evidence, a local SQLite database (replacing DynamoDB/cloud DB), a local
  evidence folder (replacing an S3 bucket), a fallback rule engine for
  fleet vehicles with no edge device, a notifications dispatcher, and the
  REST/WebSocket Fleet API consumed by the React dashboard. Triggers on
  requests like "build the DMS backend", "set up the FastAPI server for
  driver monitor", "add the fallback violation rule agent", "wire up the
  Inject API", "add the violations ingestion endpoint", "create the fleet
  API for the dashboard", "add notifications", or anything about the
  dms-backend / DMS Back End component.
---

# DMS Backend — DMS Back End (runs on laptop)

Builds the backend of the DriverMonitorPOC: the "DMS Back End" box in the architecture diagram. Per team decision, this runs entirely on a laptop for the POC — no AWS, no managed cloud database, no S3. It's a capability showcase, so favor the simplest thing that works end-to-end over production hardening.

**This is no longer the primary place violations get decided.** Per `dms-spec/changes/move-violation-detection-to-edge/`, real-time violation detection moved to `dms-edge` — that's the POC's selling point ("local AI analytics + agentic framework" running on the vehicle, not just a smarter cloud). This component's rule engine (`app/rule_agents/`) survives as **two things**: (1) a fallback path for fleet vehicles that have no edge device installed, and (2) the seed for a future Phase 3 idea — an LLM-based data-analytics agent over historical events/violations for fleet-wide pattern mining and coaching insights (not real-time detection, not built yet, not in scope until explicitly asked). Don't delete `app/rule_agents/` — it's still live code, just no longer the default path.

**Read `.claude/skills/dms-agentic-architecture/SKILL.md` first.** The fallback rule-evaluation and notification logic here is still built as agents (Violation Detection Agent, Alarm Agent — plus a Notification Agent step) conforming to that doc's shared `BaseAgent` contract, matching `specs/POC_ARCHITECTURE_WORKBENCH.drawio`'s "Voilation Detection" / "Alarms" / "Notifications" boxes. Name the classes accordingly (see below), not generic names like `RuleEngine`.

## Context to read first

Before writing code, skim these files in the repo (paths relative to repo root):
- `.claude/skills/dms-agentic-architecture/SKILL.md` — the shared `BaseAgent` contract and the canonical agent inventory (Violation Detection Agent / Alarm Agent now live primarily in `dms-edge`; this component keeps a fallback copy)
- `dms-spec/changes/move-violation-detection-to-edge/design.md` — why the primary path moved, the `vehicle.edge_device_id`-based gating logic, and the exact `POST /api/violations` contract this skill implements
- `dms-spec/specs/violation-detection/spec.md` — still the accurate spec for **this component's own rule engine** (now the fallback path); the 4 rules and "growing violations" behavior described there are unchanged, just no longer the only place they run
- `specs/VIOLATION_AND_EVIDENCE_MODELS.md` — the Event/Violation/Evidence/Alarm JSON schemas. Still the data contract — don't redesign it; this change adds a new *ingestion route* into the same shapes, not a new data model.
- `specs/PHASE_2_DEVELOPMENT_PLAN.md` § "Backend Architecture (Laptop-First)" — confirms FastAPI + local storage + zero AWS dependencies, and flags SQLite as the recommended local database (still accurate; see its status banner for the superseded violation-detection-ownership part)
- `specs/STRATEGY_MASTER.md` — reference FastAPI/WebSocket code sketch for the event receiver

**Key decisions already made**: backend runs on a laptop. Database = **SQLite** (locally runnable, zero setup, file-based — matches the repo's "keep it simple, open source" preference). Evidence media = a **local folder** (not S3). Violation detection is edge-primary, backend-fallback (see above).

## Architecture this skill implements

```
Edge (dms-edge, has edge_device_id) ──HTTP──▶ Inject API ──┐
  POST /api/events (audit trail)                            │
  POST /api/evidence                                         │
  POST /api/violations (NEW — edge already decided)  ────────┤
                                                               ├──▶ SQLite DB ──▶ Fleet API ──▶ (dms-ui)
Vehicles with NO edge device ──HTTP──▶ POST /api/events ──────┤
  (fleet-simulator direct path, or any bare telemetry source) │
                                                               │
                                              Fallback: Rule Agents (violation + notification rules)
                                              — only runs when vehicle.edge_device_id is None
                                                               │
                                              Notifications (log/webhook/email simulation)
                                                               │
                                              WebSocket broadcast ──▶ (dms-ui, live updates)
```

- **Inject API — events**: `POST /api/events` receives structured JSON from the edge's Cloud Hub Agent (or a vehicle with no edge device, via a direct source). Always persisted to SQLite as the audit trail / future Phase 3 analytics input. Rule evaluation only runs if `vehicle.edge_device_id is None` (see "Fallback rule evaluation" below) — for vehicles with an edge device, the edge already decided, and re-deriving here would risk a duplicate/conflicting violation.
- **Inject API — violations (NEW)**: `POST /api/violations` receives an already-computed `Violation` (+ nested `Alarm`) from `dms-edge`'s Cloud Hub Agent — the primary path now. Validates the payload, upserts the `Violation`/`Alarm` rows (same "growing violations" semantics as the fallback engine — an update to an existing `ACTIVE` violation of the same type/vehicle, not a duplicate), and broadcasts over WebSocket exactly like the fallback path does today.
- **SFTP / evidence receiver**: receives the video/image files the edge captured as violation evidence. For the POC, a plain `POST /api/evidence` multipart upload endpoint is simpler than standing up a real SFTP server — implement true SFTP only if the user specifically asks for it (there's a stubbed `sftp_server.py` for that case using `paramiko`).
- **SQLite DB**: replaces the DynamoDB/cloud-DB icon in the diagram. Tables: `events`, `violations`, `alarms`, `vehicles`, `drivers`. Use SQLAlchemy so it's easy to swap to Postgres later if this ever needs multi-user concurrent writes.
- **Local evidence folder**: replaces the S3-bucket icon in the diagram. Store as `storage/evidence/images/{event_id}.jpg` and `storage/evidence/videos/{event_id}.mp4`; store the *path*, not the bytes, in SQLite.
- **Violation Detection Agent** (`rule_agents/violation_rules.py`, class `ViolationDetectionAgent`) — **fallback path only now**: implements the same 4 rules from `dms-spec/specs/violation-detection/spec.md` (drowsiness 3-in-2min → CRITICAL, phone usage confidence>0.85 → HIGH, distraction 2-in-1min → MEDIUM, continuous-drive >4h → LOW). `run(event) -> Violation | None`. `inject_api.py`'s `receive_event()` only calls this when the event's vehicle has no `edge_device_id` set.
- **Alarm Agent** (`rule_agents/notification_rules.py`, class `AlarmAgent`): `run(violation) -> Alarm`, turns a violation into an alarm + recommended-action text. Used by the fallback path; the `POST /api/violations` route builds its `Alarm` row directly from the edge-supplied payload instead of re-deriving it.
- **Notification Agent** (`notifications/notifier.py`, class `NotificationAgent`): `run(alarm) -> None`, dispatches it — for the POC this can just log to the `alarms` table + broadcast over WebSocket + print/log a simulated SMS/email. Used by both the fallback path and the new `/api/violations` route. Wire a real channel (Twilio, SES, Slack webhook) only if asked.
- **Fleet API + WebSocket**: what `dms-ui` talks to. REST endpoints for the dashboard's static/queryable data (vehicle list, alert history, reports) and a WebSocket stream for live alerts — mirrors the "Live — updated 4s ago" behavior in the wireframe. Unchanged by this shift: `dms-ui` reads violations/alarms the same way regardless of which path produced them.

## Future (explicitly out of scope until asked): Phase 3 data-analytics agent

Once real fleet-wide historical data exists (events + violations across many vehicles/trips), the natural next step for this component is an LLM-based analytics agent — natural-language queries over history ("which drivers had the most drowsiness violations last week"), fleet-wide pattern mining, driver-coaching recommendations, maybe a RAG layer over evidence + violation text. This is **not real-time violation detection** — that job stays on the edge. Don't scaffold this now; it's named here so the direction is documented, per the request that prompted this reframing.

## Folder structure to create

Scaffold this inside the repo root (sibling to `specs/` and `dms-edge/`), only creating what doesn't already exist:

```
dms-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, mounts routers, CORS, startup DB init
│   ├── api/
│   │   ├── __init__.py
│   │   ├── inject_api.py          # POST /api/events, /api/evidence, /api/violations (NEW) — from edge
│   │   ├── fleet_api.py           # GET endpoints for dashboard: vehicles, alerts, regions, routes, reports
│   │   └── websocket.py           # WS /ws/alerts — live push to dms-ui
│   ├── sftp/
│   │   └── sftp_server.py         # optional real SFTP receiver (paramiko) — only if asked
│   ├── rule_agents/
│   │   ├── __init__.py
│   │   ├── violation_rules.py     # ViolationDetectionAgent — fallback path only (vehicle.edge_device_id is None)
│   │   └── notification_rules.py  # AlarmAgent — violation -> alarm/advisory mapping
│   ├── notifications/
│   │   └── notifier.py            # NotificationAgent — logs + WS broadcast + simulated email/sms
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite engine + session (SQLAlchemy)
│   │   ├── models.py              # Event, Violation, Alarm, Vehicle, Driver ORM models
│   │   └── migrations/            # Alembic migrations if the schema needs to evolve
│   └── config.py                  # DB path, evidence dir, host/port, rule thresholds
├── storage/
│   ├── dms.db                     # SQLite file — gitignore this
│   └── evidence/
│       ├── videos/
│       └── images/
├── scripts/
│   └── start_backend.sh           # uvicorn app.main:app --host 0.0.0.0 --port 8000
├── tests/
├── requirements.txt
├── Dockerfile                     # optional — see "Optional: Docker" below
├── .dockerignore                  # optional
└── README.md
```

Run once when scaffolding:
```bash
mkdir -p dms-backend/app/{api,sftp,rule_agents,notifications,db/migrations}
mkdir -p dms-backend/{scripts,tests,storage/evidence/videos,storage/evidence/images}
touch dms-backend/app/__init__.py dms-backend/app/api/__init__.py dms-backend/app/db/__init__.py dms-backend/app/rule_agents/__init__.py
```

Add to (or create) the repo `.gitignore`:
```
dms-backend/storage/dms.db
dms-backend/storage/evidence/
dms-backend/.venv/
dms-backend/__pycache__/
```

## Tech stack (open source, laptop-runnable)

- Python 3.11+, FastAPI + Uvicorn — API + WebSocket server
- SQLite (via SQLAlchemy) — the "locally runnable database"; zero external services to install
- Alembic (optional) — schema migrations, only if the schema will change over time
- `python-multipart` — file uploads for evidence images/video
- `paramiko` — only if real SFTP is required; otherwise skip it
- `websockets` (bundled with FastAPI/Starlette) — live alert stream to the UI

## API surface to build

| Endpoint | Consumer | Purpose |
|---|---|---|
| `POST /api/events` | dms-edge Cloud Hub (all vehicles) | ingest an Event, store (audit trail); trigger fallback rule evaluation only if `vehicle.edge_device_id is None` |
| `POST /api/violations` **(NEW)** | dms-edge Cloud Hub (edge-equipped vehicles) | ingest an already-computed Violation + Alarm from the edge; upsert (growing-violations semantics), broadcast |
| `POST /api/evidence` | dms-edge Cloud Hub | upload evidence image/video for an event_id, save to local folder |
| `GET /api/vehicles` | dms-ui | fleet list + status (matches "Vehicles Active: 128" card) |
| `GET /api/alerts?status=active` | dms-ui | live + resolved alert list (matches "Live Alerts" sidebar list) |
| `GET /api/alerts/{id}` | dms-ui | full detail: trip, evidence, location, vehicle, in-cabin response, recommended action |
| `POST /api/alerts/{id}/acknowledge` | dms-ui | driver/dispatcher acknowledges — matches "Acknowledge" button |
| `POST /api/alerts/{id}/advisory` | dms-ui | send advisory — matches "Send advisory" button |
| `WS /ws/alerts` | dms-ui | push new/updated alerts in real time |

## When building

- **Don't re-derive violations for edge-equipped vehicles.** Gate `violation_rules.evaluate_event()` behind `vehicle.edge_device_id is None` in `inject_api.py`'s `receive_event()` — this is what prevents a duplicate/conflicting violation for the same pattern the edge already resolved.
- Keep the fallback rule engine's logic byte-for-byte consistent with what the edge ports from it (same thresholds, same `recommended_action_text` templates) — they will visibly diverge in a demo if they drift, since both can be shown side-by-side (edge-equipped vs. edge-less vehicle).
- Store raw events too (not just violations) — useful for the dashboard's evidence/trace view, for tuning thresholds live during a demo, and as the eventual input to the Phase 3 analytics agent.
- Default `config.py` to `host=0.0.0.0` so a teammate's edge device on the same network/laptop can reach it.
- If the user later asks to swap SQLite for Postgres or the local folder for S3, keep the DB access behind `db/database.py` and file access behind a small storage helper so that swap stays contained — but don't build that abstraction speculatively now.
- Name the rule/notification classes per `dms-agentic-architecture`'s `BaseAgent` shape (`ViolationDetectionAgent`, `AlarmAgent`, `NotificationAgent`, each with a `run(input) -> output`) even though they're called directly today (no message broker, no graph engine) — this is what makes the "agentic framework" claim backed by real code structure instead of just the folder names, on both the edge and the (now fallback) backend path.

## Optional: Docker

The primary/default workflow is the local venv (`python -m venv` + `pip install -r requirements.txt`
+ `uvicorn`). Docker is an **optional alternative** for when Docker Desktop is available — build it
only if the user asks to run in a Docker/container environment, not speculatively.

- `Dockerfile`: `python:3.11-slim` base, `pip install -r requirements.txt`, copy `app/` and
  `scripts/`, create the `storage/evidence/{images,videos}` dirs, `EXPOSE 8000`,
  `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
- `.dockerignore`: exclude `.venv/`, `__pycache__/`, `storage/dms.db`, `storage/evidence/`, `tests/`.
- Pairs with a root-level `docker-compose.yml` (see `dms-ui-dev` skill) that also builds `dms-ui`
  and wires them together. Mount `./storage` (or a named volume) onto `/app/storage` in
  `docker-compose.yml` so the SQLite DB and evidence files survive container restarts.
- `scripts/seed_demo.py` still works against a containerized backend — run it from the host
  (`python scripts/seed_demo.py`, since it just POSTs to `http://localhost:8000`) or via
  `docker compose exec backend python scripts/seed_demo.py`. Note `seed_demo.py`'s scripted events
  won't have an `edge_device_id` set unless updated to include one, so they'll still exercise the
  fallback rule-evaluation path — useful for testing that path stays correct.
- Don't containerize `dms-edge` here — it runs on the on-vehicle device, not the laptop backend stack.
