# Add dms-edge (edge/device component)

**Change:** `add-dms-edge` · **Status:** proposed · **Owner:** Abhijith VR

## Problem / Why

`dms-backend` and `dms-ui` are implemented and can run end-to-end today, but only against
`dms-backend/scripts/seed_demo.py`'s scripted event sequence — there's no real (simulated-camera)
edge device in the loop. `dms-edge` is the last of the four architecture-diagram components missing
from the repo, and a complete, working CV detection app already exists at
`specs/DriverMonitorPOC-main/` to vendor in rather than rebuild.

## Story

As a developer demoing the DriverMonitorPOC, I want a `dms-edge` component that runs the existing
camera-based detection app, receives simulated vehicle telemetry, and pushes real detection events
(with vehicle context) into the running `dms-backend`, so that the full edge → backend → dashboard
pipeline can be demonstrated on real video input instead of only the scripted seed data.

## Scope

- Vendor `specs/DriverMonitorPOC-main` into `dms-edge/src/` unmodified.
- Add three agents per `dms-agentic-architecture`/`dms-edge-dev`: `TelematicsAgent`,
  `BehaviourDetectionAgent`, `CloudHubAgent`.
- Telematics Agent exposes `POST /telemetry` (port 5060) matching the fleet-simulator GPS schema;
  verified via manual `curl` (no live `fleet-simulator` to integrate against yet).
- Cloud Hub Agent pushes to `dms-backend`'s real `POST /api/events` and `POST /api/evidence`,
  verified against a locally running `dms-backend`.
- `dms-edge/README.md` with run instructions; `.gitignore` entries for edge-generated artifacts.
- Basic unit tests for the agents (event mapping, vehicle-state store), independent of camera/YOLO.

## Non-goals

- No `fleet-simulator` build (separate component/skill, not started).
- No Docker packaging for `dms-edge` in this change (skill marks it optional/on-request).
- No live camera (`--camera`) support — Phase 2, explicitly deferred by the vendored app itself.
- No modification to `dms-backend` or `dms-ui`.
- No changes to the frozen CV logic (`src/dms.py`, `src/events.py`, `src/alert_templates.py`).
- No retry/durability queue for failed backend pushes (log-and-drop, per skill).

## Acceptance criteria

- [ ] `dms-edge/` exists with the folder structure from `dms-edge-dev` SKILL.md.
- [ ] `python main.py --video <file> --no-display` runs the vendored detection pipeline unchanged.
- [ ] `curl -X POST localhost:5060/telemetry` with a sample GPS payload updates `TelematicsAgent`'s
      stored `VehicleState` (verified via a debug read, e.g. a log line or tiny `GET /telemetry`).
- [ ] A synthetic `DMSEvent` run through `CloudHubAgent` against a live local `dms-backend` produces
      a `201`/success from `POST /api/events`, and evidence upload succeeds for a `PHONE_USAGE`
      event.
- [ ] `dms-edge/README.md` lets a stranger run the component from scratch.
- [ ] Root `.gitignore` updated; no generated artifacts (venv, logs, output videos) staged.

## Affected capabilities

New: `dms-spec/specs/dms-edge/spec.md` (doesn't exist yet — created at Archive time to document the
three agents' behavior). No existing `dms-spec/specs/*` capability changes (violation-detection spec
is backend-only and unaffected).
