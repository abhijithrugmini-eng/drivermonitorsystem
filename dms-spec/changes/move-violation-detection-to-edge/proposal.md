# Move violation detection to the edge

**Change:** `move-violation-detection-to-edge` · **Status:** applied (code) · **Owner:** Abhijith VR

> **Status update:** the Non-goals section below originally scoped this change to docs/skills only,
> with the code move planned as a separate follow-up change. In practice the follow-up was applied
> directly in this same change folder (`tasks.md` § 2) instead of being split out, since `design.md`
> already fully specified it — see `tasks.md` for what was actually built and verified. Review/
> Release/Archive are still open (see `tasks.md` § 2.8).

## Problem / Why

Real-time violation detection currently runs only in `dms-backend`, server-side. For a capability
showcase whose selling point is *local AI analytics and an agentic framework running on the vehicle*,
a cloud-only detection story undersells the product: it looks like a dashboard that reacts to
whatever the edge chooses to report, not a truck that reasons about its own driver in real time. This
change moves the actual rule-evaluation intelligence onto `dms-edge`, where it becomes the headline
demo capability, and repositions `dms-backend`'s current rule engine as (a) a fallback path for fleet
vehicles with no edge device installed, and (b) the seed for a future Phase 3 LLM-based fleet
analytics agent — not real-time detection.

## Story

As a solution architect demoing this POC to a customer, I want the truck's own edge device to detect
and grade driver-safety violations locally — with the cloud only receiving the finished result — so
that the demo credibly shows "local AI + agentic framework" as the product's core differentiator,
not just a device that streams raw events to a smarter cloud.

## Scope

- Document the architecture decision and rationale (this proposal + `design.md`).
- Update `.claude/skills/dms-edge-dev/SKILL.md`: add `ViolationDetectionAgent` + `AlarmAgent` as core
  edge agents, local SQLite storage for the sliding-window rule state, the `EventSink`-based
  integration mechanism (with local-HTTP documented as the upgrade path), and the new
  `POST /api/violations` push from `CloudHubAgent`.
- Update `.claude/skills/dms-backend-dev/SKILL.md`: reframe its rule engine as the edge-less fallback
  path, add the `POST /api/violations` ingestion endpoint to its API surface, add a Phase 3 (future,
  out of scope) LLM analytics agent note.
- Update `.claude/skills/dms-agentic-architecture/SKILL.md`: add the POC USP statement, move the
  Violation Detection Agent / Alarm Agent rows in the agent inventory table to `dms-edge`, update the
  hand-wired call-chain diagram.
- Update `CLAUDE.md`: USP statement, four-component diagram, "Critical responsibility split"
  paragraph (reversed), and the stale "Project state" paragraph (`dms-edge` is implemented today, not
  "planned").
- Add a status banner (not a rewrite) to `dms-spec/specs/violation-detection/spec.md` pointing at this
  change, since the living spec still accurately documents the *currently running* code.
- Add brief superseding notes to the two older `specs/*.md` docs that state "server detects
  violations" as a settled decision (`PHASE_2_DEVELOPMENT_PLAN.md`,
  `🎯_COMPLETE_DESIGN_PACKAGE.md`).

## Non-goals

- **No code changes in this change.** `dms-edge/agents/violation_detection_agent.py`,
  `alarm_agent.py`, the local SQLite store, `dms-backend`'s `POST /api/violations` route, and the
  `vehicle.edge_device_id` gating logic are all designed in `design.md` but implemented in a
  follow-up change (`design.md` → Apply is out of scope here; this change stops at Propose/docs).
- No deletion of `dms-backend`'s existing rule engine — it becomes the fallback path, not dead code.
- No Phase 3 LLM analytics agent build — explicitly future work, only named here as the direction.
- No rewrite of the `dms-spec/specs/violation-detection/spec.md` Requirement blocks — they still
  describe real, running behavior; only a status banner is added.
- No change to the `Event`/`Violation`/`Alarm` storage schema — new ingestion route, same data model.
- No message broker / local event queue / `langgraph` dependency — the in-process `EventSink` stays
  the POC's integration mechanism (see `explore.md`).

## Acceptance criteria

- [x] `explore.md` documents the integration-mechanism options and the chosen direction.
- [x] `design.md` has a Mermaid architecture diagram, files-touched list, and the new
      `POST /api/violations` contract sketch.
- [x] `dms-edge-dev` SKILL.md reflects Violation Detection Agent + Alarm Agent + local storage as core
      (not optional), with the event-trigger mechanism explained.
- [x] `dms-backend-dev` SKILL.md reflects the fallback-path reframing and the new endpoint.
- [x] `dms-agentic-architecture` SKILL.md's agent inventory table and USP section are updated.
- [x] `CLAUDE.md`'s architecture diagram, responsibility-split paragraph, and project-state paragraph
      are updated and internally consistent with the skills above.
- [x] `dms-spec/specs/violation-detection/spec.md` and the two older `specs/*.md` docs carry
      status/superseding notes without having their historical content rewritten.

## Affected capabilities

`dms-spec/specs/violation-detection/spec.md` — status banner added in this change; the actual
Requirement blocks get rewritten to reflect edge-side detection at the **Archive** step of the
follow-up implementation change, once the code described in `design.md` actually ships (per this
repo's own rule: living specs reflect what shipped, not what was proposed).
