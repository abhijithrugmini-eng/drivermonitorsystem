# dms-ui — Fleet Command

React (Vite) master-detail dashboard for the DriverMonitorPOC, matching `specs/ui-wireframe.png`.
Consumes `dms-backend`'s Fleet API (REST) + `/ws/alerts` (WebSocket) for live updates.

## Run

```bash
cd dms-ui
npm install
npm run dev          # http://localhost:5173
```

Requires `dms-backend` running on `http://localhost:8000` (see `dms-backend/README.md`) — CORS is
handled by the backend, no dev proxy is used. Override the backend URL with `VITE_API_BASE_URL`
(see `.env.example`).

To see real data, run `dms-backend`'s `scripts/seed_demo.py` after both servers are up — it stands
in for `dms-edge` (which doesn't exist yet) by posting a scripted event sequence to the backend's
live API, triggering all 4 violation rules end-to-end.

## Structure

Only the Overview page is fully built out (sidebar nav, top bar with live status, 4 summary cards,
Live Alerts list, Alert Detail panel with Trip Details/Evidence/Current Location/Vehicle
Details/In-Cabin Response/Recommended Action). Regions/Routes/Vehicles/Alerts/Reports are minimal
stub pages — the POC demo script only exercises Overview.

Severity color coding (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue) and violation
icon/label mapping live in `src/utils/severity.js` — the single source of truth used by
`SeverityBadge`, `LiveAlertsList`, and `AlertDetailPanel`.
