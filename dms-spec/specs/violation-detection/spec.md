# Capability: Violation Detection

> **Status note (see `dms-spec/changes/move-violation-detection-to-edge/`):** as of that change's
> proposal, this capability's primary home is moving to `dms-edge` — a ported copy of the exact rule
> logic below, running locally against a new edge-side SQLite store — because local, on-vehicle
> violation detection is this POC's core selling point (see `CLAUDE.md` § "This POC's selling
> point" and `.claude/skills/dms-agentic-architecture/SKILL.md`). **The Requirement blocks below are
> intentionally left unchanged**: they still accurately describe the currently-running code, which
> at time of writing is `dms-backend`'s rule engine and is the only implementation in production.
> Once the edge-side port lands and is verified (see that change's `tasks.md` § 2), this file gets
> rewritten at that change's **Archive** step to describe the new primary/fallback split, per this
> repo's own rule that living specs reflect what shipped, not what was proposed. Until then, treat
> everything below as accurate for `dms-backend` specifically, which will keep this exact behavior as
> its fallback path for vehicles with no edge device even after the move.

Server-side rule evaluation that turns a stream of driver-behaviour `Event`s into `Violation`s and `Alarm`s. Owned by `dms-backend` (`app/rule_agents/violation_rules.py`, `notification_rules.py`, `app/notifications/notifier.py`) — see `.claude/skills/dms-agentic-architecture/SKILL.md` for the Violation Detection Agent / Alarm Agent / Notification Agent framing. This is a real example of the `dms-spec/specs/<capability>/spec.md` format — written from the already-implemented rule engine, not a template placeholder.

## Requirements

### Requirement: Server-side-only violation detection
Violation detection SHALL happen only in `dms-backend`. Edge devices SHALL emit raw `Event`s and MAY fire an immediate local in-cabin alarm, but SHALL NOT independently decide violations.

#### Scenario: Edge emits a raw event
- **WHEN** an edge device (or `dms-backend/scripts/seed_demo.py` standing in for one) POSTs an `Event` to `POST /api/events`
- **THEN** the event is persisted and evaluated against the rules below; the edge device performs no rule evaluation of its own

### Requirement: Drowsiness pattern rule
The system SHALL raise a `DROWSINESS_PATTERN` violation, severity `CRITICAL`, when 3 or more `DROWSINESS` events occur for the same vehicle within a rolling 120-second window.

#### Scenario: Three drowsiness events within the window
- **WHEN** a vehicle has 3 `DROWSINESS` events whose timestamps span ≤ 120 seconds
- **THEN** a `DROWSINESS_PATTERN` violation is created (or updated, see "Growing violations" below) with severity `CRITICAL`

#### Scenario: Drowsiness events spread too far apart
- **WHEN** a vehicle has drowsiness events but the oldest-to-newest span within the current window is such that fewer than 3 remain after pruning entries older than 120 seconds from the latest event
- **THEN** no violation is created

### Requirement: Phone usage rule
The system SHALL raise a `PHONE_USAGE` violation, severity `HIGH`, on a single `PHONE_USAGE` event with `detection.confidence > 0.85`.

#### Scenario: High-confidence phone detection
- **WHEN** a `PHONE_USAGE` event arrives with confidence `0.92`
- **THEN** a `PHONE_USAGE` violation is created immediately (no windowing/count needed)

#### Scenario: Low-confidence phone detection
- **WHEN** a `PHONE_USAGE` event arrives with confidence `0.80` (≤ 0.85)
- **THEN** no violation is created

### Requirement: Distraction pattern rule
The system SHALL raise a `DISTRACTION_PATTERN` violation, severity `MEDIUM`, when 2 or more `DISTRACTION` events occur for the same vehicle within a rolling 60-second window.

#### Scenario: Two distraction events within the window
- **WHEN** a vehicle has 2 `DISTRACTION` events within 60 seconds of each other
- **THEN** a `DISTRACTION_PATTERN` violation is created

### Requirement: Continuous drive rule
The system SHALL raise a `CONTINUOUS_DRIVE` violation, severity `LOW`, when a single event's `metrics.drive_duration_hours` exceeds 4.

#### Scenario: Drive duration exceeds threshold
- **WHEN** a `CONTINUOUS_DRIVE` event arrives with `metrics.drive_duration_hours = 4.3`
- **THEN** a `CONTINUOUS_DRIVE` violation is created (no windowing — single-event check)

### Requirement: Growing violations, not duplicates
Each vehicle SHALL have at most one `ACTIVE` violation per violation type at a time. New matching events SHALL update that violation in place (incrementing `event_count`, extending `trigger_event_ids`, refreshing `recommended_action_text`) rather than creating a duplicate row. A new violation of the same type SHALL only be created once the previous one has left `ACTIVE` status (acknowledged or resolved).

#### Scenario: A 4th drowsiness event arrives while the violation is still active
- **WHEN** a vehicle already has an `ACTIVE` `DROWSINESS_PATTERN` violation with `event_count = 3`, and a 4th matching `DROWSINESS` event arrives
- **THEN** the existing violation's `event_count` becomes 4 and its `recommended_action_text` is regenerated to reference the 4th micro-sleep; no second violation is created

#### Scenario: A new violation opens after acknowledgement
- **WHEN** a vehicle's `DROWSINESS_PATTERN` violation has been acknowledged (status no longer `ACTIVE`), and a fresh 3-event drowsiness pattern occurs later
- **THEN** a new `DROWSINESS_PATTERN` violation is created

### Requirement: Alarm and recommended-action generation
On every violation create/update, the system SHALL create or update an `Alarm` with a severity-appropriate message, and SHALL generate `recommended_action_text` via a rule-based template (not an LLM) keyed on violation type, event count, and window.

#### Scenario: Recommended action for a growing drowsiness violation
- **WHEN** a `DROWSINESS_PATTERN` violation reaches `event_count = 3` with a waypoint and distance available on the triggering event
- **THEN** `recommended_action_text` reads like "3rd micro-sleep in 2.0 min. Advise rest stop at {waypoint}, {distance} km ahead."

### Requirement: Simulated in-cabin response
Because no real edge device reports buzzer/acknowledgement telemetry in this POC, the system SHALL simulate plausible `driver_ack_latency_seconds`, `speed_before_kmh`, and `speed_after_kmh` values on first alarm creation for a violation, and SHALL NOT resimulate them on subsequent updates to the same violation.

#### Scenario: First alarm for a new violation
- **WHEN** a violation is created for the first time
- **THEN** the alarm gets freshly simulated ack-latency and speed-before/after values

#### Scenario: Violation grows, alarm already exists
- **WHEN** an existing violation's event_count increments (see "Growing violations")
- **THEN** the existing alarm's simulated ack-latency/speed fields are left unchanged
