# Explore — add-telematics-simulator-and-vehicle-config

No commitment yet — this is thinking-out-loud, not a plan.

## What's the problem / idea?

`dms-edge`'s Telematics Agent is receive-only — nothing generates GPS/speed/RPM telemetry, so running `main.py --video ...` on its own (no `fleet-simulator`, which doesn't exist on disk yet) produces events with empty `context.lat/lon` and `vehicle.speed_kmh`, and RPM doesn't exist anywhere in the codebase. Separately, vehicle/driver identity is a single hardcoded env var (`EDGE_VEHICLE_REGISTRATION`) — there's no way to attach a VIN, fleet ID, or driver identity to a demo run, so violation data pushed to `dms-backend` carries no real truck/driver details.

## What did you look at?

- `dms-edge/main.py` — CLI arg parsing (`--video`, `--camera`, `--save`, `--no-ui`, `--no-display`, `--no-cloud`), agent wiring, per-frame dispatch loop.
- `dms-edge/agents/telematics_agent.py` — confirmed it's a Flask listener on port 5060 (`POST /telemetry`), purely receive-only; `TelemetryUpdate`/`VehicleState` dataclasses have no `rpm` field.
- `dms-edge/agents/cloud_hub_agent.py` — `_map_event()`/`_map_violation()` map `DMSEvent`/`Violation` + `VehicleState` into `dms-backend`'s nested JSON. `EDGE_VEHICLE_REGISTRATION` is a static config constant; `driver_code`/`driver_name` are never populated even though the backend schema already accepts them.
- `dms-edge/src/config.py` — existing "Agentic layer" config section, plain `os.environ.get(...)` constants pattern.
- `dms-backend/app/db/models.py`, `app/schemas.py`, `app/api/inject_api.py` — `Vehicle` (registration/vehicle_type/region, no vin/fleet_id), `Driver` (`driver_code`/name only — no distinct fleet-system `driver_id`), `ContextIn`/`VehicleIn` schemas, `_get_or_create_vehicle`/`_get_or_create_driver` upsert logic (upserts on `vehicle_registration`/`driver_code`). Confirmed `driver_code` has exactly one write site (`_get_or_create_driver`) and one read site (`fleet_api.py`'s `serialize_alert_detail`) — safe to remove outright rather than keep alongside a new field.
- `.claude/skills/dms-edge-dev/SKILL.md` — **already specifies** an in-process "Telematics Simulator" (`agents/telematics_simulator.py`) toggled by a `TELEMATICS_SOURCE` config value (`"simulator"` default vs `"http"`), explicitly scoped to avoid building the full `fleet-simulator` early. This change implements that existing design, not a new one.
- `specs/FLEET_SIMULATOR_SPEC.md` — the GPS update JSON schema (`truckId`, `latitude`, `longitude`, `speed`, `heading`, `status`) that `TelemetryUpdate.from_json()` already matches; no RPM concept there either — confirmed RPM is net-new to every spec/schema in the repo.
- `dms-backend/app/api/fleet_api.py:95` — found `"driver_id": driver.driver_code if driver else None` in the dashboard-facing serializer. This is a pre-existing naming collision: the UI already labels `driver_code` as `"driver_id"`. Rather than leave two different concepts both called "driver_id" at different layers, this change **removes `driver_code` outright** and replaces it with the real fleet-system `driver_id` everywhere (model, schema, upsert key, serializer) — see "Driver identity: replace, not add" below.
- Confirmed no Alembic in this repo — `dms-backend/app/db/database.py::init_db()` just calls `Base.metadata.create_all(bind=engine)`, no `alembic/` directory exists.

## Options considered

### Telematics source
**Option A (chosen): in-process Telematics Simulator**, a daemon thread calling `TelematicsAgent.run()` directly on a timer — per the `dms-edge-dev` skill's existing design. No new process, starts automatically with `main.py`.
**Option B: standalone fleet-simulator process** POSTing to the existing `/telemetry` HTTP endpoint. Bigger scope — `fleet-simulator` doesn't exist on disk — and the skill explicitly says not to reach for this until a demo needs multiple trucks/real routing.

### RPM scope
**Option A: edge-only** — simulated and available locally, not pushed to backend. Smaller, avoids a schema change for a field nothing consumes yet.
**Option B (chosen): full stack** — edge dataclasses, backend schema, DB column, Cloud Hub Agent mapping, persisted like `speed_kmh` is today.

### Vehicle/driver config shape
**Option A (chosen): flexible JSON via `--vehicle-config <path>`** — a few required fields (`vehicle_registration`, `vin`, `fleet_id`, `driver_name`, `driver_id`) plus arbitrary additional fields passed through as an opaque metadata blob.
**Option B: environment variables only** — extend the existing `os.environ.get(...)` pattern. Simpler, but clunkier for a multi-field profile and not demo-friendly (can't hand someone a JSON file per truck).

### Extra/unknown JSON fields
**Option A (chosen): pass through as opaque metadata blob** (`context.vehicle_meta` → `Vehicle.extra_metadata`/`Driver.extra_metadata` JSON columns) — no schema change needed per new field.
**Option B: log and drop** — simpler, but the "flexible schema" goal only helps local config readability, not backend visibility.

### Backend field scope
**Option A: edge-only for this change**, backend fields deferred.
**Option B (chosen): extend backend now** — add `vin`/`fleet_id` to `Vehicle`, `driver_id` to `Driver`, so pushed violation data actually persists and is queryable end-to-end, matching the user's stated goal.

### Driver identity: `driver_code` + new `driver_id` vs. replace `driver_code` with `driver_id`
**Option A: keep `driver_code` (upsert key) and add `driver_id` (fleet-system ID) as a second, separate column.** Non-breaking, but leaves two overlapping driver-identifier fields — `driver_code` was never actually populated by `dms-edge` (only `dms-backend`'s own fallback path ever had a `driver_code` concept in mind, and nothing in the codebase reads/writes it besides the one upsert site), and the UI already mislabels it as `"driver_id"` (`fleet_api.py:95`), so keeping both invites exactly the confusion already observed.
**Option B (chosen): remove `driver_code` entirely, replace with a single `driver_id` field** (model column, schema field, upsert key) end-to-end. Verified via `Grep` that `driver_code` has exactly one write site (`inject_api.py::_get_or_create_driver`) and one read site (`fleet_api.py::serialize_alert_detail`) — safe to remove outright with no other callers to reconcile. `fleet_api.py`'s `"driver_id": driver.driver_code` line is fixed to `"driver_id": driver.driver_id` in the same change, resolving the existing mislabeling instead of just flagging it.

## Open questions for the user

All resolved via `AskUserQuestion` during planning:
1. Simulator location → in-process Telematics Simulator.
2. RPM scope → full stack (edge + backend).
3. Vehicle/driver config transport → `--vehicle-config` JSON file.
4. Extra field handling → opaque metadata passthrough, not dropped.
5. Backend schema timing → extend now, same change.
6. Driver identity field → replace `driver_code` with `driver_id` outright (user follow-up instruction), not keep both.

## Direction

Build the in-process Telematics Simulator exactly as `dms-edge-dev` already anticipates; add `rpm` end-to-end; add a `--vehicle-config <path.json>` flag with 5 required fields + opaque `extra` passthrough; extend `dms-backend`'s `Vehicle` model with `vin`/`fleet_id`, and replace `Driver.driver_code` with `Driver.driver_id` as the sole driver-identity column/upsert key, fixing `fleet_api.py`'s existing mislabeled serializer field in the same pass. See `design.md` for the concrete technical approach.

## Addendum: GPS/speed tandem (route-driven simulation)

### What's the problem / idea?

The originally-designed Telematics Simulator (canned waypoint loop + independent sine-wave speed) produces GPS and speed that aren't physically related — position doesn't actually advance at the rate the reported speed implies. The user wants a **tandem**: GPS position and speed derived from the same underlying motion, driven by an operator-supplied route (`from` lat/lon → `to` lat/lon), an average speed (km/h), and the video's duration (seconds) — so a 3-minute demo video plausibly covers the distance a truck would cover at the given average speed in that time, with position advancing consistently with reported speed at every tick.

### What did you look at?

- Confirmed `dms-edge/main.py` opens the video via `cv2.VideoCapture(args.video)` — frame count / FPS are available *after* `cap.isOpened()`, i.e. after the simulator would already need to start (both the Flask listener thread and, per this addendum, the simulator thread are started before the `cv2.VideoCapture` call in the current design). Auto-deriving duration from the video file would require restructuring startup order; the user instead wants duration supplied explicitly, which sidesteps this entirely and keeps the simulator decoupled from `cv2`.
- Haversine-based great-circle interpolation is the standard, dependency-free way to compute a point a given fraction along a straight path between two lat/lon pairs — no new library needed (pure math, consistent with this repo's "quick and dirty" bar).
- Re-examined the already-designed `TelematicsSimulator` internals (canned waypoints, independent sine-wave speed/RPM) — this addendum replaces that motion model, not the class/thread/config-toggle structure around it (`TELEMATICS_SOURCE`, daemon thread, direct `TelematicsAgent.run()` calls are unchanged).

### Options considered

**Where do from/to/avg-speed/duration get supplied?**
- Option A: new CLI flags on `main.py` (`--route-from`, `--route-to`, `--avg-speed-kmh`, `--sim-duration-secs`).
- Option B (chosen): a `route` section inside the same `--vehicle-config` JSON file, since it's already the mechanism for "supply configuration for this demo run" and keeps `main.py`'s CLI surface from growing by 4+ more flags. Route data lives alongside vehicle/driver identity in one file per demo run, which matches how an operator would think about "this run represents this truck, this driver, this route."

**How is speed derived once from/to/avg-speed/duration are known?**
- Option A: constant speed = avg_speed_kmh for the whole run (simplest, exactly matches "avg speed" as a literal constant).
- Option B (chosen): oscillate around avg_speed_kmh (still keeping total-distance-over-duration consistent with the average) so the demo still shows *some* speed variation (matches the original design's demo-realism goal) — the tandem constraint is enforced by having GPS position track the actual instantaneous speed at each tick (numerically integrated), not by re-deriving speed from position.

### Direction

Extend `VehicleConfig`/the `--vehicle-config` JSON with an optional `route` object (`from_lat`/`from_lon`/`to_lat`/`to_lon`/`avg_speed_kmh`/`duration_secs`). When present, `TelematicsSimulator` switches from the canned-waypoint model to a route-interpolation model: at each tick it computes instantaneous speed (oscillating around `avg_speed_kmh`), integrates distance traveled since start, and places GPS position that fraction of the way along the great-circle path from `from` to `to` (clamped at the endpoint once `duration_secs` elapses) — so speed and position are always in tandem, never independently faked. When `route` is absent (or no `--vehicle-config` given at all), the simulator falls back to today's canned-waypoint behavior unchanged. See `design.md` for the exact interpolation math and config shape.
