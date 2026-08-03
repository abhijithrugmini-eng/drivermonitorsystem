# Quick & Dirty POC — 2 Week Sprint (Aug 1-14)

**Team**: 4 people (AI Eng, Edge Expert, UI Guy, You as Server Lead)  
**Goal**: Showcase AI capabilities for customer demos & RFPs  
**Scope**: Simple, manual tuning OK, demo-focused  
**Cost**: Minimal (use existing, no new infra)

---

## 🎯 What We're Building

```
Edge Device (Laptop/Board)
├─ Run existing DMS (YOLO + MediaPipe)
└─ Detect: drowsiness, phone, distraction

↓ (REST API)

Your Server (FastAPI)
├─ Receive events
├─ Store in JSON file (no DB)
└─ Stream to UI via WebSocket

↓ (WebSocket)

UI (React)
└─ Real-time violation dashboard
   ├─ Event stream
   ├─ Violation counter
   └─ Simple charts
```

**That's it.** No multi-agent nonsense, no InfluxDB, no containerization for showcase.

---

## 👥 Team Tasks (Quick Reference)

### **AI Engineer** (Edge Detection)
- [ ] Refactor `dms.py` to emit events in JSON format
- [ ] Add REST API call: `POST http://server:8000/events` after detection
- [ ] Test with demo video (drowsy_drive.mp4)
- [ ] Manual tuning: EAR threshold, cooldowns (for demo)
- [ ] **Time**: 3 days

### **Edge Expert** (Hardware/Integration)
- [ ] Set up laptop/board to run DMS with network access
- [ ] Create simple `start_dms.sh` script (just runs main.py with server URL)
- [ ] Create test video with known violations
- [ ] Verify events flow to server
- [ ] Network debugging (if needed)
- [ ] **Time**: 2 days

### **UI Guy** (Dashboard)
- [ ] Create React SPA (localhost:3000)
- [ ] WebSocket listener for `/events` stream
- [ ] Real-time event list (drowsiness, phone, distraction)
- [ ] Simple counter: total violations
- [ ] Simple line chart: violations per minute
- [ ] Violation detail popup (show metrics)
- [ ] **Time**: 4 days

### **You (Server)** (FastAPI Backend)
- [ ] FastAPI server with 3 endpoints:
  - `POST /events` (receive detection events)
  - `GET /events/stream` (WebSocket for UI)
  - `GET /violations/summary` (stats)
- [ ] Event storage (JSON file, no DB)
- [ ] Event broadcasting to connected UIs
- [ ] Demo mode: if no edge events, inject fake ones
- [ ] **Time**: 3 days

---

## 📋 Detailed Tasks

### **AI Engineer's Sprint**

```
Day 1: Event Format
  □ Modify dms.py to create JSON event structure:
    {
      "type": "DROWSINESS",
      "severity": "CRITICAL",
      "timestamp": 1722638401.23,
      "metrics": {"ear": 0.18, "duration": 0.75},
      "trip_stats": {"total_drowsiness_count": 3}
    }
  □ Remove TTS stub (we'll skip audio for demo)
  □ Keep JSONL logging (for debugging)

Day 2: Event Transmission
  □ After each violation, call:
    requests.post(f"http://server:8000/events", json=event_data, timeout=1)
  □ Handle network errors gracefully (don't crash DMS)
  □ Test with server running

Day 3: Demo Tuning
  □ Run drowsy_drive.mp4 video
  □ Count events → adjust EAR_THRESHOLD & EAR_CONSEC_SECS
  □ Goal: 3-5 drowsiness events in 2-min clip
  □ Test phone detection (if video has phone)
  □ Test distraction (head turning)

ACCEPTANCE:
✓ Events reach server in JSON format
✓ No crashes when server offline
✓ Demo video generates expected violations
```

### **Edge Expert's Sprint**

```
Day 1: Environment Setup
  □ Verify DMS runs on target device (laptop or board)
  □ Check Python deps: cv2, mediapipe, onnxruntime
  □ Download/verify video file (drowsy_drive.mp4 exists)
  □ Measure baseline FPS (should be 10-30 FPS)

Day 2: Network Integration
  □ Create scripts/start_poc.sh:
    #!/bin/bash
    export DMS_SERVER_URL="http://192.168.1.X:8000"
    python main.py --video videos/drowsy_drive.mp4 --server-url $DMS_SERVER_URL
  □ Test: DMS connects to server before starting
  □ Create fallback: if server unreachable, still runs (logs locally only)
  □ Document IP address for UI guy

ACCEPTANCE:
✓ DMS runs with network flag
✓ Can change server URL via env var
✓ Graceful degradation if server down
```

