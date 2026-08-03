# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Before starting any non-trivial feature/story work, read `.claude/skills/dms-spec-workflow/SKILL.md`.** It's the parent process skill (explore → design → propose → apply → review → release → archive, modeled on OpenSpec) that every other skill's work happens inside of — proposals live in `dms-spec/changes/`, living specs in `dms-spec/specs/`.

## This POC's selling point

**Local AI analytics and an agentic framework running on the vehicle — not a camera that streams raw events for a smarter cloud to grade.** That one sentence is the differentiator every architecture decision in this repo should be checked against. Concretely, it's why violation detection (not just behaviour detection) runs on `dms-edge`: the edge device detects behaviour, decides violations, and fires an in-cabin alarm locally, with no cloud round-trip required to know something is wrong. `dms-backend` still exists and still matters (fleet-wide dashboard, persistence, a fallback path for vehicles with no edge device, and eventually fleet-wide analytics) — it's just not where the "smart" part of the demo lives. See `.claude/skills/dms-agentic-architecture/SKILL.md` for the full doctrine this follows, and `dms-spec/changes/move-violation-detection-to-edge/` for the change that moved detection here from the backend.

## Project state

`dms-backend` (FastAPI), `dms-ui` (React/Vite), and `dms-edge` (camera-based detection, vendoring
`specs/DriverMonitorPOC-main`) are all implemented and runnable — see the root `README.md` for how to
run them (local venv/`npm run dev`, or the optional Docker path via the root `docker-compose.yml`).
`fleet-simulator` does **not** exist on disk yet — `dms-edge`'s in-process Telematics Simulator
(see `dms-agentic-architecture`/`dms-edge-dev`) and `dms-backend/scripts/seed_demo.py` currently
stand in for it. `dms-edge` currently only emits raw
events and fires an immediate local alarm (`speak()` stub); the actual **violation-detection logic
still lives in `dms-backend`** as of this writing — moving it onto `dms-edge` (per "This POC's
selling point" above) is proposed and designed in `dms-spec/changes/move-violation-detection-to-edge/`
but not yet implemented (see that change's `tasks.md` § 2 for the remaining code work). Until that
lands, treat `dms-backend`'s rule engine as the active, only path — but build any new edge work with
the target architecture in `.claude/skills/dms-edge-dev/SKILL.md` in mind, not the pre-change one.
`specs/` holds the original architecture/planning docs, wireframes, and the `DriverMonitorPOC-main`
reference app; `.claude/skills/` holds the Claude Code skills that scaffold/extend each subsystem —
read the relevant skill before making non-trivial changes to a component, since it documents the
folder structure, tech stack, and API surface actually in use (which in places supersedes the
older/rougher sprint docs in `specs/` — see each skill's notes).

## What this POC is

Real-time driver-monitoring dashboard: an edge device runs computer-vision behaviour detection (drowsiness, phone usage, distraction), evaluates violation rules against its own local history, fires an in-cabin alarm, and syncs the finished result to a backend that serves a live fleet dashboard. Explicit team philosophy (from `specs/STRATEGY_MASTER.md`, `specs/QUICK_REFERENCE.md`): **"quick and dirty"** — favor pre-trained open-source models and the simplest thing that demonstrably works over production hardening. This is a capability showcase for a customer demo, not a production system — and per "This POC's selling point" above, the specific capability being showcased is *local* AI + agentic decision-making, not a cloud dashboard.

**Key architectural decision**: the entire stack (edge + backend + UI) runs locally on a laptop/board for the POC — no AWS, no managed cloud database, no S3, no API Gateway/Lambda. SQLite replaces the cloud DB on both `dms-backend` and (once the move above lands) `dms-edge`; a local folder replaces the S3 evidence bucket.

## Four-component, agent-based architecture

**Read `.claude/skills/dms-agentic-architecture/SKILL.md` before touching any of this.** It's the parent design doctrine: every functional unit below (Telematics Agent, Behaviour Detection Agent, Violation Detection Agent, Alarm Agent, Cloud Hub Agent, Notification Agent) is built as a named `BaseAgent` — one responsibility, typed input/output, matching a box in `specs/POC_ARCHITECTURE_WORKBENCH.drawio`/`specs/POC_ARCHITECTURE.drawio`/`specs/Updated_POC_ARCHITECTURE.png` — deliberately so the project can be shown as built on an agentic framework, and so today's hand-wired call chain has a concrete migration path to a real orchestrator (e.g. LangGraph) later without a rewrite.

Target architecture (per `dms-spec/changes/move-violation-detection-to-edge/` — see "Project state" above for what's actually implemented today):

```
fleet-simulator (standalone)          dms-edge (device)                                         dms-backend (laptop, FastAPI)         dms-ui (React)
─────────────────────────             ─────────────────                                         ──────────────────────────────        ───────────────
simulated truck GPS/telematics  ──▶   Telematics Agent (latest vehicle state)
(HttpPublisher, per truck)            Behaviour Detection Agent (wraps
                                       DriverMonitorPOC-main's dms.py,
                                       unmodified) ─DMSEvent──▶ Violation Detection Agent (PRIMARY — local SQLite
                                                                 sliding window) ─Violation──▶ Alarm Agent (in-cabin,
                                                                 escalation tier)
                                       Cloud Hub Agent (maps DMSEvent/Violation +          Inject API (/api/events audit trail,
                                       vehicle state → backend JSON) ──HTTP──▶             /api/evidence, /api/violations)
                                                                                             → Violation Detection Agent (FALLBACK —
                                                                                               edge-less vehicles only)
                                                                                             → Alarm Agent → Notification Agent
                                                                                             → Fleet API + WebSocket ─────────────▶ Fleet Command
                                                                                                                                      dashboard (live)
```

- **`dms-edge`** (implemented; violation detection move in progress): vendors `specs/DriverMonitorPOC-main/` in unmodified (MediaPipe Face Mesh for drowsiness/yawn/EAR/MAR, YOLOv8 for phone detection, time-based windows, local in-cabin alarm via a `speak()` stub) and adds an agentic layer: Telematics Agent (receives GPS/telemetry from `fleet-simulator`), Behaviour Detection Agent (thin wrapper around the vendored `DriverMonitoringSystem`), Violation Detection Agent (local rule evaluation against a local SQLite sliding window — the selling-point capability, see above), Alarm Agent (escalation-tier in-cabin alert), Cloud Hub Agent (maps events/violations + latest vehicle state → `dms-backend`'s JSON contracts and pushes them). Built via the `dms-edge-dev` skill.
- **`dms-backend`** (implemented): FastAPI service that ingests edge events (audit trail) and edge-computed violations (`POST /api/violations`, the primary path once the move above lands), runs its own Violation Detection Agent → Alarm Agent → Notification Agent only as a **fallback** for vehicles with no edge device, persists to SQLite, stores evidence media in a local folder, and serves the dashboard via a REST Fleet API + WebSocket. Its long-term direction is a Phase 3 LLM-based fleet-analytics agent over historical data — not real-time detection. Extend via the `dms-backend-dev` skill.
- **`dms-ui`** (implemented): React (Vite) "Fleet Command" dashboard — master-detail layout matching `specs/ui-wireframe.png`: sidebar nav, summary cards, live alerts list, and an alert detail panel (trip/evidence/location/vehicle/in-cabin-response/recommended-action). A REST/WebSocket **consumer**, not itself agentic — doesn't care whether an alert came from the edge-primary or backend-fallback path. Extend via the `dms-ui-dev` skill.
- **`fleet-simulator`** (planned, not built): standalone tool that simulates one or more trucks moving along GPS routes and publishes location + telematics events (engine started/stopped, geofence, fuel low, idle, route completed). Not itself an agent in the `dms-agentic-architecture` sense — it's the decoupled data source that feeds `dms-edge`'s Telematics Agent (primary path, per truck, correlated by a shared `vehicle_registration`/truck-ID) or `dms-backend` directly (secondary path, for vehicles with no edge device — exactly the fallback path above). Built via the `fleet-simulator-dev` skill; spec in `specs/FLEET_SIMULATOR_SPEC.md`.

**Critical responsibility split**: violation detection is **edge-primary, backend-fallback** — the reverse of this POC's earlier design. `dms-edge`'s Violation Detection Agent is the default, demoed path (local SQLite sliding window, no cloud round-trip needed); `dms-backend`'s copy of the same rule logic only runs for vehicles with no edge device (`vehicle.edge_device_id is None`). The edge still also fires an immediate, per-event local alarm (`speak()` stub) independent of both — that part hasn't changed. Keep the edge and backend rule logic in sync (same thresholds, same `recommended_action_text` templates) since they're both real, live code paths now, not a primary-plus-unused-stub pair. Don't move rule logic back to server-only without explicit instruction — the edge-side story is this POC's core sales pitch.

When starting work on any one of these components, read `.claude/skills/dms-agentic-architecture/SKILL.md` plus the corresponding component skill (`.claude/skills/{dms-edge,dms-backend,dms-ui,fleet-simulator}-dev/SKILL.md`) first — the parent skill defines the shared agent contract, the component skill documents the exact folder structure, tech stack, and API surface for that piece.

## Data contract

The `Event` → `Violation` → `Evidence` → `Alarm` JSON schemas in `specs/VIOLATION_AND_EVIDENCE_MODELS.md` are the fixed contract between edge, backend, and UI — **do not redesign them**, reuse the exact shapes/dataclasses documented there. `dms-spec/changes/move-violation-detection-to-edge/design.md` adds a new *ingestion route* (`POST /api/violations`) into these same shapes; it does not change the shapes themselves. Summary:

| Model | Flows | Purpose |
|---|---|---|
| `Event` | edge → backend | raw detection: type, confidence, metrics (EAR/MAR/etc.) — always sent, now primarily an audit trail once the edge is the primary detector |
| `Violation` | edge → backend (primary) or computed backend-side (fallback) → dashboard | pattern of events aggregated into a graded alert |
| `Evidence` | edge → backend → dashboard | JPG/clip of the violation moment |
| `Alarm` | edge (primary) or backend (fallback) → dashboard | driver-facing alert message |

Violation types and thresholds (also drive the UI's severity color-coding — CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue) — same rules regardless of which path (edge or fallback) evaluates them, per `dms-spec/specs/violation-detection/spec.md`:
- Drowsiness: 3 events in 2 min → CRITICAL
- Phone usage: confidence > 0.85 → HIGH
- Distraction: 2 events in 1 min → MEDIUM
- Continuous drive: > 4 hours → LOW

## Key docs (read before major changes)

- `dms-spec/changes/move-violation-detection-to-edge/` — the architecture decision behind the current edge-primary/backend-fallback split: `explore.md` (integration-mechanism options), `design.md` (Mermaid flow + API contract), `proposal.md` (why/scope)
- `dms-spec/specs/violation-detection/spec.md` — the precise rule requirements (drowsiness/phone/distraction/continuous-drive, "growing violations", simulated in-cabin response) — accurate for whichever path is running them
- `specs/VIOLATION_AND_EVIDENCE_MODELS.md` — the Event/Violation/Evidence/Alarm schemas and violation rules (the data contract)
- `specs/STRATEGY_MASTER.md` — overall POC scope, timeline, reference code sketches (FastAPI/WebSocket server, `Dashboard.jsx`)
- `specs/PHASE_2_DEVELOPMENT_PLAN.md` — the laptop-first, zero-cloud backend architecture decision and agent breakdown (see its status note on violation-detection ownership)
- `specs/ui-wireframe.png` / `specs/POC_ARCHITECTURE_WORKBENCH.drawio` / `specs/POC_ARCHITECTURE.drawio` / `specs/Updated_POC_ARCHITECTURE.png` — the exact dashboard layout and the authoritative agent/box diagrams (`dms-agentic-architecture` skill's source of truth for agent names/boundaries)
- `specs/QUICK_REFERENCE.md` — local dev/demo run commands once components exist (server on :8000, dashboard on :3000, `--video`-driven demo flow) and a debugging checklist for the event pipeline
- `specs/TASK_BOARD.md`, `specs/POC_SPRINT_2WEEKS.md` — task breakdown and 2-week timeline context
- `specs/DriverMonitorPOC-main/` — the reference camera-based detection app `dms-edge` vendors in (see `dms-edge-dev` skill); its own `DEMO.md`/`DEPLOY.md` document how it runs and deploys today
- `specs/FLEET_SIMULATOR_SPEC.md` — functional/non-functional spec for the standalone truck GPS/telematics simulator (see `fleet-simulator-dev` skill)

## Conventions to preserve when scaffolding

- Python 3.11+ for edge/backend, SQLAlchemy over SQLite (not raw `sqlite3`), FastAPI + Uvicorn for the backend — `dms-edge`'s new local storage follows the same SQLAlchemy/SQLite pattern as `dms-backend`, not a different one
- React 18 + Vite for the UI, plain CSS/flexbox — don't add Tailwind, Redux, or React Query speculatively
- Config values (detection thresholds, backend URLs, DB/evidence paths) belong in each component's `config.py` / config module, not hardcoded — they get tuned live for demos
- Any new local DB files or evidence/media directories must be added to `.gitignore` (per-component patterns are listed in each skill's SKILL.md)
- Docker is an **optional** run path, not the default — `dms-backend/Dockerfile`, `dms-ui/Dockerfile`, and the root `docker-compose.yml` exist for when Docker Desktop is available (see each skill's "Optional: Docker" section). The primary/default workflow for local dev remains the venv + `npm run dev` instructions in the root `README.md`.
