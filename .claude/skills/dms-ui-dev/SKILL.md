---
name: dms-ui-dev
description: >-
  Use when scaffolding, building, or extending the "Fleet Command" React
  dashboard for the DriverMonitorPOC — the fleet-wide overview UI with
  sidebar navigation, summary cards, a live alerts list, and an alert
  detail panel (trip details, evidence clip, location, vehicle details,
  in-cabin response, recommended action) matching the project's
  wireframe. Triggers on requests like "build the fleet dashboard",
  "create the driver monitor UI", "add the alerts panel", "set up the
  dms-ui React app", "build the Overview page", or anything about the DMS
  frontend/dashboard.
---

# DMS UI — Fleet Command Dashboard (React)

Builds the frontend of the DriverMonitorPOC: the "Fleet Command" fleet-admin dashboard shown on the right-hand side of the architecture diagram. It's a capability-showcase POC — get a convincing, real-time-feeling UI up fast; polish later.

## Context to read first

Before writing code, skim these files in the repo (paths relative to repo root):
- `specs/ui-wireframe.png` — the exact screen this skill builds (low-fidelity wireframe titled "Fleet Command & Control — Overview (master-detail layout)")
- `specs/VIOLATION_AND_EVIDENCE_MODELS.md` § Violation Model / Evidence Model — the JSON shape the alert cards render (severity, evidence JPG, alarm message, event counts)
- `specs/STRATEGY_MASTER.md` — reference `Dashboard.jsx` sketch (WebSocket pattern, counters) — the real build is richer than this sketch (matches the wireframe's master-detail layout, not just a flat event log) but the WebSocket connection pattern is reusable

**Key decision already made**: backend is `dms-backend` running locally (FastAPI on the laptop, typically `http://localhost:8000`). No cloud API Gateway/Lambda — call the local REST/WebSocket endpoints directly.

Note on `.claude/skills/dms-agentic-architecture/SKILL.md`: the rest of the stack is built as an explicit agent pipeline (Telematics/Behaviour Detection/Cloud Hub agents on the edge, Violation Detection/Alarm/Notification agents on the backend). `dms-ui` is deliberately **not** part of that — it's a REST/WebSocket consumer of what those agents produce, not itself an agent. No changes needed here because of that doc; it's mentioned for context only.

## Screen this skill implements (from the wireframe)

Master-detail layout, single "Overview" screen for the POC (other sidebar items are stubs/later work):

**Left sidebar**: Fleet Command branding + nav — Overview (active), Regions, Routes, Vehicles, Alerts, Reports.

**Top bar**: Region filter, Route filter, and a live status indicator ("● Live — updated 4s ago").

**Summary cards row** (4 cards): Vehicles Active, Critical Alerts, Unacknowledged, Avg Response Time.

**Left column — Live Alerts list**: scrollable list of alert rows, each showing violation type icon, vehicle reg, route/location, time ago, and status (active/selected vs. resolved with a checkmark). Clicking a row selects it and loads the detail panel.

**Right column — Alert detail panel** for the selected alert:
- Header: violation type + vehicle reg + severity badge (e.g. "Drowsiness Alert — KA-05-AB-1234 [CRITICAL]") + Expand action
- **Trip Details**: driver name/ID, route, shift info, speed at event, trip start/elapsed
- **Evidence**: video clip placeholder/player, severity, frame window (e.g. "3 micro-sleeps / 7 min"), capture timestamp, upload/sync status
- **Current Location (map)**: map placeholder + pin, lat/long, distance to nearest waypoint
- **Vehicle Details**: registration, vehicle type, edge device status/firmware
- **In-Cabin Response**: buzzer/alarm firing timestamp, driver acknowledgment latency, speed change after alert
- **Recommended Action**: system-generated suggestion (e.g. "3rd micro-sleep in 7 min. Advise rest stop at Kolar, 4 km ahead.") with a "Send advisory" button
- **Action bar**: Call driver / Acknowledge / Send advisory buttons

## Folder structure to create

Scaffold this inside the repo root (sibling to `specs/`, `dms-edge/`, `dms-backend/`), only creating what doesn't already exist:

```
dms-ui/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx           # nav: Overview, Regions, Routes, Vehicles, Alerts, Reports
│   │   │   └── TopBar.jsx            # Region/Route filters + live status indicator
│   │   ├── overview/
│   │   │   ├── SummaryCards.jsx      # 4-card row
│   │   │   ├── LiveAlertsList.jsx    # scrollable left list, active + resolved rows
│   │   │   └── AlertDetailPanel.jsx  # right panel: trip/evidence/location/vehicle/response/action
│   │   └── shared/
│   │       ├── SeverityBadge.jsx
│   │       └── StatusDot.jsx
│   ├── pages/
│   │   ├── Overview.jsx              # composes TopBar + SummaryCards + LiveAlertsList + AlertDetailPanel
│   │   ├── Regions.jsx               # stub for POC
│   │   ├── Routes.jsx                # stub for POC
│   │   ├── Vehicles.jsx              # stub for POC
│   │   ├── Alerts.jsx                # stub for POC
│   │   └── Reports.jsx               # stub for POC
│   ├── services/
│   │   ├── api.js                    # fetch wrappers for dms-backend REST endpoints
│   │   └── websocket.js              # connects to ws://localhost:8000/ws/alerts
│   ├── hooks/
│   │   └── useLiveAlerts.js          # subscribes to websocket.js, merges into alert list state
│   ├── App.jsx                       # router + layout shell
│   └── main.jsx
├── public/
├── index.html
├── package.json
├── vite.config.js
├── Dockerfile                         # optional — see "Optional: Docker" below
├── nginx.conf                         # optional, pairs with Dockerfile
├── .dockerignore                      # optional
└── README.md
```

Run once when scaffolding (Vite + React, no TypeScript needed for a POC unless the user asks):
```bash
npm create vite@latest dms-ui -- --template react
cd dms-ui && npm install
mkdir -p src/components/{layout,overview,shared} src/pages src/services src/hooks
```

Add to `.gitignore` (Vite's default template already includes most of this):
```
dms-ui/node_modules/
dms-ui/dist/
```

## Tech stack (open source, fast to build)

- React 18 + Vite — fast dev server, no heavyweight framework needed for a POC
- Plain CSS or a lightweight utility approach (Tailwind is fine if the user wants it; don't add it speculatively — the wireframe is achievable with plain CSS grid/flexbox)
- Native `fetch` + native `WebSocket` — no need for React Query/Redux at POC scale; `useState`/`useEffect`/a couple of custom hooks is enough
- `recharts` only if/when a chart is actually requested (matches the "nice to have" charts mentioned in the specs) — don't add it up front

## Data contract with the backend

Pull alert/violation data from `dms-backend`'s Fleet API (see `dms-backend-dev` skill):
- `GET /api/alerts?status=active` → populates the Live Alerts list + summary card counts
- `GET /api/alerts/{id}` → populates the detail panel (trip, evidence, location, vehicle, in-cabin response, recommended action)
- `POST /api/alerts/{id}/acknowledge` → "Acknowledge" button
- `POST /api/alerts/{id}/advisory` → "Send advisory" button
- `WS /ws/alerts` → pushes new/updated alerts; on message, prepend/update the Live Alerts list and bump the "Live — updated Xs ago" indicator

Evidence images/video referenced in the detail panel come from the backend's local evidence folder — the backend should serve them at a static path (e.g. `GET /api/evidence/{event_id}.jpg`) rather than the UI reading the filesystem directly.

## When building

- Match the wireframe's master-detail structure and section names above — the customer demo script depends on scanning quickly between the alert list and detail panel, so preserve the exact real-estate layout (list on the left, detail on the right, cards on top) rather than redesigning it.
- Severity color-coding: CRITICAL = red, HIGH = orange, MEDIUM = yellow, LOW = blue — matches `specs/🎯_COMPLETE_DESIGN_PACKAGE.md` § Violation Rules.
- Treat Regions/Routes/Vehicles/Alerts/Reports as thin stub pages for the POC unless asked to build them out — the demo script only exercises Overview.
- Keep the live-update feel (WebSocket + "updated Xs ago") — it's a core part of the demo per `specs/STRATEGY_MASTER.md`'s "customer sees real-time violations" pitch.

## Optional: Docker

The primary/default workflow is `npm run dev` (Vite dev server). Docker is an **optional
alternative** for when Docker Desktop is available — build it only if the user asks to run in a
Docker/container environment, not speculatively.

- `Dockerfile`: multi-stage — `node:20-alpine` stage runs `npm ci && npm run build`, then an
  `nginx:alpine` stage copies `dist/` and serves it on port 80.
- Vite bakes `VITE_API_BASE_URL` into the static build at build time (it's a client-side env var,
  not read at container runtime) — pass it as a build `ARG`, and it must be a URL the *browser* can
  reach (e.g. `http://localhost:8000`), not a docker-network service name like `http://backend:8000`.
- `nginx.conf`: needs an SPA fallback (`try_files $uri /index.html;`) since `react-router-dom`'s
  `BrowserRouter` handles routes client-side — without it, refreshing on `/vehicles` etc. 404s.
- `.dockerignore`: exclude `node_modules/`, `dist/`.
- Pairs with a root-level `docker-compose.yml` (sibling to `dms-backend/` and `dms-ui/`) that builds
  both services — publish this one on host port `5173` (mapped to the container's nginx port 80) to
  match the local dev port convention, with `depends_on: [backend]`.
