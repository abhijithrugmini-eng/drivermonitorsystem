# Display real trip details in the alert detail panel

**Change:** `display-trip-details-in-ui` · **Status:** proposed · **Owner:** unassigned

## Problem / Why

The alert detail panel's "Trip Details" card (`dms-ui`'s `AlertDetailPanel.jsx`) always shows placeholders — "Unknown driver", "Route: —", "Shift: —", "Speed at event: —", "Trip started: — (— ago)" — for every single alert, regardless of severity or violation type. This isn't a UI rendering bug: the UI reads the exact right field names from the exact right API response shape. The data is simply never generated or never threaded through upstream — a full trace (see `explore.md`) found two independent gaps: (1) `dms-edge` never generates `route`/`shift_label`/`trip_id`/`trip_started_at` in the first place (only vehicle/driver identity is configured today), and (2) even the fields that *are* available today (`driver_id`, `driver_name`) get silently dropped by `dms-backend`'s `receive_violation` handler — the primary, edge-sourced ingestion path — because it never links the incoming violation to a `Driver` row or an `Event` row the way the (now-fallback-only) `receive_event` path already does.

For a customer-facing demo, an alert detail panel that always says "Unknown driver" undercuts the pitch — it looks unfinished regardless of how good the underlying violation detection is.

## Story

As a fleet operator viewing a drowsiness/distraction/phone-usage alert on the Fleet Command dashboard, I want to see which driver, route, shift, and speed were involved (and when the trip started), so that I can make an informed decision about the alert without having to separately look up which driver was assigned to that vehicle.

## Scope

- `dms-edge`: add optional `route_name`/`shift_label` fields to `--vehicle-config` JSON; generate a session-scoped `trip_id`/`trip_started_at` once per edge process run; thread all of it (plus the existing `driver_id`/`driver_name`) through the Cloud Hub Agent's `POST /api/violations` payload (it's already sent on `POST /api/events`, minus trip fields — see `explore.md`).
- `dms-backend`: fix `receive_violation` (`POST /api/violations` handler) to resolve/set `violation.driver_id` and `violation.primary_evidence_event_id`, matching what the fallback rule engine already does for locally-evaluated violations.
- No `dms-ui` changes — `AlertDetailPanel.jsx` already reads the correct field names and will render real values once the backend returns them.
- No API/schema contract changes — `ContextIn`/`ViolationIn` already declare every field needed.

## Non-goals

- Real ignition-cycle/trip-boundary detection (multiple trips per edge-process run, trip end/resume). One demo run = one trip, matching this POC's "quick and dirty" philosophy.
- Deriving `shift_label` dynamically from wall-clock time (considered in `explore.md`, user chose static `--vehicle-config` fields instead).
- Storing `speed_kmh`/`elapsed_trip_seconds` directly on the `Violation` row instead of resolving them via the linked `Event` — kept consistent with the existing fallback-path design (see `design.md` Risks).
- Backfilling trip details for already-stored violations/events from before this change ships (existing demo data keeps showing "—" until new alerts come in).

## Acceptance criteria

- [ ] A `--vehicle-config` JSON with `route_name` and `shift_label` set produces an alert whose detail panel shows the real driver name, route, and shift (not placeholders).
- [ ] `trip_started_at` and the derived "ago" display are non-placeholder and increase correctly across multiple violations from the same edge run.
- [ ] `speed_at_event_kmh` shows a real value (not "—") for a violation whose `trigger_event_ids` match a previously-pushed `Event`.
- [ ] A `--vehicle-config` *without* `route_name`/`shift_label` (or no `--vehicle-config` at all) still runs without errors and shows "—" for just those fields — no regression for demos that don't set them.
- [ ] The backend-fallback path (vehicle with no edge device, `POST /api/events` → local rule engine) is unaffected — it already worked and must keep working identically.
- [ ] Existing tests (if any) for `inject_api.py` and the edge Cloud Hub Agent still pass.

## Affected capabilities

None of `dms-spec/specs/`'s existing capabilities cover trip-detail display specifically (`violation-detection/spec.md` is scoped to rule evaluation, not UI/API presentation). At Archive time, evaluate whether a small `### Requirement:` addition to a fleet-api- or alert-presentation-facing spec is warranted, or whether this is minor enough to leave undocumented at the spec level (POC-scale judgment call).
