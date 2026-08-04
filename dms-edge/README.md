# dms-edge

Edge/device side of the DriverMonitorPOC. Vendors in `specs/DriverMonitorPOC-main`'s camera-based
detection app (`src/`, unmodified) and adds five agents on top (`agents/`) per
`.claude/skills/dms-agentic-architecture/SKILL.md` and `.claude/skills/dms-edge-dev/SKILL.md`. A
single `python main.py` run starts **all** of them together (see "What `main.py` starts" below) —
there's nothing else to launch separately:

- **Telematics Agent** — receives simulated vehicle GPS/telemetry over `POST /telemetry` (port
  `5060`), holds the latest known vehicle state.
- **Behaviour Detection Agent** — thin wrapper around the vendored `DriverMonitoringSystem`
  (MediaPipe Face Mesh + YOLOv8n phone detection).
- **Violation Detection Agent** — evaluates the 4 violation rules against a local SQLite sliding
  window (`storage/local.db`) — the primary, on-vehicle detection path (see root `CLAUDE.md`).
- **Alarm Agent** — fires the escalation-tier in-cabin alert for each violation.
- **Cloud Hub Agent** — maps each `DMSEvent`/`Violation` + latest vehicle state into `dms-backend`'s
  JSON contracts and pushes them to the Inject API (`POST /api/events`, `POST /api/evidence`,
  `POST /api/violations`).

## Run

The baseline path below uses only the Python standard library's `venv` + `pip` — no extra tools
required — and works the same way on Windows, Linux, and macOS. This is the path to use on locked-down
Windows workstations where installing `uv` or Docker Desktop isn't an option. If `uv` and/or Docker
*are* available on your machine, the call-out boxes after each step show the faster equivalent — use
whichever fits your environment; neither is required.

<details open>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
cd dms-edge
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
```

If `py -3.11` isn't found, install Python 3.11 from [python.org](https://www.python.org/downloads/)
or the Microsoft Store, or swap in whichever 3.11+ interpreter `py -0p` lists. No `uv` needed on
Windows — plain `venv`/`pip` works fine here.
</details>

<details>
<summary><b>Linux / macOS</b></summary>

```bash
cd dms-edge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
</details>

> **Optional, only if `uv` is already installed on your machine:** [`uv`](https://github.com/astral-sh/uv)
> is a faster drop-in for the steps above, and is also the workaround if `pip`/`venv` fails with a
> `pyexpat`/`libexpat` symbol error (seen with Homebrew Python on some macOS setups — the system
> `libexpat.1.dylib` is older than Homebrew's Python expects, breaking `ensurepip`). Not required —
> skip this if `uv` isn't already on your machine:
> ```bash
> uv venv .venv --python 3.13
> uv pip install -r requirements.txt --python .venv/bin/python3.13
> ```

> **Optional, only if Docker Desktop is already installed:** `dms-edge` isn't containerized yet (no
> `Dockerfile` in this folder) — see `.claude/skills/dms-edge-dev/SKILL.md`'s "Optional: Docker"
> section for the planned image (targets the on-board ARM64 device, not just a laptop demo). Until
> that lands, use the venv path above on all three OSes, Docker or not.

Provide your own input video (none ships in this repo), then run every dms-edge agent/component
together via `main.py` — it wires up the Telematics Agent, Behaviour Detection Agent, Violation
Detection Agent, Alarm Agent, Cloud Hub Agent, and the local Flask/SSE UI in one process (see
"What `main.py` starts" below):

**Windows:**
```powershell
.\.venv\Scripts\python.exe main.py --video videos\dataset.mp4 --no-display
```

**Linux / macOS:**
```bash
python main.py --video videos/dataset.mp4 --no-display
```

### What `main.py` starts

One process, one command, all agents — no separate terminals needed for the edge side itself:

1. `init_db()` creates/opens `storage/local.db` (SQLite, for the Violation Detection Agent's
   sliding window).
2. **Telematics Agent** starts its `POST /telemetry` listener on a background thread (port `5060`).
3. **Behaviour Detection Agent**, **Violation Detection Agent**, **Alarm Agent**, and (unless
   `--no-cloud`) **Cloud Hub Agent** are constructed.
4. Unless `--no-ui`, the local Flask/SSE stub UI starts on a background thread
   (`http://localhost:5050`).
5. The main thread reads `--video` frame-by-frame, runs the Behaviour Detection Agent on each
   frame, and for every `DMSEvent` produced: logs it, runs the Violation Detection Agent, runs the
   Alarm Agent if a violation fired, and (unless `--no-cloud`) pushes the event/violation via the
   Cloud Hub Agent.

Flags:

- Drop `--no-display` to see the annotated feed live (requires a display).
- `--save` writes an annotated copy to `output/dms_out_<name>.mp4`.
- `--no-ui` disables the local Flask/SSE stub UI (`http://localhost:5050`).
- `--no-cloud` disables the Cloud Hub Agent's push to `dms-backend` (local-only run).
- `--camera <index>` is Phase 2 / not used in this demo — video-file input only for now.
- `--vehicle-config <path.json>` supplies this run's truck/driver identity (required fields:
  `vehicle_registration`, `vin`, `fleet_id`, `driver_name`, `driver_id`; any other JSON keys are
  forwarded to `dms-backend` as opaque metadata) — see `fleet/example-vehicle-config.json`. Missing
  a required field exits before any video is opened. When omitted, identity falls back to the
  `EDGE_VEHICLE_REGISTRATION` env var and no driver is attached. Optionally include a `"route"`
  block (`from_lat`/`from_lon`/`to_lat`/`to_lon`/`avg_speed_kmh`/`duration_secs`) to drive the
  Telematics Simulator's GPS-position-from-speed tandem instead of its canned-waypoint fallback.

