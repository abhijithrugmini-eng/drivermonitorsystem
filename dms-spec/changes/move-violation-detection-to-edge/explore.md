# Explore — move-violation-detection-to-edge

No commitment yet — this is thinking-out-loud, not a plan.

## What's the problem / idea?

Today, `dms-edge` only emits raw `DMSEvent`s; `dms-backend`'s `ViolationDetectionAgent`
(`app/rule_agents/violation_rules.py`) is the sole place violation patterns get evaluated. Abhijith
wants this reversed: violation detection SHALL run on the edge device, because "local AI analytics +
agentic framework running at the edge" is this POC's core selling point for customer demos — a cloud
dashboard that merely displays server-computed alerts is a much weaker story than a truck that
reasons about its own driver in real time, with the cloud round-trip only needed for fleet-wide
visibility. Backend-side rule evaluation becomes a Phase 3 idea instead: an LLM-based data-analytics
agent over historical events/violations, not real-time detection.

This was prompted by an updated architecture sketch (attached image, "DMS Edge Agentic System") that
already draws Violation Detection + Local Storage + Alarms inside the edge box, with an open question
sticky-noted on the diagram: *"How will Behaviour Detection Agent and Violation Detection Agent be
integrated? ... as an asynchronous daemon agent listening to behaviour detection events, how should
we interconnect? Do we need a local event bridge?"*

## What did you look at?

- `dms-spec/specs/violation-detection/spec.md` — the living spec for the *current*, backend-side
  rule engine (4 rules + "growing violations" + simulated in-cabin response). This is the exact
  behavior that needs to move, verbatim in its rule logic, to the edge.
- `dms-backend/app/rule_agents/violation_rules.py`, `notification_rules.py`, `app/db/models.py`,
  `app/schemas.py`, `app/api/inject_api.py` — the real, running implementation and its API contract.
  `inject_api.py`'s `receive_event()` already stores `vehicle.edge_device_id` from
  `payload.device.device_id` — a field that turns out to be exactly what's needed to distinguish
  "this vehicle has an edge device (skip backend rule evaluation)" from "this vehicle has no edge
  device (backend must still evaluate rules itself)" without inventing a new field.
- `.claude/skills/dms-edge-dev/SKILL.md` — today's edge agents (`TelematicsAgent`,
  `BehaviourDetectionAgent`, `CloudHubAgent`) and the existing `EventSink` multi-sink extension point
  in `main.py` (file logger + SSE sink + Cloud Hub Agent all already fan out from one `DMSEvent`).
  This existing pattern is directly relevant to the sticky note's integration question below.
- `.claude/skills/dms-agentic-architecture/SKILL.md` — the shared `BaseAgent` contract and the
  canonical agent inventory table, which currently assigns Violation Detection Agent / Alarm Agent to
  `dms-backend`.
- `CLAUDE.md` — the "Critical responsibility split" paragraph explicitly says violation detection is
  server-side only; that's the sentence this change reverses.
- The fleet-simulator design already anticipated a "no edge device" fallback path (`fleet-simulator-dev`
  skill: the simulator's `HttpPublisher` can target `dms-backend` directly "for vehicles with no edge
  device") — a useful existing concept to reuse for what backend-side rule evaluation becomes.

## Options considered

### Integration mechanism: how does the Violation Detection Agent receive events from the Behaviour Detection Agent?

**Option A: In-process `EventSink` registration (function call)**
`ViolationDetectionAgent` registers as another sink in `main.py`'s existing multi-sink fan-out,
alongside the file logger and SSE sink. Same process, synchronous call, zero new ports/servers.
- Pros: zero new infrastructure; reuses an extension point that already exists and is already proven
  (Cloud Hub Agent is wired this exact way today); lowest latency; nothing to keep running/restart
  independently.
- Cons: not independently restartable/deployable; doesn't literally look like "a daemon agent
  listening over HTTP" the way the sticky note phrased it; harder to demo as a standalone service.

**Option B: Local HTTP loopback call**
`ViolationDetectionAgent` runs as its own small local server (e.g. FastAPI on `127.0.0.1:<port>`);
`BehaviourDetectionAgent`/its `EventSink` POSTs each `DMSEvent` to it, matching the same
short-timeout, fire-and-forget style already used for the Cloud Hub Agent's push to `dms-backend`.
- Pros: matches the sticky note's "daemon agent" framing closely; genuinely decoupled process, could
  be restarted/scaled/moved independently later; consistent with how the edge already talks to the
  backend (same pattern, one more hop, nothing new to learn).
- Cons: an extra local network hop and failure mode for every single event; two processes to start
  for a demo instead of one; needs its own tiny web framework/port allocated.

**Option C: Local message queue / event bridge (e.g. a Python `asyncio.Queue`, or a lightweight
broker)**
- Pros: cleanest "pub/sub" story.
- Cons: real overkill for a single-process, single-camera POC; adds a dependency or a second process
  either way; nothing today needs the backpressure/fan-out a queue buys you. Explicitly the kind of
  thing this repo's own philosophy (`STRATEGY_MASTER.md`, `dms-agentic-architecture`) says not to add
  speculatively.

## Open questions for the user

- Confirmed via the request itself: Option A (in-process `EventSink`) as the POC default, with Option
  B documented as the upgrade path if/when Violation Detection Agent needs to run as its own
  independently-restartable process — this directly matches "remember POC" in the request and mirrors
  how `dms-agentic-architecture` already reasons about "today's hand-wired chain vs. the future
  LangGraph story" for the exact same kind of tradeoff.
- Whether `dms-backend`'s existing rule engine gets deleted or kept as a fallback for edge-less
  vehicles: kept, per the request's own framing ("could be a data analytics component... Phase 3
  later") — deleting working, spec'd code that Phase 3 will want to build on top of isn't warranted
  by this request.

## Direction

Move real-time violation detection (the exact 4 rules + growing-violations behavior currently in
`dms-backend/app/rule_agents/violation_rules.py`) into a new `ViolationDetectionAgent` +
`AlarmAgent` on `dms-edge`, backed by a new local SQLite store there for the sliding-window queries
the rules need. Wire it to `BehaviourDetectionAgent` via the existing in-process `EventSink`
extension point (Option A), with local-HTTP (Option B) documented as the explicit upgrade path.
`dms-backend`'s existing rule engine stays in place as a fallback path for vehicles with no edge
device (`vehicle.edge_device_id is None`), and its future is repurposed toward a Phase 3 LLM-based
analytics agent over historical data — not built in this change. This is a docs/skills-only change
(see `proposal.md` Non-goals); the actual code move to `dms-edge` is a follow-up change.
