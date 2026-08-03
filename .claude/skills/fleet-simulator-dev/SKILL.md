---
name: fleet-simulator-dev
description: >-
  Use when scaffolding, building, or extending the Fleet Simulator for the
  DriverMonitorPOC/fleet-management demo — a standalone tool that simulates
  one or more trucks moving along predefined GPS routes and continuously
  publishes location updates and telematics events (engine started/stopped,
  speed changed, geofence enter/exit, fuel low, idle, route completed) for
  demoing the Fleet Command dashboard without real hardware. Triggers on
  requests like "build the fleet simulator", "simulate truck GPS data",
  "generate fake telematics/GPS data", "create the vehicle tracking
  simulator", "add a route simulator", "simulate 100 trucks", or anything
  about a truck/vehicle-tracking simulator for this project.
---

# Fleet Simulator — Truck GPS & Telematics Simulator

Builds a standalone simulator that generates realistic truck GPS and telematics data, so the Fleet Command dashboard (and the rest of the DriverMonitorPOC stack) can be demoed with a convincing moving fleet instead of waiting on real hardware/telematics units. This is demo tooling for a capability showcase — favor the simplest thing that looks smooth and realistic on a map over a physically accurate traffic/GPS simulation.

**Read `.claude/skills/dms-agentic-architecture/SKILL.md` first** if wiring this simulator's output into `dms-edge` — it defines the Telematics Agent this simulator's `HttpPublisher` primarily targets (see "Publishers" below) and the agent inventory this component fits into as a standalone, non-agentic data source.

## Context to read first

- `specs/FLEET_SIMULATOR_SPEC.md` — the full functional/non-functional spec this skill implements (truck model, route model, GPS update schema, telematics events, simulation controls, publisher interfaces, config file, scale requirements). Treat it as the source of truth; don't redesign the schemas or API surface documented there.
- `.claude/skills/dms-edge-dev/SKILL.md` § "Telematics Agent" — **the primary integration target.** Per the updated deployment design, this simulator sends data *to* a `dms-edge` instance's Telematics Agent (one simulated truck ↔ one edge deployment, correlated by `truckId` == `EDGE_VEHICLE_REGISTRATION`), not directly to `dms-backend`. That's what lets a simulated truck's GPS/speed show up attached to the same vehicle's behaviour-detection alerts on the dashboard.
- `dms-backend/app/schemas.py` and the `dms-backend-dev` skill — relevant only if a user wants the simulator to *also* (or instead) push straight into `dms-backend`, e.g. for fleet vehicles that have no `dms-edge` running at all. There is **no dedicated `/api/telemetry` endpoint** on `dms-backend` today — check its current Inject API surface before assuming one exists.
- `specs/PHASE_2_DEVELOPMENT_PLAN.md` — confirms the whole stack is laptop-first/zero-cloud; the simulator should default to running locally with no external services required to see it work.

## What this component is (and isn't)

This is a **data generator**, not part of the DMS behaviour-detection pipeline (`dms-edge`) or the violation backend (`dms-backend`) themselves — it's the thing that stands in for real trucks/telematics units so those components (and the `dms-ui` map/vehicle views) have something to show. It is **not itself an agent** in the `dms-agentic-architecture` sense (it's a decoupled, standalone data source, not a `BaseAgent` node in the pipeline) — see that skill's agent inventory. Keep it decoupled: it should run fine on its own (printing/logging GPS updates and events) with zero other components running, and optionally push into a `dms-edge` Telematics Agent (primary path) or `dms-backend` directly (secondary path) when those are up.

## Architecture this skill implements

```
config.yaml ──▶ Simulation Engine ──┐
                                      ├─▶ Truck[] (position/speed/heading/status, moving along a Route)
Routes (routes/*.json) ─────────────▶┘        │
                                                ├─▶ GPS Publisher.publishLocation(update) ──▶ console/file/HTTP sink
                                                └─▶ Event Publisher.publishEvent(event) ─────▶ console/file/HTTP sink
Control surface (CLI / optional REST API) ──▶ start / stop / pause / resume / addTruck / removeTruck / loadRoute / setSimulationSpeed
```