### **UI Guy's Sprint**

```
Day 1: Basic React Setup
  □ Create React app with:
    - Header: "DMS Real-Time Dashboard"
    - Main panel: Event list (scrollable)
    - Stats panel: Total drowsiness / phone / distraction counts
  □ Connect to server WebSocket (localhost:8000/events/stream)

Day 2: Real-Time Updates
  □ WebSocket listener:
    ws.onmessage = (event) => {
      data = JSON.parse(event.data)
      setEvents([...events, data])
      updateCounts()
    }
  □ Display event in list:
    - Type (badge: red for CRITICAL, orange for others)
    - Timestamp
    - Metrics (EAR, duration, etc.)

Day 3: Charts + Polish
  □ Add Recharts simple line chart:
    - X-axis: Time (rolling 5 min)
    - Y-axis: Violation count per minute
  □ Add event detail modal:
    - Click event → show all metrics
  □ Add "Clear" button (reset stats)
  □ Responsive design (mobile-friendly)

ACCEPTANCE:
✓ Dashboard loads at localhost:3000
✓ WebSocket connects on startup
✓ Events appear in real-time
✓ Chart updates smoothly
```

### **You (Server) Sprint**

```
Day 1: FastAPI Endpoints
  □ POST /events
    - Accept JSON event
    - Store in list (in-memory)
    - Broadcast to all connected WebSocket clients
  □ GET /events/stream (WebSocket)
    - Client connects
    - Sends all recent events (last 100)
    - Streams new events as they arrive
  □ GET /violations/summary
    - Return: {"drowsiness": 3, "phone": 1, "distraction": 2, ...}

Day 2: Demo Mode + Storage
  □ Add --demo flag to FastAPI:
    ./start_server.py --demo
    → Sends fake events every 5 sec for testing
  □ Persist events to JSON file:
    logs/events.jsonl (one event per line)
  □ Handle client disconnects gracefully
  □ CORS headers (for localhost:3000)

Day 3: Testing + Deployment
  □ Test flow end-to-end:
    - Start server
    - Start DMS (point at server)
    - Open dashboard
    - Verify events flow
  □ Create docker-compose.yml (optional, for easy deployment):
    - FastAPI service
    - React build service (static)
  □ Document: how to run locally vs. on board

ACCEPTANCE:
✓ Server runs on 0.0.0.0:8000
✓ Dashboard connects and receives events
✓ No data loss during demo
✓ Can run in demo mode (fake data)
```

---

## 📅 2-Week Timeline

```
Week 1
Mon   □ Standup + planning (30 min)
      □ AI: Start event format
      □ Edge: Environment setup
      □ UI: React skeleton
      □ You: FastAPI endpoints

Tue   □ AI: Event transmission
      □ Edge: Network integration
      □ UI: WebSocket listener
      □ You: WebSocket broadcaster

Wed   □ AI: Demo tuning (drowsy video)
      □ Edge: Test DMS + network
      □ UI: Real-time updates
      □ You: Demo mode endpoint

Thu   □ Integration testing
      □ AI: Verify events flow
      □ Edge: Verify network
      □ UI: Verify dashboard updates
      □ You: Verify no data loss

Fri   □ Demo dry-run
      □ Fix any glitches
      □ Tune thresholds
      □ Document setup

Week 2
Mon   □ Customer demo ready (or RFP showcase)
      □ Final testing on target device
      □ Practice narration (what to say)

Tue-Wed
      □ Run demos for customers/partners
      □ Take notes on feedback
      □ Quick bug fixes if needed

Thu   □ Debrief + feedback
      □ Identify Phase 2 asks
      □ Archive demo artifacts

Fri   □ Wrap-up + lessons learned
```

---

## 🛠️ Tech Stack (Keep It Simple)

| Component | Tech | Why |
|-----------|------|-----|
| Edge | Python 3.8+ (existing) | Already have YOLO + MediaPipe |
| Server | FastAPI | 10 lines of code per endpoint |
| Storage | JSON file | No DB setup needed |
| UI | React + Recharts | Simple charts, real-time |
| Real-time | WebSocket | Built into FastAPI |
| Deploy | Docker Compose | Optional, for ease |

