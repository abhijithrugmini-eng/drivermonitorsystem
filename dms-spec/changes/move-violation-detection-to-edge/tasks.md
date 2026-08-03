# Tasks — move-violation-detection-to-edge

Check items off as they land (verified working, not just written). Section 1 was this change's
original docs/skills-only scope; Section 2 (the code move itself) has since been applied in this same
change rather than split into a separate one, since design.md already fully specified it.

## 1. Docs & skills (this change's actual scope)

- [x] 1.1 `explore.md` — integration-mechanism options, direction
- [x] 1.2 `design.md` — architecture, files touched, `POST /api/violations` contract sketch, risks
- [x] 1.3 `proposal.md` — problem/story/scope/non-goals/acceptance criteria
- [x] 1.4 `.claude/skills/dms-edge-dev/SKILL.md` updated
- [x] 1.5 `.claude/skills/dms-backend-dev/SKILL.md` updated
- [x] 1.6 `.claude/skills/dms-agentic-architecture/SKILL.md` updated
- [x] 1.7 `CLAUDE.md` updated
- [x] 1.8 Status banner added to `dms-spec/specs/violation-detection/spec.md`
- [x] 1.9 Superseding notes added to `specs/PHASE_2_DEVELOPMENT_PLAN.md` and
      `specs/🎯_COMPLETE_DESIGN_PACKAGE.md`

## 2. Follow-up implementation

- [x] 2.1 `dms-edge/storage/database.py` + `models.py` — local SQLite, `events` + `violations` tables
- [x] 2.2 `dms-edge/agents/violation_detection_agent.py` — port the 4 rules + growing-violations logic
- [x] 2.3 `dms-edge/agents/alarm_agent.py` — escalation-tier alarm + recommended-action text
- [x] 2.4 `dms-edge/main.py` — register `ViolationDetectionAgent` (+ `AlarmAgent`) in the dispatch
      fan-out
- [x] 2.5 `dms-edge/agents/cloud_hub_agent.py` — add `POST /api/violations` push
- [x] 2.6 `dms-backend/app/schemas.py` — `ViolationIn`/`AlarmIn`; `app/api/inject_api.py` — new
      `POST /api/violations` route + gate `violation_rules.evaluate_event()` behind
      `vehicle.edge_device_id is None`
- [x] 2.7 Verification: ran the real `ViolationDetectionAgent` → `AlarmAgent` → `CloudHubAgent` chain
      (3 fabricated `DROWSINESS` `DMSEvent`s, no camera/video needed) against a live local
      `dms-backend`; confirmed a CRITICAL `DROWSINESS_PATTERN` violation (event_count=3,
      `recommended_action_text` populated) landed on `GET /api/alerts`/`/api/alerts/{id}`, and that a
      fallback-path event stream (no `edge_device_id`) still produces a violation via `dms-backend`'s
      own rule engine — both paths confirmed live, side by side. 29 automated tests also added and
      passing: `dms-edge/tests/test_violation_detection_agent.py` (11), `test_alarm_agent.py` (4),
      `test_agents.py` (+2 for the violation push), and `dms-backend/tests/test_inject_api_violations.py`
      (5, via a new `tests/conftest.py` using an isolated in-memory DB + FastAPI dependency override).
- [ ] 2.8 Archive step: rewrite `dms-spec/specs/violation-detection/spec.md`'s Requirement blocks to
      describe the new edge-side behavior now that 2.1–2.7 are verified

## 3. Verification (this change's own bar)

- [x] 3.1 Every doc/skill file above was read back after writing to confirm the edit landed as
      intended (no partial/garbled sections) — verified via `Read` on each file post-write.
- [x] 3.2 Code changes in §2 are working, not just type-checked: 29 automated tests pass
      (`pytest tests/` in both `dms-edge/` and `dms-backend/`), plus a live end-to-end run against a
      real `dms-backend` server (see 2.7) exercising the actual production code paths, not mocks.