Run `dms-backend` first (see `dms-backend/README.md`) if you want events/evidence to actually land
on the "Fleet Command" dashboard; otherwise the Cloud Hub Agent logs a failed push per event and
keeps going (log-and-drop, no retry queue).

### `--vehicle-config` example

```powershell
.\.venv\Scripts\python.exe main.py --video videos\dataset.mp4 --no-display `
  --vehicle-config fleet\example-vehicle-config.json
```

`fleet/example-vehicle-config.json` ships in this folder:

```json
{
  "vehicle_registration": "MH-12-AB-4321",
  "vin": "1HGCM82633A004352",
  "fleet_id": "FLEET-WEST-07",
  "driver_name": "Ramesh Kulkarni",
  "driver_id": "DRV-10245",
  "route_name": "Mumbai-Pune Corridor",
  "shift_label": "Day Shift (06:00-14:00)",
  "depot": "Pune Hub 3",
  "insurance_expiry": "2027-01-15",
  "notes": "Demo truck for AI COE showcase",
  "route": {
    "from_lat": 18.5204,
    "from_lon": 73.8567,
    "to_lat": 18.5384,
    "to_lon": 73.8757,
    "avg_speed_kmh": 60,
    "duration_secs": 180
  }
}

```

The 5 top-level fields (`vehicle_registration`, `vin`, `fleet_id`, `driver_name`, `driver_id`) are
required whenever `--vehicle-config` is given; any other top-level key is passed through to
`dms-backend` untouched as opaque metadata (`context.vehicle_meta`) — add whatever fields you need.
The optional `route` block drives the GPS/speed tandem: `from_lat`/`from_lon` → `to_lat`/`to_lon` is
the path, `avg_speed_kmh` paces it, and `duration_secs` is how long the trip should take — set it to
roughly your `--video` file's length so the simulated truck arrives around when the demo ends. Once
`duration_secs` elapses the truck holds at the destination and reports `speed_kmh: 0`. Omit `route`
to fall back to the canned-waypoint model. Copy this file and edit it per truck/demo — a required
field missing from your copy makes `main.py` print which one and exit before opening the video.

## Telematics ingest (manual, until fleet-simulator exists)

**Windows (PowerShell):**
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:5060/telemetry `
  -ContentType "application/json" `
  -Body '{"truckId":"EDGE-DEMO-001","latitude":34.05,"longitude":-118.25,"speed":72,"heading":180,"status":"MOVING"}'

Invoke-RestMethod http://localhost:5060/telemetry   # read back the stored latest state
```

**Linux / macOS:**
```bash
curl -X POST http://localhost:5060/telemetry \
  -H "Content-Type: application/json" \
  -d '{"truckId":"EDGE-DEMO-001","latitude":34.05,"longitude":-118.25,"speed":72,"heading":180,"status":"MOVING"}'

curl http://localhost:5060/telemetry   # read back the stored latest state
```

`truckId` must match `EDGE_VEHICLE_REGISTRATION` (below) so the Fleet Simulator's per-truck stream
and this edge instance's behaviour events land on the same `dms-backend` vehicle row.

## Config

All in `src/config.py`, tunable via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `EDGE_VEHICLE_REGISTRATION` | `EDGE-DEMO-001` | vehicle identity attached to every pushed event (overridden by `--vehicle-config` when given) |
| `BACKEND_URL` | `http://localhost:8000` | `dms-backend` base URL |
| `TELEMATICS_INGEST_PORT` | `5060` | Telematics Agent's `POST /telemetry` port |
| `DEVICE_ID` | `edge-001` | device identity forwarded to `dms-backend` |
| `TELEMATICS_SOURCE` | `simulator` | `"simulator"` starts the in-process Telematics Simulator thread; `"http"` leaves telemetry purely to `POST /telemetry` |
| `TELEMATICS_SIM_INTERVAL_SECS` | `1.5` | Telematics Simulator tick interval |

Detection thresholds (EAR/MAR/head-pose/YOLO confidence/cooldowns) are unchanged from the vendored
reference app — see `src/config.py`'s upper section.

## Tests

**Windows:**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/
```

**Linux / macOS:**
```bash
pytest tests/
```

Covers `TelematicsAgent`'s state store and `CloudHubAgent`'s `DMSEvent` → backend `EventIn` mapping
— headless, no camera/YOLO/mediapipe dependency.

## Troubleshooting

**`pip`/`venv` fails with a `pyexpat`/`libexpat` symbol error** — macOS/Linux only, see the `uv`
call-out above. Not applicable on Windows.

**Windows: `.venv` scripts blocked by execution policy** — call `.venv\Scripts\python.exe`/`pip.exe`
directly (as shown throughout this doc, which avoids activation entirely) or run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current terminal session.

**Port already in use (`5060` telemetry, `5050` local UI)**
- Linux/macOS: `lsof -ti:5060 -sTCP:LISTEN | xargs -r kill` (swap in `5050` as needed).
- Windows (PowerShell): `Get-NetTCPConnection -LocalPort 5060 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force`
