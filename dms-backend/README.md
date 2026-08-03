# dms-backend

FastAPI service for the DriverMonitorPOC. Ingests events from the edge (or `scripts/seed_demo.py`,
which stands in for `dms-edge` until it exists), applies the 4 violation rules server-side, persists
to a local SQLite database, stores evidence images/video in a local folder, and serves the "Fleet
Command" dashboard (`dms-ui`) over REST + WebSocket.

## Run

```bash
cd dms-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/start_backend.sh          # uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **If `pip`/`venv` fails with a `pyexpat`/`libexpat` symbol error** (seen on this machine's Homebrew
> Python 3.13/3.14 — the system `libexpat.1.dylib` is older than what Homebrew's Python expects, which
> breaks `ensurepip` for every Homebrew Python), use [`uv`](https://github.com/astral-sh/uv) instead —
> it downloads its own standalone Python, sidestepping the broken system library:
> ```bash
> uv venv .venv --python 3.13
> uv pip install -r requirements.txt --python .venv/bin/python3.13
> .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
> ```

Swagger UI: http://localhost:8000/docs

## Demo data (no real edge device required)

```bash
source .venv/bin/activate
python scripts/seed_demo.py
```

Posts a scripted sequence of events for 4 vehicles to the backend's own live `/api/events` endpoint —
one sequence per violation rule (drowsiness, phone usage, distraction, continuous drive), plus a
couple of "noise" events that deliberately stay under threshold. Also uploads a placeholder JPG as
evidence for each triggering event. Prints a summary and polls `GET /api/alerts?status=active` at
the end.

## Data contract deviation from `specs/VIOLATION_AND_EVIDENCE_MODELS.md`

That spec's Event model has no vehicle/driver identity field. This backend extends `context` with
`vehicle_registration` (required) and optional `driver_code`/`driver_name` — vehicles and drivers are
looked up or created on first sighting (get-or-create). Evidence is stored as files under
`storage/evidence/{images,videos}/`, not inline base64 JPG — the spec's older inline-base64 approach
is superseded by `.claude/skills/dms-backend-dev/SKILL.md`.

## Violation lifecycle

One ACTIVE violation per `(vehicle, violation_type)`. New matching events update it in place
(`event_count`, evidence, `recommended_action_text` keep climbing) rather than spawning a duplicate
row per re-trigger; a fresh violation only opens once the previous one is acknowledged. Each
create/update broadcasts over `WS /ws/alerts` as `{"type": "alert_created" | "alert_updated", "alert": {...}}`.

## API surface

| Endpoint | Consumer | Purpose |
|---|---|---|
| `POST /api/events` | dms-edge / seed script | ingest an Event, persist, run rule engine |
| `POST /api/evidence` | dms-edge / seed script | multipart upload of an image/video for an event_id |
| `GET /api/vehicles` | dms-ui | fleet list |
| `GET /api/alerts?status=active` | dms-ui | Live Alerts list |
| `GET /api/alerts/{id}` | dms-ui | full alert detail (trip/evidence/location/vehicle/in-cabin/recommended-action) |
| `POST /api/alerts/{id}/acknowledge` | dms-ui | Acknowledge button |
| `POST /api/alerts/{id}/advisory` | dms-ui | Send advisory button |
| `GET /api/evidence/{filename}` | dms-ui | serves stored evidence image/video |
| `WS /ws/alerts` | dms-ui | live alert push |

## Config

Thresholds, DB path, evidence dir, host/port live in `app/config.py` — tune live for demos.
