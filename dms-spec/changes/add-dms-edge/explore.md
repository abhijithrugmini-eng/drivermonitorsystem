# Explore — add-dms-edge

No commitment yet — this is thinking-out-loud, not a plan.

## What's the problem / idea?

`dms-edge` doesn't exist on disk yet. Per `CLAUDE.md`/`dms-edge-dev` skill, it's the last major
component needed to close the loop: today only `dms-backend/scripts/seed_demo.py` exercises the
Inject API — there's no real (simulated-camera) edge device pushing events.

## What did you look at?

- `.claude/skills/dms-agentic-architecture/SKILL.md` — shared `BaseAgent` contract, canonical agent
  inventory (Telematics/Behaviour Detection/Cloud Hub agents live in `dms-edge`).
- `.claude/skills/dms-edge-dev/SKILL.md` — full folder structure, tech stack, data contract mapping;
  already very prescriptive (this is closer to "implement the skill" than "invent a design").
- `specs/DriverMonitorPOC-main/` — `main.py`, `src/config.py`, `src/events.py` (frozen reference app
  to vendor in unmodified).
- `dms-backend/app/schemas.py` — actual (nested) Inject API `EventIn` contract, more authoritative
  than `specs/VIOLATION_AND_EVIDENCE_MODELS.md`.
- `dms-backend/README.md` — API surface (`POST /api/events`, `POST /api/evidence`), run commands.
- `.claude/skills/fleet-simulator-dev/SKILL.md` — GPS update JSON schema the Telematics Agent's
  `POST /telemetry` endpoint must accept (`truckId`/`latitude`/`longitude`/`speed`/`heading`/`status`).
  `fleet-simulator` itself doesn't exist yet either — the Telematics Agent is built against the
  documented schema, verified with a manual `curl`, not against a live simulator.

## Options considered

Not really forking options — the `dms-edge-dev` skill is prescriptive enough (folder layout, agent
responsibilities, data mapping table) that this is mostly transcription + filling in the detail it
leaves open (exact `TelematicsUpdate`/`VehicleState` shapes, error handling specifics, whether to
build Docker now).

One real fork: **Docker now or later.** Skill says Docker is optional/build-only-if-asked. Decision:
skip it for this change — scaffold the venv path only, matching "primary/default workflow" guidance;
add Docker in a follow-up if requested.

## Open questions for the user

None blocking. One gap worth flagging: no demo video ships with `specs/DriverMonitorPOC-main`, so
`--video` needs a user-supplied file to run end-to-end on camera frames; this doesn't block
scaffolding or the manual `curl`-based Telematics/Cloud Hub agent verification against a running
`dms-backend`.

## Direction

Follow the `dms-edge-dev` skill's plan directly: vendor `specs/DriverMonitorPOC-main` into
`dms-edge/src` unmodified, add `dms-edge/agents/{base,telematics_agent,behaviour_detection_agent,
cloud_hub_agent}.py`, extend `src/config.py`, adapt `main.py` minimally to wire the new sinks/agents,
ship venv-only (no Docker) for this change.
