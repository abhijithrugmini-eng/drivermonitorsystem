# Tasks — display-trip-details-in-ui

Check items off as they land (verified working, not just written — same bar as TodoWrite). `generate_release.py` reads this file: don't mark something `[x]` until it's actually true, and don't remove/renumber items once apply has started (add new ones instead).

## 1. dms-edge

- [x] 1.1 `src/vehicle_config.py`: add optional `route_name: str | None = None` and `shift_label: str | None = None` to `VehicleConfig`; parse from JSON if present (do not add to `REQUIRED_FIELDS`).
- [x] 1.2 `agents/cloud_hub_agent.py`: generate `self._trip_id` (`f"trip_{uuid4().hex[:12]}"`) and `self._trip_started_at` (`time.time()`) once in `CloudHubAgent.__init__`.
- [x] 1.3 `agents/cloud_hub_agent.py`: extend `_identity_context()` (or add a sibling `_trip_context()`) to include `route`, `shift_label` (from `self._vehicle_config`), `trip_id`, `trip_started_at`, and `elapsed_trip_seconds` (`time.time() - self._trip_started_at`, computed fresh per call); merge into both `_map_event`'s and `_map_violation`'s `context` dict.

## 2. dms-backend

- [x] 2.1 `app/api/inject_api.py` `receive_violation`: call `_get_or_create_driver(db, payload.context)` and set `violation.driver_id = driver.id if driver else None`.
- [x] 2.2 `app/api/inject_api.py` `receive_violation`: resolve `primary_evidence_event_id` by querying `models.Event` for `event_id IN payload.trigger_event_ids`, preferring one with non-null `evidence`, else most recent by `timestamp`; set `violation.primary_evidence_event_id` if found, leave unset otherwise (no error).

## 3. Verification

- [x] 3.1 Ran the live backend against a hand-crafted `POST /api/events` + `POST /api/violations` pair shaped exactly like `CloudHubAgent`'s new payload (real `route`/`shift_label`/`trip_id`/`trip_started_at`/`elapsed_trip_seconds`/`driver_id`/`driver_name`); confirmed `GET /api/alerts/{id}` returns real values for every `trip_details` field (`driver_name: "Ramesh Kulkarni"`, `route: "Mumbai-Pune Corridor"`, `shift_label: "Day Shift (06:00-14:00)"`, `speed_at_event_kmh: 71.6`, `trip_started_at`/`elapsed_trip_seconds` populated) instead of nulls/placeholders. Test rows cleaned up afterward.
- [x] 3.2 `VehicleConfig.from_file()` sanity-checked directly in a Python shell against the updated `dms-edge/fleet/example-vehicle-config.json` — `route_name`/`shift_label` parse correctly; both fields stay `None`-safe (optional, not in `REQUIRED_FIELDS`) for configs/runs that omit them.
- [x] 3.3 Triggered a violation via the fallback path (`POST /api/events` for a vehicle with no `--vehicle-config` identity, no edge device) — `violation_rules.evaluate_event` still fires and creates a violation with no errors, confirming `receive_violation`'s changes (a different code path) don't affect the fallback flow. Test rows cleaned up afterward.
