---
name: dms-agentic-architecture
description: >-
  The cross-cutting design doctrine for the DriverMonitorPOC's Agentic AI
  framework — read this BEFORE dms-edge-dev, dms-backend-dev, dms-ui-dev, or
  fleet-simulator-dev whenever the work touches an "agent" (Telematics
  Agent, Behaviour Detection Agent, Violation Detection Agent, Alarm Agent,
  Cloud Hub Agent, Notification Agent). Defines the shared BaseAgent
  contract, this POC's core selling point (local AI analytics + agentic
  framework running on the vehicle, not a cloud-only detector), how agents
  pass typed messages instead of sharing state, today's hand-wired pipeline
  vs. the future LangGraph-style graph-orchestration story, and the
  canonical agent inventory mapped to
  specs/POC_ARCHITECTURE_WORKBENCH.drawio / specs/POC_ARCHITECTURE.drawio /
  specs/Updated_POC_ARCHITECTURE.png. Triggers on requests like "agent
  framework", "agentic architecture", "how do agents talk to each other",
  "add a new agent", "wire this into LangGraph", "agent contract", "why is
  violation detection on the edge", or any cross-component architecture
  question for this project.
---

# DMS Agentic Architecture — Design Doctrine

This is the parent design skill for the whole DriverMonitorPOC stack. Every component skill (`dms-edge-dev`, `dms-backend-dev`, `fleet-simulator-dev`, and — as a consumer, not a producer — `dms-ui-dev`) should be read *together with* this one whenever the work involves adding, renaming, or wiring an agent. This doc doesn't replace those skills' component-specific detail (folder structure, tech stack, exact API contracts) — it defines the shape every agent across all of them must share.

## Why this exists

This project is a deliberate **capability showcase**: alongside "does the driver-monitoring demo work," a stated goal is to demonstrate that we build with an **agentic AI framework**, not a pile of scripts calling each other. Concretely, that means every meaningful unit of behaviour in the stack — ingesting telemetry, detecting driver behaviour, evaluating violation rules, raising alarms, notifying, syncing to the cloud, simulating a fleet — is implemented as a discrete, named **Agent** with an explicit input contract and output contract. That buys three things:

1. A real story for demos/RFPs ("built on an agent-based architecture"), backed by actual code structure, not just a diagram.
2. A concrete seam to later drop in a real orchestrator (LangGraph, or similar) without rewriting business logic — because every agent already looks like a graph node.
3. Independently testable, independently reasoned-about units, which is also just good design at this POC's complexity.

### The POC's actual selling point: local AI analytics, not a cloud-only detector

**This is the principle every other decision in this doc — and in `dms-edge-dev`/`dms-backend-dev` — now flows from.** The differentiator this POC exists to demonstrate is that the *intelligence* runs on the vehicle: the edge device detects behaviour AND decides violations AND fires an escalation-tier in-cabin alarm, all locally, with no cloud round-trip required to know something is wrong. A truck that reasons about its own driver in real time and only phones home with the finished result is a fundamentally stronger demo than a camera that streams raw events for a smarter server to grade — the latter looks like the cloud vendor did the hard part, which is the opposite of the story this POC needs to tell.

