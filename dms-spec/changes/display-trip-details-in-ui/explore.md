# Explore — display-trip-details-in-ui

No commitment yet — this is thinking-out-loud, not a plan.

## What's the problem / idea?

The alert detail panel's "Trip Details" card in `dms-ui` renders nothing but placeholders — "Unknown driver", "Route: —", "Shift: —", "Speed at event: —", "Trip started: — (— ago)" — for every alert, even though the panel component and the backend response shape both already have named slots for these fields. The user wants a proposal that (a) traces the trip-details data flow across all four components (simulation → event detection → violation creation → backend → UI) and (b) fixes whatever is broken.

## What did you look at?

- `specs/VIOLATION_AND_EVIDENCE_MODELS.md` — the historical Event/Violation contract doc; documents `trip_id`/`elapsed_trip_seconds` as part of `Event.context`.
- `dms-spec/specs/violation-detection/spec.md`, `dms-spec/changes/move-violation-detection-to-edge/design.md` — the current edge-primary/backend-fallback architecture; `design.md` explicitly (and, it turns out, wrongly in practice) asserts "`dms-ui` needs no changes: it still reads violations/alarms from the Fleet API exactly as today, regardless of which agent produced them."
- `dms-edge/agents/telematics_simulator.py`, `telematics_agent.py` — the in-process Telematics Simulator/Agent (`TelemetryUpdate`/`VehicleState`): lat/lon/speed/heading/is_moving/rpm only, no trip/driver/route/shift fields.
- `dms-edge/src/vehicle_config.py` — `VehicleConfig` (from `--vehicle-config <path.json>`): `vehicle_registration, vin, fleet_id, driver_name, driver_id, route (GPS from/to for the speed simulation, not a display string), extra`. No `route_name` or `shift_label`.
- `dms-edge/agents/violation_detection_agent.py` `_upsert_violation` (dms-edge/agents/violation_detection_agent.py:183-230) — builds the edge's local `models.Violation`; carries `violation_id/type/rule_id/severity/status/trigger_event_ids_json/event_count/*_timestamp/time_window_seconds/severity_score/primary_evidence_event_id/recommended_action_text`. No trip/driver/route/shift/speed field at all.
- `dms-edge/agents/cloud_hub_agent.py` `_map_event`/`_map_violation`/`_identity_context` (lines 57-149) — maps edge state to the backend's JSON contract. `_identity_context()` sends `driver_id`/`driver_name`/`vin`/`fleet_id` when `--vehicle-config` is given, but `_map_violation` never sends `trip_id`/`route`/`shift_label`/`trip_started_at`/`elapsed_trip_seconds` (those `ContextIn` fields exist in the schema but nothing populates them at the source).
- `dms-backend/app/schemas.py` `ContextIn` — already declares `trip_id, route, shift_label, trip_started_at, elapsed_trip_seconds`. The contract exists; it's just unpopulated by the edge-primary path.
- `dms-backend/app/db/models.py` — `Event` has `trip_id/route/shift_label/trip_started_at/elapsed_trip_seconds/speed_kmh` columns; `Violation` has **none** of these — it's designed to look them up via `Violation.driver` and `Violation.primary_evidence_event_id → Event`, not to store them directly.
- `dms-backend/app/api/inject_api.py` `receive_event` (fallback-only path, lines 84-151) sets all the `Event` trip columns correctly from `ContextIn`. `receive_violation` (the **primary**, edge-sourced path, lines 154-216) builds/updates `Violation` (lines 172-186) but never sets `violation.driver_id` or `violation.primary_evidence_event_id` — even though `ViolationIn.context` already carries `driver_id`/`driver_name` today.
- `dms-backend/app/api/fleet_api.py` `serialize_alert_detail` (lines 85-101) — builds `trip_details` from `violation.driver` (→ `None`, since `driver_id` is never set on edge-sourced violations) and `_primary_event(violation)` (→ `None`, since `primary_evidence_event_id` is never set either). Hence every field in `trip_details` resolves to `None`/"Unknown driver" for any alert that came through the edge path — which is all of them, since edge is primary.
- `dms-ui/src/components/overview/AlertDetailPanel.jsx` (lines 39, 58-63) — reads `alert.trip_details.{driver_name,driver_id,route,shift_label,speed_at_event_kmh,trip_started_at,elapsed_trip_seconds}`. Field names match the backend's output exactly. **The UI is not the bug** — it faithfully renders an all-null object.

## Options considered

### Option A: Backend-only fix (wire up what's already flowing)
Fix `receive_violation` to set `violation.driver_id` (via `_get_or_create_driver`) and `violation.primary_evidence_event_id` (via the matching `Event` row looked up by `trigger_event_ids[-1]` or similar). This alone recovers `driver_name`/`driver_id`/`speed_at_event_kmh` (from the matched Event) for free, since `_identity_context()` already sends `driver_id`/`driver_name` and the Event row already has `speed_kmh`.
Pros: smallest change, no edge/schema changes.
Cons: `route`/`shift_label`/`trip_started_at`/`elapsed_trip_seconds` still show "—" forever, because nothing upstream of the backend generates them. Doesn't fully satisfy "display trip details."

### Option B: Full pipeline fix — generate trip/route/shift at the edge, wire the backend gap, done
Add `route_name`/`shift_label` as new optional `--vehicle-config` fields (static per demo run, same pattern as `driver_name`/`driver_id`); add a `trip_id`/`trip_started_at` generated once at edge process start (session-scoped, matches "quick and dirty" POC philosophy — no real trip lifecycle needed); thread all of it through `CloudHubAgent._identity_context`/`_map_violation`/`_map_event` → `ContextIn` (already has the fields) → fix `receive_violation`'s two missing assignments → `serialize_alert_detail` (already reads the right fields) → UI (already renders the right fields).
Pros: closes every gap identified in the trace, matches the existing `driver_name`/`driver_id` pattern exactly, no UI or schema changes needed (contract already supports this).
Cons: touches `dms-edge` (`vehicle_config.py`, `cloud_hub_agent.py`, `violation_detection_agent.py` or wherever trip_id is threaded) as well as `dms-backend`.

### Option C: Derive shift_label from wall-clock time instead of static config
Same as B but compute `shift_label` automatically (e.g. time-of-day bands) instead of reading it from `--vehicle-config`.
Pros: feels more "live"/dynamic for a demo.
Cons: adds derivation logic and a band-definition decision for a POC that doesn't need it; user's call, asked directly.

## Open questions for the user

Asked via `AskUserQuestion`: how should `route`/`shift_label` be sourced, given neither is generated anywhere today?
**Answer**: Add optional `route_name` and `shift_label` string fields to `--vehicle-config` JSON (static per demo run) — matches how `driver_name`/`driver_id` already work, no new simulation/derivation logic. (Option B, not C.)

## Direction

**Option B** — fix the full pipeline, not just the backend half. Add `route_name`/`shift_label` (optional, static) to `--vehicle-config`; generate a session-scoped `trip_id`/`trip_started_at` once at edge startup; thread both through the Cloud Hub Agent's existing `ContextIn`-shaped payload (already has every field needed — no schema change); fix `receive_violation`'s two missing assignments (`driver_id`, `primary_evidence_event_id`) so the backend can resolve driver/event lookups the same way the fallback path already does. No UI changes — `AlertDetailPanel.jsx` already reads the correct field names.
