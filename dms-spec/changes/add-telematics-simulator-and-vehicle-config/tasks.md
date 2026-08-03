# Tasks — add-telematics-simulator-and-vehicle-config

Check items off as they land (verified working, not just written — same bar as TodoWrite). `generate_release.py` reads this file: don't mark something `[x]` until it's actually true, and don't remove/renumber items once apply has started (add new ones instead).

## 1. Telematics Simulator (dms-edge)

- [ ] 1.1 Add `TELEMATICS_SOURCE`, `TELEMATICS_SIM_INTERVAL_SECS`, `TELEMATICS_SIM_RPM_IDLE`, `TELEMATICS_SIM_RPM_CRUISE` to `dms-edge/src/config.py`
- [ ] 1.2 Create `dms-edge/agents/telematics_simulator.py` — `TelematicsSimulator` class with canned waypoint list (fallback model), sine-wave speed profile, speed-linked RPM band, `run_forever()` loop
- [ ] 1.3 Wire into `dms-edge/main.py`: start `TelematicsSimulator` thread only when `TELEMATICS_SOURCE == "simulator"`, alongside (not instead of) the existing Flask listener thread

## 1b. GPS/speed tandem (route-driven simulation)

- [ ] 1b.1 Add `RouteConfig` dataclass to `dms-edge/src/vehicle_config.py` (`from_lat`, `from_lon`, `to_lat`, `to_lon`, `avg_speed_kmh`, `duration_secs`) and `ROUTE_REQUIRED_FIELDS`; wire optional `route` field into `VehicleConfig`
- [ ] 1b.2 `VehicleConfig.from_file()`: parse the optional `"route"` JSON object into `RouteConfig`, all-or-nothing required-field validation (fail fast with a clear message if `route` is present but incomplete)
- [ ] 1b.3 Add `_haversine_distance_km()` and `_interpolate()` helpers to `telematics_simulator.py`
- [ ] 1b.4 `TelematicsSimulator`: accept optional `route: RouteConfig | None`; implement `_next_route_update()` (instantaneous speed oscillating around `avg_speed_kmh`, integrate `distance_km` from actual elapsed wall-clock time, interpolate GPS by distance fraction, clamp/stop at `to_lat`/`to_lon` once `duration_secs` elapses); keep existing canned-waypoint logic as `_next_fallback_update()`, selected when `route is None`
- [ ] 1b.5 `dms-edge/main.py`: pass `vehicle_config.route if vehicle_config else None` into `TelematicsSimulator(...)`
- [ ] 1b.6 Update `dms-edge/fleet/example-vehicle-config.json` to include a sample `route` block
- [ ] 1b.7 Manual test: run with a `route`-bearing `--vehicle-config`, confirm GPS visibly progresses from `from` to `to` over `duration_secs` and reported `speed_kmh` stays consistent with distance covered between ticks (no independent jumps)
- [ ] 1b.8 Manual test: run with a `route` present but missing one required sub-field (e.g. no `duration_secs`) — confirm `main.py` exits before video processing, naming the missing route field
- [ ] 1b.9 Manual test: run with `--vehicle-config` but no `route` block — confirm fallback canned-waypoint behavior is unchanged from before this addendum

## 2. RPM plumbing (dms-edge + dms-backend)

- [ ] 2.1 `dms-edge/agents/telematics_agent.py`: add `rpm` to `TelemetryUpdate` (+ `from_json`) and `VehicleState`; set in `TelematicsAgent.run()`
- [ ] 2.2 `dms-edge/agents/cloud_hub_agent.py`: add `"rpm": vehicle_state.rpm` to `_map_event`/`_map_violation`'s `"vehicle"` dict
- [ ] 2.3 `dms-backend/app/schemas.py`: add `rpm: float | None = None` to `VehicleIn`
- [ ] 2.4 `dms-backend/app/db/models.py`: add `rpm = Column(Float, nullable=True)` to `Event`
- [ ] 2.5 `dms-backend/app/api/inject_api.py`: pass `payload.vehicle.rpm` into `models.Event(...)` construction in `receive_event()`

## 3. Vehicle/driver config (`--vehicle-config`)

