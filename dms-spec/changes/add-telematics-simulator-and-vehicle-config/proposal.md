# Telematics Simulator, RPM plumbing, and vehicle/driver config file

**Change:** `add-telematics-simulator-and-vehicle-config` · **Status:** proposed · **Owner:** unassigned

## Problem / Why

`dms-edge`'s Telematics Agent is receive-only — nothing today generates GPS/speed/RPM telemetry, so a laptop/office demo with no `fleet-simulator` running (it doesn't exist on disk yet) shows no speed, no GPS, no RPM, and `CloudHubAgent` pushes events with empty `context.lat/lon` and `vehicle.speed_kmh`. Separately, vehicle/driver identity is hardcoded to a single env var (`EDGE_VEHICLE_REGISTRATION`) with no way to attach a VIN, fleet ID, or driver name/ID without editing `src/config.py`, and the backend's `Vehicle`/`Driver` tables have no columns for any of this. As a result, violation data pushed to `dms-backend` today carries no real, identifiable vehicle or driver details.

The backend's existing `Driver.driver_code` field compounds this: it's a placeholder that was never actually populated by `dms-edge`, and the dashboard-facing serializer already mislabels it as `"driver_id"` (`dms-backend/app/api/fleet_api.py:95`). Introducing a second, genuinely distinct `driver_id` (the fleet-system ID) alongside the unused `driver_code` would leave two overlapping fields and worsen the existing mislabeling rather than resolve it.

## Story

As a demo operator running `python main.py --video videos/dataset.mp4`, I want the system to synthesize plausible-looking GPS/speed/RPM automatically (no second process to start) and to load a JSON file describing which truck and driver this run represents, so that the dashboard shows a moving, identifiable vehicle with a named driver instead of a static, anonymous stub.

As that same operator, I want to optionally supply a route (from/to GPS coordinates), an average speed, and the video's duration, so that the simulated GPS position and reported speed move **in tandem** — the truck visibly progresses from the start coordinate toward the end coordinate at a pace consistent with the speed being reported — instead of GPS and speed being independently randomized and physically inconsistent with each other.

## Scope

- In-process Telematics Simulator (`dms-edge/agents/telematics_simulator.py`) driving `TelematicsAgent.run()` on a timer, toggled via `TELEMATICS_SOURCE` config.
- `rpm` added end-to-end: `TelemetryUpdate`, `VehicleState`, simulator output, backend `VehicleIn` schema, `Event` DB column, `CloudHubAgent` mapping.
- `--vehicle-config <path.json>` CLI flag on `dms-edge/main.py`, a `VehicleConfig` dataclass/loader, required-field validation (fail-fast), opaque passthrough for extra fields.
- **GPS/speed tandem via an optional `route` section in `--vehicle-config`**: `from_lat`/`from_lon`, `to_lat`/`to_lon`, `avg_speed_kmh`, `duration_secs`. When supplied, `TelematicsSimulator` interpolates GPS position along the great-circle path from the start to end coordinate, paced so cumulative distance-over-time matches the supplied average speed and duration — speed and position are derived from the same underlying motion model, never independently faked. When omitted, the simulator falls back to the original canned-waypoint behavior.
- Backend schema/model extensions: `Vehicle.vin`, `Vehicle.fleet_id`, `extra_metadata` JSON columns on both `Vehicle` and `Driver`, `ContextIn`/`VehicleIn` field additions, `_get_or_create_vehicle`/`_get_or_create_driver` upsert logic updates.
- **Remove `Driver.driver_code` outright and replace it with `Driver.driver_id`** (the fleet-system ID) as the single driver-identity column and upsert key — not an additive second field. Fix `fleet_api.py`'s `serialize_alert_detail()` to read the real `driver.driver_id` instead of the current `driver.driver_code` mislabeled as `"driver_id"`.

## Non-goals

