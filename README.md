# drivermonitor

Real-time driver-monitoring POC: an edge device runs CV behaviour detection and local violation
detection (`dms-edge`), an in-cabin alarm fires with no cloud round-trip, and the finished result
syncs to a FastAPI backend (`dms-backend`) that serves a live "Fleet Command" dashboard (`dms-ui`).
See `CLAUDE.md` for full architecture/context.

This doc covers running all three components that exist today: `dms-backend`, `dms-ui`, and
`dms-edge`. `fleet-simulator` does not exist on disk yet (see `CLAUDE.md`'s "Project state").

**Credit**: `dms-edge`'s core detection logic and AI models (MediaPipe face-mesh drowsiness/yawn
detection, YOLOv8 phone-usage detection) come from
[raviR-lab/DriverMonitorPOC](https://github.com/raviR-lab/DriverMonitorPOC), vendored in unmodified
under `specs/DriverMonitorPOC-main/`. `dms-edge` is an **agentification** of that project — it wraps
the same detection core in a `BaseAgent` pipeline (Telematics, Behaviour Detection, Violation
Detection, Alarm, Cloud Hub agents) and integrates it with a local, on-device violation-detection
model (a SQLite sliding-window rule engine) so violations are decided on the vehicle, not just
raw behaviour events.

## Prerequisites

- Python 3.11+ and Node 18+
- `uv` and Docker Desktop are both **optional accelerators, not requirements** — every command
  below has a plain `venv`/`pip` form that works the same way on Windows, Linux, and macOS with no
  extra tools installed. This matters most on locked-down Windows workstations where installing
  `uv` or Docker isn't an option. Where `uv` or Docker happen to already be on your machine, an
  optional faster path is called out — use it if you like, skip it otherwise.

The commands below work the same on Windows, Linux, and macOS unless a tab says otherwise — the
only real difference is venv activation syntax and which Python launcher you use.

## 1. Run the backend

<details open>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
   cd dms-backend
   py -3.11 -m venv .venv
   .\.venv\Scripts\pip.exe install -r requirements.txt
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

No `uv` needed on Windows — plain `venv`/`pip` works fine here. If `py -3.11` isn't found, install
Python 3.11 from [python.org](https://www.python.org/downloads/) or the Microsoft Store, or swap in
whichever 3.11+ interpreter `py -0p` lists.
</details>

<details>
<summary><b>Linux / macOS</b></summary>

```bash
cd dms-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/start_backend.sh          # uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If `pip`/`venv` fails with a `pyexpat`/`libexpat` symbol error (seen with Homebrew Python on some
macOS setups — the system `libexpat.1.dylib` is older than Homebrew's Python expects, breaking
`ensurepip`), use [`uv`](https://github.com/astral-sh/uv) instead — it downloads its own standalone
Python and sidesteps the broken system library:

```bash
uv venv .venv --python 3.13
uv pip install -r requirements.txt --python .venv/bin/python3.13
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
</details>

- API + Swagger docs: http://localhost:8000/docs
- SQLite DB and evidence files are created under `dms-backend/storage/` on first run.

### Seed demo data (no `dms-edge` run needed)

Skip step 2 (`dms-edge`) entirely and use this seed script instead to exercise the full pipeline
(events → violations → alarms → live dashboard) with a scripted event sequence that triggers
all 4 violation rules — handy when you don't have a demo video or camera handy. Run it in a new
terminal while the backend is running:

```powershell
# Windows
cd dms-backend
.\.venv\Scripts\python.exe scripts\seed_demo.py
```

```bash
# Linux / macOS
cd dms-backend
source .venv/bin/activate   # or .venv/bin/python3.13 scripts/seed_demo.py if you used uv
python scripts/seed_demo.py
```

Re-run it any time — it also posts a few "noise" events that deliberately stay under threshold,
to prove the rule engine doesn't over-fire.

## 2. Run the edge (optional — `scripts/seed_demo.py` can stand in for it)

`dms-edge` runs every edge agent (Telematics, Behaviour Detection, Violation Detection, Alarm,
Cloud Hub) in one process against a video file, pushing events/violations to the backend from step
1. It needs its own `venv` (separate from `dms-backend`'s) and, unlike the backend/UI, isn't in
`docker-compose.yml` yet. If you just want to see the dashboard populate, skip this and use the
"Seed demo data" step below instead — `dms-edge` matters when you want to demo the actual
local/on-vehicle detection path described in `CLAUDE.md`.

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
cd dms-edge
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe main.py --video videos\dataset.mp4 --no-display --vehicle-config fleet\example-vehicle-config.json
```
</details>

<details>
<summary><b>Linux / macOS</b></summary>

```bash
cd dms-edge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --video videos/dataset.mp4 --no-display --vehicle-config fleet/example-vehicle-config.json
```
</details>

You provide your own input video (none ships in this repo). By default this also starts an
in-process **Telematics Simulator** that generates plausible GPS/speed/RPM automatically — no
separate process needed. To tag the run with a specific truck/driver identity (and optionally a
GPS route the simulator follows), add `--vehicle-config fleet\example-vehicle-config.json` (a
sample ships in `dms-edge/fleet/`). This also drives the dashboard's **Trip Details** card
(driver, route, shift, speed at event, trip started) — see `demo/DEMO_GUIDE.md`'s
"Trip Details (driver, route, shift, speed, trip started)" section for exactly which config
fields feed which card fields. Full flag reference, the sample config's shape, the local
telemetry-ingest endpoint, and troubleshooting: `dms-edge/README.md`.

## 3. Run the UI

In a second terminal (same commands on all three OSes):

```bash
   cd dms-ui
   npm install
   npm run dev
```

- Dashboard: http://localhost:5173
- It talks to the backend at `http://localhost:8000` by default (override via `VITE_API_BASE_URL`,
  see `dms-ui/.env.example`). No dev proxy — CORS is handled by the backend.

## Option: Run backend + UI with Docker

Available only if Docker Desktop is already installed — if it isn't, use the venv/`npm run dev`
steps above instead, they work identically. When available, this replaces steps 1 and 3 above
(`dms-backend` + `dms-ui` only — `dms-edge` isn't containerized yet, see step 2):

```bash
docker compose up --build
```

- Backend: http://localhost:8000/docs
- UI: http://localhost:5173

`dms-backend`'s SQLite DB and evidence files persist in a named volume across restarts. Seed demo
data the same way, just via `exec` into the running container instead of a local `.venv`:

```bash
docker compose exec backend python scripts/seed_demo.py
```

Stop with `docker compose down` (add `-v` to also drop the storage volume and start fresh next time).

This is an **optional alternative** to the local venv/`npm run dev` workflow above, not a
replacement for it — use whichever fits your environment. See `dms-backend/Dockerfile`,
`dms-ui/Dockerfile`, and `docker-compose.yml` for details.

## Demo flow

1. Start the backend (step 1).
2. Start the UI (step 3) — it'll load with an empty Overview page.
3. Either run `dms-edge` (step 2) against a video file — its Cloud Hub Agent pushes real
   events/violations from the local detection pipeline — or run `scripts/seed_demo.py` (below) to
   simulate the same pipeline without a video/camera. Watch the dashboard update live over
   WebSocket: summary cards, Live Alerts list, and the Alert Detail panel (Trip Details / Evidence /
   Location / Vehicle / In-Cabin Response / Recommended Action) all populate without a page refresh.
   Trip Details (driver, route, shift, speed at event, trip started) only shows real values instead
   of "—"/"Unknown driver" if `dms-edge` was launched with `--vehicle-config` — see step 2 above.
4. Click an alert row, then try **Acknowledge** / **Send advisory** — both mutate state on the
   backend and broadcast the update back to the dashboard live.

## Troubleshooting

**`pip`/`venv` fails with a `pyexpat`/`libexpat` symbol error** — seen with Homebrew Python on
some macOS setups, where the system `libexpat.1.dylib` is older than what Homebrew's Python
expects, breaking `ensurepip` for every Homebrew Python install. Use `uv` as shown above — it
downloads its own standalone Python and sidesteps the broken system library.

**Port already in use**
- Linux/macOS: `lsof -ti:8000 -sTCP:LISTEN | xargs -r kill` (or `:5173` for the UI).
- Windows (PowerShell): `Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force` (or `-LocalPort 5173` for the UI).

**Windows: `.venv` scripts blocked by execution policy** — if activating fails with a script-execution
error, either call the `.venv\Scripts\python.exe`/`pip.exe` executables directly (as shown above,
which avoids activation entirely) or run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current terminal session.

For component-specific details (API surface, folder structure, data contract deviations), see
`dms-backend/README.md`, `dms-ui/README.md`, and `dms-edge/README.md`.