- [ ] 3.1 Create `dms-edge/src/vehicle_config.py` — `VehicleConfig` dataclass, `REQUIRED_FIELDS`, `VehicleConfig.from_file()`, `load_vehicle_config()`
- [ ] 3.2 `dms-edge/main.py`: add `--vehicle-config` argparse flag; call `load_vehicle_config(args.vehicle_config)` before opening video capture; fail fast with clear message + `sys.exit(1)` on missing required fields or unreadable/invalid JSON
- [ ] 3.3 `dms-edge/main.py`: pass `vehicle_config` into `CloudHubAgent(telematics_agent, vehicle_config)` and into `TelematicsSimulator(telematics_agent, truck_id=...)`
- [ ] 3.4 `dms-edge/agents/cloud_hub_agent.py`: accept `vehicle_config` in constructor; add vehicle-registration precedence helper; update `_map_event`/`_map_violation`'s `context` dict with `vehicle_vin`, `vehicle_fleet_id`, `driver_id`, `driver_name`, `vehicle_meta`
- [ ] 3.5 Add example JSON `dms-edge/fleet/example-vehicle-config.json` for operators to copy

## 4. Backend schema

- [ ] 4.1 `dms-backend/app/db/models.py`: add `Vehicle.vin`, `Vehicle.fleet_id`, `Vehicle.extra_metadata`; on `Driver`, **remove `driver_code` and add `driver_id` (unique, indexed, nullable) as its replacement**, plus `Driver.extra_metadata`
- [ ] 4.2 `dms-backend/app/schemas.py`: on `ContextIn`, **remove `driver_code`**, add `vehicle_vin`, `vehicle_fleet_id`, `driver_id`, `vehicle_meta`, `driver_meta`
- [ ] 4.3 `dms-backend/app/api/inject_api.py`: update `_get_or_create_vehicle()` to set `vin`/`fleet_id`/`extra_metadata` on create and refresh on update; rewrite `_get_or_create_driver()` to upsert on `ctx.driver_id` only (no `driver_code` branch), set `name`/`extra_metadata`
- [ ] 4.4 `dms-backend/app/api/fleet_api.py`: fix `serialize_alert_detail()`'s `"driver_id": driver.driver_code` → `"driver_id": driver.driver_id`
- [ ] 4.5 Grep the repo for any remaining `driver_code` references after the above edits to confirm full removal
- [ ] 4.6 Note in code comment (inject_api.py) and in DEMO_GUIDE/README: delete any existing local `dms-backend` SQLite DB before first run post-change, since `create_all` won't alter/rename existing columns

## 5. Docs / Config

- [ ] 5.1 Update `.claude/skills/dms-edge-dev/SKILL.md`'s Telematics Simulator section if actual implementation deviates from its sketch (interval, RPM bands, waypoint count)
- [ ] 5.2 Note `--vehicle-config <path.json>` usage and required-field list in `dms-edge/README.md` and/or `run_demo.sh` header comment

## 6. Verification

- [ ] 6.1 `python main.py --video videos/dataset.mp4` (no flags) — confirm changing lat/lon/speed/rpm logged every ~1.5s, no second process, unchanged behavior otherwise
- [ ] 6.2 `TELEMATICS_SOURCE=http python main.py --video ...` — confirm simulator thread does not start, manual `curl -X POST localhost:5060/telemetry` still works
- [ ] 6.3 Run with `--vehicle-config` pointing at a valid JSON file — confirm pushed `/api/events`/`/api/violations` payloads (or backend DB rows) carry `vehicle_registration`/`vin`/`fleet_id`/`driver_id`/`driver_name`, extra keys under `vehicle_meta`
- [ ] 6.4 Run with a JSON file missing `fleet_id` — confirm `main.py` exits before opening the video, naming the missing field
- [ ] 6.5 Delete/recreate local `dms-backend` SQLite DB, run `init_db()`, confirm `Vehicle`/`Driver`/`Event` tables include new columns (and no `driver_code` column) and a pushed event/violation populates them correctly end-to-end
- [ ] 6.6 `GET /api/alerts/{violation_id}` — confirm `trip_details.driver_id` in the response reflects the real `Driver.driver_id` value from the pushed `--vehicle-config`, not `None`/stale data
- [ ] 6.7 With a `route`-bearing `--vehicle-config`, sample `TelematicsAgent.get_latest_state()` (or the pushed event `context.lat/lon` + `vehicle.speed_kmh`) at several points during a run and confirm the GPS-to-elapsed-distance relationship matches the reported speed within the expected oscillation band — i.e. speed and position are never contradictory
