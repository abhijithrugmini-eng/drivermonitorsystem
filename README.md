# drivermonitor

Real-time driver-monitoring POC: an edge device (planned, not yet built — see `dms-edge-dev` skill)
runs CV behaviour detection and streams events to a FastAPI backend, which applies violation rules
and serves a live "Fleet Command" dashboard. See `CLAUDE.md` for full architecture/context.

This doc covers running the two components that exist today: `dms-backend` and `dms-ui`.

## Prerequisites

- Python 3.11+ and Node 18+
- [`uv`](https://github.com/astral-sh/uv) (recommended for the backend — see the troubleshooting
  note below)

## 1. Run the backend

```bash
cd dms-backend
uv venv .venv --python 3.13
uv pip install -r requirements.txt --python .venv/bin/python3.13
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API + Swagger docs: http://localhost:8000/docs
- SQLite DB and evidence files are created under `dms-backend/storage/` on first run.

<details>
<summary>Alternative: plain <code>venv</code> + <code>pip</code></summary>

```bash
cd dms-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/start_backend.sh
```
</details>

### Seed demo data (no real edge device needed)

`dms-edge` doesn't exist yet, so use the seed script to exercise the full pipeline
(events → violations → alarms → live dashboard) with a scripted event sequence that triggers
all 4 violation rules:

```bash
cd dms-backend
.venv/bin/python3.13 scripts/seed_demo.py
```

Re-run it any time — it also posts a few "noise" events that deliberately stay under threshold,
to prove the rule engine doesn't over-fire.

## 2. Run the UI

In a second terminal:

```bash
cd dms-ui
npm install
npm run dev
```

- Dashboard: http://localhost:5173
- It talks to the backend at `http://localhost:8000` by default (override via `VITE_API_BASE_URL`,
  see `dms-ui/.env.example`). No dev proxy — CORS is handled by the backend.

## Option: Run with Docker

If you have Docker Desktop running, this replaces steps 1 and 2 above:

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
2. Start the UI (step 2) — it'll load with an empty Overview page.
3. Run `scripts/seed_demo.py` — watch the dashboard update live over WebSocket: summary cards,
   Live Alerts list, and the Alert Detail panel (Trip Details / Evidence / Location / Vehicle /
   In-Cabin Response / Recommended Action) all populate without a page refresh.
4. Click an alert row, then try **Acknowledge** / **Send advisory** — both mutate state on the
   backend and broadcast the update back to the dashboard live.

## Troubleshooting

**`pip`/`venv` fails with a `pyexpat`/`libexpat` symbol error** — seen with Homebrew Python on
some macOS setups, where the system `libexpat.1.dylib` is older than what Homebrew's Python
expects, breaking `ensurepip` for every Homebrew Python install. Use `uv` as shown above — it
downloads its own standalone Python and sidesteps the broken system library.

**Port already in use** — `lsof -ti:8000 -sTCP:LISTEN | xargs -r kill` (or `:5173` for the UI).

For component-specific details (API surface, folder structure, data contract deviations), see
`dms-backend/README.md` and `dms-ui/README.md`.