Concretely, this is why **Violation Detection Agent and Alarm Agent now live on `dms-edge`** (moved there via `dms-spec/changes/move-violation-detection-to-edge/` — see that change's `design.md` for the full rationale and the alternatives considered for how they wire to the Behaviour Detection Agent), with `dms-backend`'s copy of the same logic demoted to a fallback for fleet vehicles that have no edge device, and eventually repurposed toward a Phase 3 LLM-based fleet-analytics agent (historical pattern mining, natural-language queries, coaching insights) — explicitly **not** real-time detection. When in doubt about where a new piece of intelligence should live, default to the edge; only put it in `dms-backend` if it's genuinely fleet-wide (spans multiple vehicles/trips) or genuinely can't run within an edge device's resource budget.

## The canonical architecture: the drawio diagrams are the source of truth

`specs/POC_ARCHITECTURE_WORKBENCH.drawio` (page 2), `specs/POC_ARCHITECTURE.drawio`, and `specs/Updated_POC_ARCHITECTURE.png` (the newer sketch that first drew Violation Detection + Local Storage + Alarms inside the edge box) are the authoritative box diagrams for this system. **Agent names and boundaries in code must match the boxes in these diagrams** — don't invent a different decomposition per skill, and don't quietly drop a box (an earlier draft of `dms-edge-dev` dropped "Telematics Agent" entirely; that was wrong and has been corrected — see the agent inventory below).

### Telematics data: three tiers, don't conflate them

The "Telematics Unit" box in the drawio is deliberately generic — three different things can sit behind it in this POC, and conflating them leads to wrong assumptions about what's built vs. planned:

1. **A real telematics unit** — out of scope entirely; no hardware in this POC.
2. **The Fleet Simulator** (`fleet-simulator-dev`, standalone, not yet built) — the real long-term answer: simulates a fleet of trucks on GPS routes and pushes updates to each truck's `dms-edge` Telematics Agent over HTTP, one truck ↔ one edge deployment.
3. **The Telematics Simulator** (new, minimal, lives *inside* `dms-edge`) — a lightweight synthetic vehicle-state generator, directly in-process with the Telematics Agent, for the case the workbench sticky note calls out explicitly: the edge board itself is stationary during demos (a laptop, not a moving truck), and still needs GPS/speed to feed the Alarm Agent's `recommended_action_text` and the Cloud Hub Agent's location fields. No HTTP hop, no separate process, no routes/geofences/config file — one canned loop, toggled on when nothing else is publishing telemetry. See `dms-edge-dev`'s "Telematics Simulator" section.

Keep 2 and 3 distinct: the Fleet Simulator is a standalone tool with its own skill that simulates *many* trucks for the fleet-wide dashboard story; the Telematics Simulator is a `dms-edge`-local convenience with no dashboard/fleet ambitions, meant only to unblock a single-vehicle edge demo before (or without) the Fleet Simulator existing. Don't grow the Telematics Simulator toward the Fleet Simulator's feature set — if a demo needs multiple trucks or real route logic, that's a signal to build `fleet-simulator-dev`, not to expand the stub.

## The `BaseAgent` contract

Minimal, dependency-free, and **duplicated per component** (see "Why not a shared library" below):

```python
from typing import Protocol, TypeVar

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")

class BaseAgent(Protocol[TIn, TOut]):
    name: str  # stable id — used in logs, and becomes the node name if this is ever
               # wrapped as a LangGraph node

    def run(self, input_: TIn) -> TOut:
        """Given a typed input, produce a typed output. Avoid hidden global state —
        anything the agent needs across calls should be an explicit attribute on
        the agent instance (e.g. `self._latest_state`), not a module-level global."""
```

Rules every agent follows, regardless of which component it lives in:

- **One agent = one responsibility = one box in the drawio.** If you find yourself building something that does two of the diagram's boxes at once, split it.
- **Inputs/outputs are the project's existing typed models** — `DMSEvent` (from `https://github.com/raviR-lab/DriverMonitorPOC/tree/main/src/events.py`), the Event/Violation/Alarm JSON shapes (`dms-backend/app/schemas.py`, `dms-backend/app/db/models.py`, and the new local-storage models in `dms-edge/storage/models.py`), GPS/telemetry updates (`specs/FLEET_SIMULATOR_SPEC.md`). Never invent a second ad hoc shape for a concept that already has one.
- **Agents communicate by passing these typed messages forward** — a sink/callback (`EventSink.emit`, matching what `https://github.com/raviR-lab/DriverMonitorPOC/tree/main` already does and what `dms-edge`'s Violation Detection Agent now also hooks into), an HTTP call, or a plain function return — never through shared mutable globals or reaching into another agent's internals.
- **Give every agent a stable, drawio-matching `name`** (`"telematics_agent"`, `"behaviour_detection_agent"`, `"violation_detection_agent"`, `"alarm_agent"`, …) and log it plus a short input/output summary on each `run()` — cheap now, and exactly what you'd want visible if this were ever traced through a real orchestrator later.

## Why not a shared installable library

`dms-edge`, `dms-backend`, and `fleet-simulator` are three separately deployed Python processes/venvs (soon possibly separate containers/boards) with no monorepo packaging tooling set up. Duplicating the ~10-line `BaseAgent` shape in each is the right call at this scale — standing up a shared installable package (versioning, publishing, cross-repo dependency management) is premature infrastructure for a POC. Consistency comes from every component following *this document*, not from a shared `import`. Revisit this only if/when the project moves past POC scale.

## Today's orchestration vs. the LangGraph story

**Today**: agents are wired together with plain sequential Python calls and the existing sink/callback pattern (`EventSink.emit()`, one agent's output passed directly into the next agent's `.run()`) — no message broker, no graph engine, no `langgraph` dependency. This matches the repo's "quick and dirty" POC philosophy and is enough at this scale; don't build a task queue or an actual graph runtime unless explicitly asked. This same reasoning is why `dms-edge`'s Violation Detection Agent hooks into the existing `EventSink` fan-out in-process rather than getting its own HTTP server — see `dms-spec/changes/move-violation-detection-to-edge/explore.md` for the options that were weighed.

**Why this is still a real LangGraph on-ramp, not just an aspiration**: because every agent already has a typed `run(input) -> output` method and a stable name, the migration path is concrete: each `Agent.run()` becomes a LangGraph node function, the typed input/output becomes (a slice of) the graph's shared `State`, and today's hand-wired call chain —

```
Telematics Agent ─┐
                    ├─▶ Behaviour Detection Agent ─┬─▶ Violation Detection Agent ─▶ Alarm Agent ─┐
                    │                              │                                              │
                    │                              └─▶ Cloud Hub Agent ◀────────────────────────┘
                    │                                       │ (all in dms-edge, in-process)
                    │                                       ▼
                    │                          dms-backend Inject API
                    │                                       │
                    │                          (fallback, edge-less vehicles only)
                    │                                       ▼
                    └─────────────────────────▶ dms-backend Violation Detection Agent ─▶ Alarm Agent ─▶ Notification Agent
```

— becomes the graph's edges, unchanged in substance. This is what lets a demo credibly say "this can plug into LangGraph" rather than merely asserting it.

## Agent inventory (canonical — update this table, not a per-skill copy, if an agent is added/renamed)

| Agent | Drawio box | Lives in | Input | Output | Skill |
|---|---|---|---|---|---|
| **Telematics Agent** | "Telematics Agent" (fed by "Telematics Unit") | `dms-edge/agents/telematics_agent.py` | GPS/telemetry update — from the **Fleet Simulator** (`fleet-simulator-dev`, standalone) over HTTP, or the in-process **Telematics Simulator** (`dms-edge/agents/telematics_simulator.py`, new — see "Telematics data" above) when nothing external is publishing | latest normalized vehicle state (speed, lat/lon, heading), held for other edge agents to read | `dms-edge-dev` |
| **Behaviour Detection Agent** | "Behaviour Detection Agent" (fed by camera) | `dms-edge/agents/behaviour_detection_agent.py` — a thin wrapper around the vendored, frozen `https://github.com/raviR-lab/DriverMonitorPOC/tree/main/src/dms.py` | video frame | `DMSEvent` | `dms-edge-dev` |
| **Violation Detection Agent** (primary) | "Violation Detection" | `dms-edge/agents/violation_detection_agent.py` — reads/writes `dms-edge/storage/` (local SQLite) for the sliding-window rule state | `DMSEvent` (via in-process `EventSink` fan-out from Behaviour Detection Agent) | `Violation \| None` | `dms-edge-dev` |
| **Alarm Agent** (primary) | "Alarms" | `dms-edge/agents/alarm_agent.py` — the escalation tier; the frozen `speak()` stub in `src/alert_templates.py` is the separate immediate tier | `Violation` | `Alarm` + recommended-action text; fires the in-cabin alert | `dms-edge-dev` |
| **Cloud Hub Agent** | "Cloud Hub" | `dms-edge/agents/cloud_hub_agent.py` | `DMSEvent` / `Violation` + Telematics Agent's latest vehicle state | HTTP push to `dms-backend` (`POST /api/events` audit trail, `POST /api/evidence`, `POST /api/violations`) | `dms-edge-dev` |
| **Violation Detection Agent** (fallback) | "Voilation Detection" / "Rule Agents" [sic — typo is in the source diagram] | `dms-backend/app/rule_agents/violation_rules.py` — only runs for vehicles with no edge device (`vehicle.edge_device_id is None`) | `Event` | `Violation` | `dms-backend-dev` |
| **Alarm Agent** (fallback) | "Alarms" / "Rule Agents" | `dms-backend/app/rule_agents/notification_rules.py` | `Violation` | `Alarm` + recommended-action text | `dms-backend-dev` |
| **Notification Agent** | "Notifications" | `dms-backend/app/notifications/notifier.py` | `Alarm` (from either the fallback path or the new `POST /api/violations` route) | WS broadcast to `dms-ui`, simulated SMS/email log line | `dms-backend-dev` |
| **Fleet Simulation Agent(s)** | not in the drawio — new, standalone, decoupled | `fleet-simulator/simulator/engine.py` + `publishers/` | route/config | GPS/telemetry updates | `fleet-simulator-dev` |
| *(future, Phase 3, not built)* **Data Analytics Agent** | not in the drawio yet | would live in `dms-backend`, LLM-based | historical `Event`/`Violation` rows across the fleet | natural-language answers, coaching/pattern insights | none yet — don't scaffold until asked |

`dms-ui` is deliberately **not** in this table — it's a rendering client that consumes what the backend agents produce (REST + WebSocket), not itself agentic. Don't force-fit a `BaseAgent` onto UI components.

Note the two `Violation Detection Agent` / `Alarm Agent` rows: **the edge copy is the primary, demoed path; the backend copy is the fallback for edge-less vehicles.** Keep both — don't delete the backend rule engine, and don't let the two drift apart (same thresholds, same `recommended_action_text` templates); see `dms-backend-dev`'s "When building" notes.

## What this means for each component skill

- **`dms-edge-dev`**: build `agents/telematics_agent.py`, `agents/behaviour_detection_agent.py`, `agents/violation_detection_agent.py`, `agents/alarm_agent.py`, `agents/cloud_hub_agent.py`, each implementing the `BaseAgent` shape above, plus `storage/` (local SQLite) for the Violation Detection Agent's sliding-window state. The Telematics Agent receives data pushed by the Fleet Simulator (not a fabricated/hardcoded feed) — see that skill for the exact ingestion mechanism. The Violation Detection Agent receives events via the existing in-process `EventSink` fan-out, not a new HTTP hop — see that skill's "How Behaviour Detection Agent and Violation Detection Agent talk to each other."
- **`dms-backend-dev`**: `rule_agents`/`notifications` already match this shape conceptually — name the classes `ViolationDetectionAgent`, `AlarmAgent`, `NotificationAgent` so the code matches the drawio + this doc, not just the folder names. This path is now the **fallback** (gated on `vehicle.edge_device_id is None`) plus the ingestion point for edge-computed violations (`POST /api/violations`) — not the primary detector.
- **`fleet-simulator-dev`**: its `HttpPublisher` should be able to target a `dms-edge` Telematics Agent's ingestion endpoint (per simulated truck), not only push into `dms-backend` directly — see that skill for the URL convention and how it correlates a simulated truck to a real edge deployment.
- **`dms-ui-dev`**: no changes needed — it stays a REST/WebSocket consumer, and doesn't care whether a given alert came from the edge-primary path or the backend-fallback path.

## When building any agent (any component)

- Name it after its drawio box (`ViolationDetectionAgent`, not `RuleEngine`; `TelematicsAgent`, not `GPSReader`).
- If an agent is "mostly existing logic plus a new interface" (e.g. wrapping `https://github.com/raviR-lab/DriverMonitorPOC/tree/main`'s `dms.py`, or porting `dms-backend`'s rule engine onto the edge), wrap/port it faithfully — don't modify the frozen reference code, and don't redesign rule thresholds while porting them.
- Keep the `run()` method's input/output typed and boring; resist adding orchestration smarts (retries-with-backoff, circuit breakers, queues) beyond what the POC actually needs — that's Phase 2 scope, same as the rest of this repo's philosophy.
- Don't add a message broker, task queue, or an actual `langgraph`/`crewai`/etc. dependency unless a user explicitly asks to wire one in — the contract is what matters for the showcase story right now, not the orchestration engine. This applies as much to Behaviour Detection ↔ Violation Detection Agent wiring as it does to anything else — default to a direct/in-process call, document the HTTP or queue alternative, don't build it speculatively.