- **Simulation Engine**: owns the tick loop (default every `gpsInterval` ms, sped up by `simulationSpeed` multiplier), advances every truck's position along its route, and fires publishers. Use `asyncio` so 100+ trucks can be simulated concurrently without spinning up 100 threads.
- **Truck**: id, optional driver id, current lat/lon, speed, heading, status (`MOVING` / `STOPPED` / `IDLE`). Moves along its assigned route by interpolating between the route's waypoints based on elapsed simulated time and current speed — not teleporting waypoint-to-waypoint, so movement looks smooth on a map.
- **Route**: an ordered list of `{lat, lon}` waypoints loaded from `routes/*.json`. Ship 3 sample routes matching the spec's categories — approximate, illustrative coordinates are fine, this is demo data, not a mapping product:
  - `busy-highway` (e.g. LA → Las Vegas corridor, `la-lasvegas.json`)
  - `medium-highway` (e.g. Dallas → Houston corridor, `dallas-houston.json`)
  - `remote-highway` (e.g. US-50 Nevada — "The Loneliest Road in America", `us50-nevada.json`)
- **Telematics events**: generated from truck state transitions (engine started when a truck begins a route, engine stopped/idle on route completion or a scheduled stop, speed changed when the interpolated speed crosses a threshold) plus geofence enter/exit checks against simple circular/radius zones, and low-probability random events (fuel low) for demo variety. Keep the event generation rules readable and tunable, not a black box.
- **Publishers**: two small interfaces per the spec — `publishLocation(locationUpdate)` and `publishEvent(event)`. Ship a `ConsolePublisher` (prints + appends JSONL to a log file — zero setup, good default) and an `HttpPublisher` (POSTs to a configurable URL **per truck**). The primary target is a `dms-edge` Telematics Agent instance's `POST /telemetry` endpoint (`http://<edge-host>:<TELEMATICS_INGEST_PORT>/telemetry`, default port `5060` — see `dms-edge-dev`), one truck's `HttpPublisher` config pointed at the one edge deployment representing that same vehicle. Only target `dms-backend` directly if a truck has no corresponding `dms-edge` instance. Keep both publishers behind the same base interface so a future Kafka/MQTT publisher (explicitly a "Future Enhancement" in the spec — don't build it now) can be swapped in without touching the engine.
- **Control surface**: a CLI entrypoint is the minimum bar (`start/stop/pause/resume` via flags or a REPL). Add a thin optional FastAPI wrapper (`api/control_api.py`) exposing the same operations over HTTP only if the user wants to trigger/control the simulation from `dms-ui` or another process — don't build it speculatively.

## Folder structure to create

Scaffold this inside the repo root (sibling to `specs/`, `dms-edge/`, `dms-backend/`, `dms-ui/`), only creating what doesn't already exist:

```
fleet-simulator/
├── simulator/
│   ├── __init__.py
│   ├── engine.py             # SimulationEngine: tick loop, start/stop/pause/resume/setSimulationSpeed
│   ├── truck.py              # Truck model + movement interpolation + status state machine
│   ├── route.py              # Route model + loader + waypoint interpolation helpers
│   ├── events.py             # telematics event generation rules
│   └── config.py             # SimulationConfig dataclass, loads config/config.yaml
├── publishers/
│   ├── __init__.py
│   ├── base.py                # Publisher ABC: publishLocation(), publishEvent()
│   ├── console_publisher.py   # default — stdout + JSONL log file, no setup required
│   └── http_publisher.py      # optional — POSTs to dms-backend or any configured URL
├── routes/
│   ├── la-lasvegas.json       # "Busy highway" sample route
│   ├── dallas-houston.json    # "Medium traffic highway" sample route
│   └── us50-nevada.json       # "Remote highway" sample route
├── api/
│   └── control_api.py         # optional FastAPI control surface — only if asked
├── config/
│   └── config.yaml            # simulationSpeed, gpsInterval, defaultSpeed, numberOfTrucks, routes
├── scripts/
│   └── run_simulator.py       # CLI entrypoint: python run_simulator.py --config config/config.yaml
├── tests/
├── requirements.txt
└── README.md
```

Run once when scaffolding:
```bash
mkdir -p fleet-simulator/{simulator,publishers,routes,api,config,scripts,tests}
touch fleet-simulator/simulator/__init__.py fleet-simulator/publishers/__init__.py
```

Add to (or create) the repo `.gitignore`:
```
fleet-simulator/logs/
fleet-simulator/.venv/
fleet-simulator/__pycache__/
```

## Tech stack (open source, laptop-runnable, matches the rest of the repo)

- Python 3.11+ (same language as `dms-edge`/`dms-backend`, so code/patterns are reusable across components)
- `asyncio` (stdlib) — concurrent per-truck tick loop; scales to 100+ trucks without a thread per truck
- `PyYAML` — load `config/config.yaml`
- Plain-Python haversine/linear interpolation for movement between waypoints — no need for a heavyweight geospatial library (`geopandas`, etc.) at POC scale
- `requests` — for `HttpPublisher` pushing into a `dms-edge` Telematics Agent (primary) or `dms-backend` (secondary)
- `random.Random(seed)` — use a seeded instance (not the global `random` module) so runs are reproducible per the spec's determinism requirement
- FastAPI (optional, only for `api/control_api.py`) — reuse the same framework as `dms-backend` for consistency if a control API is needed

## Interfaces (from the spec — keep these exact signatures)

**Simulator API**: `start()`, `stop()`, `pause()`, `resume()`, `addTruck(truckConfig)`, `removeTruck(truckId)`, `loadRoute(routeId)`, `setSimulationSpeed(multiplier)`

**GPS update** (published on every position change, default every `gpsInterval` ms):
```json
{
  "truckId": "TRUCK-001",
  "timestamp": "2026-08-02T10:15:30Z",
  "latitude": 40.12345,
  "longitude": -89.12345,
  "speed": 72,
  "heading": 180,
  "status": "MOVING"
}
```

**Telematics events**: `ENGINE_STARTED`, `ENGINE_STOPPED`, `SPEED_CHANGED`, `ENTERED_GEOFENCE`, `EXITED_GEOFENCE`, `FUEL_LOW`, `IDLE`, `ROUTE_COMPLETED`

## Configuration

`config/config.yaml`:
```yaml
simulationSpeed: 5       # multiplier — 5x means 5 simulated seconds pass per real second
gpsInterval: 1000        # ms between GPS updates per truck
defaultSpeed: 80         # default cruising speed (km/h or mph — pick one and document it)
numberOfTrucks: 20        # snappy default for a live demo; spec requires the engine to scale to 100+
routes:
  - la-lasvegas
  - dallas-houston
  - us50-nevada
seed: 42                  # optional — set for deterministic/reproducible runs
trucks:                   # optional — per-truck HttpPublisher target, only needed once wiring to dms-edge
  - truckId: KA-05-AB-1234
    telematicsAgentUrl: http://localhost:5060/telemetry   # must match that vehicle's dms-edge instance
```

## Non-functional requirements (from the spec — don't skip these)

- Must handle at least 100 concurrently simulated trucks without the tick loop falling behind real time — favor the async tick loop over per-truck threads/processes for this reason.
- Movement must look smooth on a map — interpolate between waypoints based on elapsed time and speed, don't jump truck position waypoint-to-waypoint.
- Same seed → same simulation output. Thread the seeded `random.Random` instance through truck/event generation rather than relying on global random state.
- Keep GPS generation, telemetry/event generation, and any control/UI layer independently swappable — this is why publishers sit behind a small interface instead of being called directly from the engine.

## When building

- Start with `ConsolePublisher` + a handful of trucks on the `remote-highway` route (fewest moving parts, easiest to verify visually via logs) before wiring up `HttpPublisher` or scaling to 100 trucks.
- Don't build the Future Enhancements section of the spec (traffic simulation, weather, driver behavior profiles, historical replay, Kafka/MQTT, vehicle diagnostics) unless specifically asked — they're explicitly out of scope for now.
- If the user wants the simulator's output to drive `dms-ui`'s map/vehicle views *and* correlate with behaviour-detection alerts, wire `HttpPublisher` to the matching `dms-edge` instance's Telematics Agent (`POST /telemetry`) using the same `truckId`/`EDGE_VEHICLE_REGISTRATION` for both — see `dms-edge-dev`. Only wire directly to `dms-backend` if the user explicitly wants GPS-only vehicles with no behaviour-detection agent attached; check the `dms-backend-dev` skill for its current API surface first, since there's no dedicated telemetry route there today.
