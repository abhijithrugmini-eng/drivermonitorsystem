# dms-edge

Edge/device side of the DriverMonitorPOC. Vendors in `specs/DriverMonitorPOC-main`'s camera-based
detection app (`src/`, unmodified) and adds three agents on top (`agents/`) per
`.claude/skills/dms-agentic-architecture/SKILL.md` and `.claude/skills/dms-edge-dev/SKILL.md`:

- **Telematics Agent** — receives simulated vehicle GPS/telemetry over `POST /telemetry` (port
  `5060`), holds the latest known vehicle state.
- **Behaviour Detection Agent** — thin wrapper around the vendored `DriverMonitoringSystem`
  (MediaPipe Face Mesh + YOLOv8n phone detection).
- **Cloud Hub Agent** — maps each `DMSEvent` + latest vehicle state into `dms-backend`'s Event JSON
  and pushes it to the Inject API (`POST /api/events`, `POST /api/evidence`).

## Run

```bash
cd dms-edge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> If `pip`/`venv` fails with a `pyexpat`/`libexpat` symbol error (Homebrew Python), use
> [`uv`](https://github.com/astral-sh/uv) instead, same workaround as `dms-backend/README.md`:
> ```bash
> uv venv .venv --python 3.13
> uv pip install -r requirements.txt --python .venv/bin/python3.13
> ```

Provide your own input video (none ships in this repo), then:

```bash
python main.py --video videos/dataset.mp4 --no-display
```

- Drop `--no-display` to see the annotated feed live (requires a display).
- `--save` writes an annotated copy to `output/dms_out_<name>.mp4`.
- `--no-ui` disables the local Flask/SSE stub UI (`http://localhost:5050`).
- `--no-cloud` disables the Cloud Hub Agent's push to `dms-backend` (local-only run).
- `--camera <index>` is Phase 2 / not used in this demo — video-file input only for now.

Run `dms-backend` first (see `dms-backend/README.md`) if you want events/evidence to actually land
on the "Fleet Command" dashboard; otherwise the Cloud Hub Agent logs a failed push per event and
keeps going (log-and-drop, no retry queue).

## Telematics ingest (manual, until fleet-simulator exists)

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
| `EDGE_VEHICLE_REGISTRATION` | `EDGE-DEMO-001` | vehicle identity attached to every pushed event |
| `BACKEND_URL` | `http://localhost:8000` | `dms-backend` base URL |
| `TELEMATICS_INGEST_PORT` | `5060` | Telematics Agent's `POST /telemetry` port |
| `DEVICE_ID` | `edge-001` | device identity forwarded to `dms-backend` |

Detection thresholds (EAR/MAR/head-pose/YOLO confidence/cooldowns) are unchanged from the vendored
reference app — see `src/config.py`'s upper section.

## Tests

```bash
pytest tests/
```

Covers `TelematicsAgent`'s state store and `CloudHubAgent`'s `DMSEvent` → backend `EventIn` mapping
— headless, no camera/YOLO/mediapipe dependency.