---

## 📂 Code Snippets (Copy-Paste Ready)

### **1. AI Engineer: Event Emission (dms.py)**

```python
import requests
import json
from datetime import datetime

class DriverMonitoringSystem:
    def __init__(self, server_url=None):
        self.server_url = server_url
        # ... existing init code ...
    
    def _emit_event(self, event_type, severity, metrics):
        """Send event to server"""
        event = {
            "type": event_type,
            "severity": severity,
            "timestamp": time.time(),
            "metrics": metrics,
            "trip_stats": self.trip.snapshot()
        }
        
        # Log locally
        with open("logs/events.jsonl", "a") as f:
            f.write(json.dumps(event) + "\n")
        
        # Send to server (if configured)
        if self.server_url:
            try:
                requests.post(
                    f"{self.server_url}/events",
                    json=event,
                    timeout=0.5  # Don't block frame processing
                )
            except Exception as e:
                print(f"[WARNING] Server unreachable: {e}")
```

### **2. Your Server: FastAPI (src/server/app.py)**

```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime

app = FastAPI()

# Enable CORS for localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory event storage
events = []
clients = []

@app.post("/events")
async def receive_event(event: dict):
    """Receive event from edge device"""
    events.append(event)
    
    # Save to file
    with open("logs/events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")
    
    # Broadcast to all connected UIs
    for client in clients:
        try:
            await client.send_json(event)
        except:
            clients.remove(client)
    
    return {"status": "received"}

@app.websocket("/events/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for UI to receive events"""
    await websocket.accept()
    clients.append(websocket)
    
    # Send recent events
    for event in events[-100:]:
        await websocket.send_json(event)
    
    # Keep connection open, send new events
    try:
        while True:
            await asyncio.sleep(0.1)
    except:
        clients.remove(websocket)

@app.get("/violations/summary")
async def get_summary():
    """Return violation counts"""
    counts = {}
    for event in events:
        event_type = event.get("type", "UNKNOWN")
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts

# Demo mode
@app.on_event("startup")
async def demo_mode():
    """Optional: inject fake events for testing"""
    if os.getenv("DEMO_MODE"):
        asyncio.create_task(fake_events_loop())

async def fake_events_loop():
    """Send fake events every 5 seconds"""
    import random
    types = ["DROWSINESS", "PHONE_USAGE", "DISTRACTION"]
    while True:
        event = {
            "type": random.choice(types),
            "severity": "CRITICAL",
            "timestamp": time.time(),
            "metrics": {"confidence": random.uniform(0.7, 0.99)},
        }
        events.append(event)
        for client in clients:
            try:
                await client.send_json(event)
            except:
                pass
        await asyncio.sleep(5)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### **3. UI Guy: React Dashboard (web/src/Dashboard.jsx)**

```jsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [counts, setCounts] = useState({});
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/events/stream');
    
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents(prev => [event, ...prev.slice(0, 100)]);
      
      // Update counts
      setCounts(prev => ({
        ...prev,
        [event.type]: (prev[event.type] || 0) + 1
      }));
      
      // Update chart (every minute)
      const now = new Date().getTime();
      setChartData(prev => {
        const last = prev[prev.length - 1];
        if (!last || now - last.time > 60000) {
          return [...prev, { time: now, count: Object.values(counts).reduce((a,b)=>a+b,0) }];
        }
        return prev;
      });
    };
    
    return () => ws.close();
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>🚗 DMS Real-Time Dashboard</h1>
      
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
          <h3>😴 Drowsiness</h3>
          <p style={{ fontSize: '24px', color: 'red' }}>{counts.DROWSINESS || 0}</p>
        </div>
        <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
          <h3>📱 Phone Usage</h3>
          <p style={{ fontSize: '24px', color: 'orange' }}>{counts.PHONE_USAGE || 0}</p>
        </div>
        <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
          <h3>👀 Distraction</h3>
          <p style={{ fontSize: '24px', color: 'yellow' }}>{counts.DISTRACTION || 0}</p>
        </div>
      </div>

      {/* Chart */}
      <LineChart width={800} height={300} data={chartData}>
        <CartesianGrid />
        <XAxis dataKey="time" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="count" stroke="#8884d8" />
      </LineChart>

      {/* Event Log */}
      <h2>📋 Event Log</h2>
      <div style={{ height: '300px', overflow: 'auto', border: '1px solid #ddd' }}>
        {events.map((e, i) => (
          <div
            key={i}
            onClick={() => setSelectedEvent(e)}
            style={{
              padding: '10px',
              borderBottom: '1px solid #eee',
              backgroundColor: e.type === 'DROWSINESS' ? '#ffe6e6' : e.type === 'PHONE_USAGE' ? '#fff4e6' : '#fffde6',
              cursor: 'pointer'
            }}
          >
            <strong>{e.type}</strong> @ {new Date(e.timestamp * 1000).toLocaleTimeString()}
            {e.metrics && <span> (EAR: {e.metrics.ear?.toFixed(2) || 'N/A'})</span>}
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {selectedEvent && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '10px', maxWidth: '500px' }}>
            <h3>{selectedEvent.type}</h3>
            <pre>{JSON.stringify(selectedEvent, null, 2)}</pre>
            <button onClick={() => setSelectedEvent(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
```

### **4. Edge Expert: Start Script (scripts/start_poc.sh)**

```bash
#!/bin/bash

# Configuration
SERVER_URL=${1:-"http://localhost:8000"}
VIDEO=${2:-"videos/drowsy_drive.mp4"}

echo "🚀 Starting POC..."
echo "  Server: $SERVER_URL"
echo "  Video: $VIDEO"

# Verify server is up
echo "Checking server..."
if ! curl -s "$SERVER_URL/violations/summary" > /dev/null; then
    echo "⚠️  Server not responding. Start it first:"
    echo "   python src/server/app.py"
    exit 1
fi

# Start DMS with server
export DMS_SERVER_URL="$SERVER_URL"
python main.py --video "$VIDEO" --no-display --server-url "$SERVER_URL"
```

---

## ✅ Definition of Done

### By End of Week 1 (Fri Aug 8)
- [ ] DMS sends events to server (JSON format)
- [ ] Server receives & stores events
- [ ] Dashboard WebSocket connects
- [ ] Events appear on dashboard in real-time
- [ ] Demo video generates 3-5 violations

### By End of Week 2 (Fri Aug 15)
- [ ] Full end-to-end demo works
- [ ] Can run on target device (board or laptop)
- [ ] Manual tuning done (thresholds dialed in)
- [ ] All glitches fixed
- [ ] Ready for customer demos/RFP

---

## 🎬 Demo Script (5 Minutes)

```
1. [0:00] Open dashboard: http://localhost:3000
          "Real-time violation detection dashboard"

2. [0:30] Start DMS: ./scripts/start_poc.sh
          "Processing video... detecting behaviors"

3. [1:00] Watch violations appear:
          "First drowsiness event detected... EAR dropped to 0.18"

4. [2:00] Multiple events trigger:
          "3 drowsiness events in 2 minutes = violation"
          "Phone detected = immediate alert"

5. [3:00] Show dashboard metrics:
          "Here are all violations in real-time"
          "Safety trends in the chart"

6. [4:00] Click event detail:
          "Full metrics: eye aspect ratio, duration, timestamp"

7. [5:00] Summary:
          "This is AI-powered driver monitoring on edge devices"
          "Detects safety risks in real-time with minimal latency"
          "Ready to integrate with fleet management systems"
```

---

## 🎯 Success Metrics

- ✅ Dashboard shows events in < 1 second
- ✅ Demo video generates expected violations (manual tuned)
- ✅ No crashes during 5-minute demo
- ✅ Server handles 100 events/min without data loss
- ✅ Works offline (events logged locally if server down)

---

## 📌 Key Files to Create/Modify

| File | Owner | Status |
|------|-------|--------|
| `dms.py` | AI Eng | Add event emission |
| `src/server/app.py` | You | Create FastAPI |
| `web/src/Dashboard.jsx` | UI Guy | Create React UI |
| `scripts/start_poc.sh` | Edge Expert | Create startup script |
| `docker-compose.yml` | You | Optional, for easy deploy |

---

## 🚀 That's It!

**Total lines of new code**: ~500 (very manageable)  
**Time to demo-ready**: 2 weeks with 4 people  
**Cost**: $0 (no infrastructure)  
**Complexity**: Low (mostly integration, not invention)

Good luck! 🎉

---

**Document Version**: 1.0  
**Status**: Ready for Team Kickoff