- No other `dms-ui`/`fleet_api.py` changes beyond the `driver_id` field-name fix above — RPM, VIN, fleet_id, and metadata blobs are not surfaced on the dashboard (data lands in the DB, inert until a follow-up UI change reads it).
- No multi-truck simulation, real route/geofence logic, or a simulator config file — explicitly reserved for `fleet-simulator-dev` per the `dms-edge-dev` skill. The route interpolation added here is a single straight-line (great-circle) from/to path, not real road routing/geofencing.
- No auto-detection of video duration from the video file — `duration_secs` is an explicit, operator-supplied input (see design.md's Approach for why: the simulator starts before `cv2.VideoCapture` opens the file).
- No Alembic/migration tooling — this repo has none today; additive/renamed nullable columns + "delete your local dms.db" is the accepted POC-scale approach.
- No change to the existing `TELEMATICS_SOURCE="http"` / Fleet Simulator ingestion path — it must keep working unmodified.
- No backward-compatible alias/shim for `driver_code` — it is being removed, not deprecated, since it was never populated by any real code path (see Problem/Why).

## Acceptance criteria

- [ ] `python main.py --video videos/dataset.mp4` (no extra flags) starts a background thread that updates `TelematicsAgent`'s state every ~1-2s with oscillating speed/GPS/RPM, with no second process.
- [ ] `TelematicsAgent.get_latest_state().rpm` is populated and flows into every `CloudHubAgent`-pushed event/violation's `vehicle.rpm` field, and lands in the backend's `Event.rpm` column.
- [ ] `python main.py --video ... --vehicle-config fleet/truck-42.json` with a valid JSON file overrides `EDGE_VEHICLE_REGISTRATION`-sourced identity for the whole run; a JSON file missing a required field causes `main.py` to exit(1) with a clear message before any video/frame processing starts.
- [ ] Extra keys in the JSON file (beyond the 5 required fields) show up in the backend as `Vehicle.extra_metadata`/`Driver.extra_metadata` JSON, not dropped and not individually validated.
- [ ] With a `route` section supplied in `--vehicle-config` (from/to lat-lon, avg speed km/h, duration secs), GPS position reported by the simulator visibly progresses from the `from` coordinate toward the `to` coordinate over the run, reaching (or nearly reaching) the `to` coordinate by `duration_secs`, and at every tick the reported `speed_kmh` is consistent with the distance covered since the previous tick (no independent/contradictory speed and position).
- [ ] Without a `route` section (or without `--vehicle-config` at all), the simulator falls back to the original canned-waypoint + independent-speed behavior unchanged.
- [ ] `dms-backend`'s `Vehicle` table gains `vin`, `fleet_id`, `extra_metadata`; `Driver` table has `driver_code` removed and replaced by `driver_id` (+ `extra_metadata`) — no trace of `driver_code` remains in models/schemas/upsert logic/serializers. All created correctly via `Base.metadata.create_all` on a fresh `dms.db`.
- [ ] `GET /api/alerts/{violation_id}` returns `trip_details.driver_id` sourced from the real `Driver.driver_id` column, not a `driver_code` value under that name.
- [ ] Existing behavior with no `--vehicle-config` flag and `TELEMATICS_SOURCE` unset is unchanged (defaults preserve current demo behavior); `TELEMATICS_SOURCE=http` still accepts manual/Fleet-Simulator POSTs to `/telemetry` unmodified.

## Affected capabilities

- `dms-edge`: Telematics Agent, new Telematics Simulator, Cloud Hub Agent, `main.py`, `src/config.py`.
- `dms-backend`: `Vehicle`/`Driver`/`Event` models, `ContextIn`/`VehicleIn` schemas, `inject_api.py` upsert logic, `fleet_api.py`'s `serialize_alert_detail()` (one-field fix: `driver_code` → `driver_id`).
- No `dms-spec/specs/` capability exists yet for telematics/vehicle-identity — this change will add a new `dms-spec/specs/telematics-simulation/spec.md` at Archive time (see design.md).
