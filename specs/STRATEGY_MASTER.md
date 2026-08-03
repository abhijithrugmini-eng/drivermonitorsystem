# DriverMonitorPOC: Master Strategy Document

**Last Updated**: August 1, 2026  
**Status**: Ready for 2-Week Sprint (POC Phase)  
**Scope**: Quick & Dirty Showcase (NOT Enterprise)

---

## 📌 Overview: What We're Building

A **real-time driver monitoring dashboard** for AI capability showcases and RFP presentations. The system detects drowsiness, phone usage, and distraction using edge AI (YOLO + MediaPipe) and streams results to a web dashboard.

**Key Constraint**: This is a **POC for internal demos**. NO production requirements. Manual tuning of thresholds is OK. Zero infrastructure cost. 4-person team. 2-week timeline (Aug 1-14).

---

## 🎯 Business Context

### What the User Needs
- Customer demos showing AI capabilities
- RFP showcases ("Here's what we can build")
- Proof that the architecture works end-to-end
- Foundation for Phase 2 (cloud integration)

### What the User Does NOT Need
- Multi-agent enterprise architecture
- InfluxDB time-series database
- Containerization for deployment
- Violation state machine lifecycle
- Production-grade error handling
- Compliance/security hardening

### User's Critical Feedback (From Session)
> "These many epics and 63 tasks are too much for poc... there are 4 people in team... so let it be quick and dirty"

**Action Taken**: Scrapped the original 63-task enterprise plan. Created a 12-task, 2-week sprint focused on MVP: Event Emission → Server → Dashboard.

---

## 🏗️ System Architecture (Simple)

```
Edge Device (Laptop/Board)
├─ Run existing DMS (YOLO + MediaPipe)
└─ Emit JSON events via REST POST

          ↓ (POST /events)

FastAPI Server (Port 8000)
├─ Receive events
├─ Store in JSON file (NO database)
└─ Stream to UI via WebSocket

          ↓ (WebSocket /events/stream)

React Dashboard (Port 3000)
└─ Real-time violation list + counters
```

**That's it.** No multi-agent complexity. No message queues. No time-series DB. Just HTTP + WebSocket.

---

## 👥 Team & Task Breakdown

### AI Engineer (3 Days)
1. **Event Format**: Create JSON event structure in dms.py
2. **Transmission**: Add `requests.post()` to send events to server
3. **Demo Tuning**: Adjust EAR_THRESHOLD & EAR_CONSEC_SECS for demo video

### Edge Expert (2 Days)
1. **Environment Setup**: Verify Python, OpenCV, MediaPipe on device
2. **Network Script**: Create `scripts/start_poc.sh` to launch DMS with server URL

### UI Guy (4 Days)
1. **React App**: Create skeleton (header, event list, counters)
2. **WebSocket**: Connect to server, listen for events in real-time
3. **Charts & Polish**: Add Recharts line chart, event detail modal

### You (Server) (3 Days)
1. **FastAPI Endpoints**: POST /events, GET /violations/summary, WebSocket /events/stream
2. **Demo Mode**: Optional fake-event endpoint for testing without DMS
3. **Testing**: Verify end-to-end, no data loss

---

## 📅 2-Week Timeline

### Week 1: Foundation & Integration
| Day | AI Engineer | Edge Expert | UI Guy | You (Server) |
|-----|------------|-------------|--------|--------------|
| **Mon** | Event format | Environment setup | App skeleton | FastAPI endpoints |
| **Tue** | Event transmission | Network script | WebSocket | WebSocket streaming |
| **Wed** | Demo tuning | Network testing | Charts setup | Demo mode |
| **Thu** | Fine-tune thresholds | Verify flow | UI polish | End-to-end test |
| **Fri** | Final tuning | Edge-to-server test | Final polish | All systems go |

### Week 2: Demo Ready
| Day | Action |
|-----|--------|
| **Mon** | Full system test on target device |
| **Tue-Wed** | Customer demos / RFP showcase |
| **Thu** | Bug fixes + feedback |
| **Fri** | Wrap-up + next steps |

---

## 💻 Code Snippets (Copy-Paste Ready)

### 1. AI Engineer: Event Emission (dms.py)

```python
import requests
import json
import time

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

### 2. Your Server: FastAPI (src/server/app.py)

```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
    # Keep connection open
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. UI Guy: React Dashboard (web/src/Dashboard.jsx)

```jsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts';

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [counts, setCounts] = useState({});
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/events/stream');
    
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents(prev => [event, ...prev.slice(0, 100)]);
      setCounts(prev => ({
        ...prev,
        [event.type]: (prev[event.type] || 0) + 1
      }));
    };
    
    return () => ws.close();
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h1>🚗 DMS Real-Time Dashboard</h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px' }}>
        <div style={{ border: '1px solid #ccc', padding: '10px' }}>
          <h3>😴 Drowsiness</h3>
          <p style={{ fontSize: '24px', color: 'red' }}>{counts.DROWSINESS || 0}</p>
        </div>
        <div style={{ border: '1px solid #ccc', padding: '10px' }}>
          <h3>📱 Phone Usage</h3>
          <p style={{ fontSize: '24px', color: 'orange' }}>{counts.PHONE_USAGE || 0}</p>
        </div>
        <div style={{ border: '1px solid #ccc', padding: '10px' }}>
          <h3>👀 Distraction</h3>
          <p style={{ fontSize: '24px', color: 'yellow' }}>{counts.DISTRACTION || 0}</p>
        </div>
      </div>

      <h2>📋 Event Log</h2>
      <div style={{ height: '300px', overflow: 'auto', border: '1px solid #ddd' }}>
        {events.map((e, i) => (
          <div key={i} style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
            <strong>{e.type}</strong> @ {new Date(e.timestamp * 1000).toLocaleTimeString()}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 4. Edge Expert: Start Script (scripts/start_poc.sh)

```bash
#!/bin/bash

SERVER_URL=${1:-"http://localhost:8000"}
VIDEO=${2:-"videos/drowsy_drive.mp4"}

echo "🚀 Starting POC..."
echo "  Server: $SERVER_URL"
echo "  Video: $VIDEO"

# Verify server is up
if ! curl -s "$SERVER_URL/violations/summary" > /dev/null; then
    echo "⚠️  Server not responding. Start it first:"
    echo "   python src/server/app.py"
    exit 1
fi

# Start DMS
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
- [ ] Can run on target device
- [ ] Manual tuning done
- [ ] Ready for customer demos/RFP

---

## 🎬 Demo Script (5 Minutes, Memorize This)

```
[00:00] Open dashboard: http://localhost:3000
        "Real-time violation detection dashboard"

[00:30] Start DMS: ./scripts/start_poc.sh
        "Processing video... detecting behaviors"

[01:00] Watch violations appear:
        "First drowsiness event detected... EAR dropped to 0.18"

[02:00] Multiple events trigger:
        "3 drowsiness events in 2 minutes = violation"

[03:00] Show dashboard metrics:
        "Full metrics here: eye aspect ratio, duration, timestamp"

[04:00] Close:
        "This is AI-powered driver monitoring on edge devices"
        "Ready to integrate with your fleet management systems"

[05:00] "Questions?"
```

---

## 🔧 Key Configuration Values (For Manual Tuning)

File: `src/config.py`

| Parameter | Current | How to Adjust |
|-----------|---------|---------------|
| `EAR_THRESHOLD` | 0.21 | Lower = more sensitive drowsiness |
| `EAR_CONSEC_SECS` | 0.7 | Lower = alert faster |
| `MAR_THRESHOLD` | 0.5 | Lower = catch lighter yawns |
| `YOLO_CONFIDENCE` | 0.45 | Increase for phones only, decrease for more detections |

**Demo Tuning Rule**: Lower thresholds = more events = more impressive demo. Tune after seeing drowsy_drive.mp4 output.

---

## 🌐 Network Setup

### Local Testing (All on Same Machine)
```bash
# Terminal 1: Start server
python src/server/app.py

# Terminal 2: Open dashboard
open http://localhost:3000

# Terminal 3: Start DMS
python main.py --video videos/drowsy_drive.mp4 --server-url http://localhost:8000
```

### On Target Device
```bash
# Get device IP
DEVICE_IP=$(ifconfig | grep inet | head -1 | awk '{print $2}')

# Terminal 1: Start server on any machine (binding to 0.0.0.0)
python src/server/app.py --host 0.0.0.0

# Terminal 2: Start DMS on device
python main.py --video videos/drowsy_drive.mp4 --server-url http://<SERVER_IP>:8000
```

---

## 🐛 Debugging Checklist

### Events not reaching server?
- [ ] Is server running? `curl http://localhost:8000/violations/summary`
- [ ] Is DMS sending? Check logs: `tail -f logs/events.jsonl`
- [ ] Network issue? `ping <server_ip>`

### Dashboard not updating?
- [ ] WebSocket connected? Open browser DevTools → Network → Filter "WS"
- [ ] Server receiving events? Check server logs

### Events in server but not in dashboard?
- [ ] Browser console errors? (Ctrl+Shift+I → Console)
- [ ] Try hard refresh: Ctrl+Shift+R
- [ ] Check WebSocket URL is correct

---

## 📊 Critical Path (What Blocks Others)

1. **AI Eng → You**: Need event schema by EOD Mon (for POST endpoint)
2. **You → UI Guy**: Need server endpoint by EOD Tue (for WebSocket connection)
3. **UI Guy + You**: Need WebSocket working by EOD Wed (for real-time updates)
4. **All**: Full integration test by EOD Thu (before demos Week 2)

**If blocked**: Escalate immediately. Don't wait for standup.

---

## 📋 Daily Standup (9:00 AM, 15 min)

**What to say:**
1. What did you finish yesterday?
2. What will you finish today?
3. Blockers?

**Example:**
```
AI:    "Finished event format. Today: transmission. No blockers."
Edge:  "Env done. Today: network script. Waiting on server IP."
UI:    "App skeleton. Today: WebSocket. Need server."
You:   "Endpoints done. Today: WebSocket. On track."
```

---

## 📂 Files to Create/Modify

| File | Owner | Action |
|------|-------|--------|
| `dms.py` | AI Eng | Modify: add event emission |
| `src/server/app.py` | You | CREATE: FastAPI server |
| `web/src/Dashboard.jsx` | UI Guy | CREATE: React UI |
| `scripts/start_poc.sh` | Edge Expert | CREATE: startup script |
| `logs/events.jsonl` | All | AUTO-GENERATED: event log |

---

## ✨ Why This Approach Works

✅ **Simple**: 3 pieces (Event → Server → Dashboard)  
✅ **Fast**: 2 weeks with 4 people  
✅ **Cheap**: $0 infrastructure, no databases  
✅ **Scalable**: Foundation for Phase 2 (cloud integration)  
✅ **Demo-Friendly**: Manual tuning OK, no production complexity  

---

## 🚀 Go/No-Go Checklist

### We're GO if:
- ✅ Team of 4 available (AI Eng, Edge Expert, UI Guy, You)
- ✅ Laptops/boards with Python + npm
- ✅ Demo video (drowsy_drive.mp4) available
- ✅ Leadership OK with 2-week deadline

### We're NO-GO if:
- ❌ Team members pulled for other projects
- ❌ Deadline flexibility < 2 weeks
- ❌ No demo video available

---

## 🎯 Success Metrics

By EOD Week 2:
- ✅ Dashboard shows events in < 1 second
- ✅ Demo video generates expected violations (3-5 for drowsy, 2-3 for phone)
- ✅ No crashes during 5-minute demo
- ✅ Works on target device (board or laptop)
- ✅ Team can run demo independently

---

## 📌 Next Steps (For Monday Kickoff)

1. **Print** TASK_BOARD.md + QUICK_REFERENCE.md
2. **Post** on team wall
3. **Read** START_HERE_POC.md (5 min)
4. **Assign** tasks per person
5. **Standup** Monday 9:00 AM
6. **Execute** your task

---

## 📚 Document Index

| Document | Purpose | Read When |
|----------|---------|-----------|
| **TASK_BOARD.md** | Task breakdown per person | Sprint kickoff |
| **QUICK_REFERENCE.md** | Daily cheat sheet | Bookmark for daily use |
| **POC_SPRINT_2WEEKS.md** | Detailed specs + code snippets | Start your task |
| **START_HERE_POC.md** | Navigation guide | First 5 minutes |
| **STRATEGY_MASTER.md** | This file: overall strategy | When you need context |

---

## ⚖️ Enterprise Alternative (What We Rejected)

The original plan (RELEASE_PLAN_AUGUST_13.md) proposed:
- 8 EPICs, 63 tasks
- Multi-agent architecture
- InfluxDB time-series database
- Containerization + Docker Compose
- Violation state machine lifecycle
- 13-day timeline with 3 engineers
- Production-grade complexity

**Why we rejected it:**
> "These many epics and 63 tasks are too much for poc... there are 4 people in team... so let it be quick and dirty"

**What we're doing instead:**
- 1 epic, 12 tasks
- Simple HTTP + WebSocket
- JSON file storage (no DB)
- Optional Docker (not required)
- Manual event handling (no state machine)
- 2 weeks with 4 people
- POC-level simplicity

**Result**: Team can execute, demo is ready by Aug 14, foundation for Phase 2.

---

## 🎓 Learning Objectives (For Phase 2)

By the end of this sprint, team will understand:
- [ ] How YOLO + MediaPipe work together for edge detection
- [ ] How to stream events from edge to server in real-time
- [ ] How to build a real-time dashboard with WebSocket
- [ ] How to handle network failures gracefully
- [ ] What thresholds matter for different detection types

This knowledge feeds into Phase 2 (cloud integration, fleet dashboard, advanced analytics).

---

## 📞 Support & Escalation

| Problem | First Try | If Stuck | Escalate To |
|---------|-----------|----------|-------------|
| **Unclear task** | Re-read task description in TASK_BOARD.md | Ask in standup | You (Server Lead) |
| **Blocker** | Check QUICK_REFERENCE.md debugging | Ask in Slack | You (can unblock) |
| **Design question** | Check POC_SPRINT_2WEEKS.md code snippets | Ask in standup | You (architectural decisions) |
| **Network issue** | Ask Edge Expert | Test with curl | Edge Expert |
| **WebSocket issue** | Ask UI Guy or You | Check browser DevTools | UI Guy + You |

---

## 🏁 Finish Line

**Friday Aug 15, EOD**: You're done.

At that point:
- ✅ Working POC (AI → Server → Dashboard)
- ✅ Customer demos ready (5 min script)
- ✅ Team feedback captured for Phase 2
- ✅ Team momentum & confidence high

---

**Version**: 1.0  
**Created**: Aug 1, 2026  
**Status**: READY FOR SPRINT  
**Confidence**: HIGH (4 people, clear scope, proven tech)

---

*This document consolidates 63 enterprise tasks into 12 POC tasks. Keep it as your north star for the next 2 weeks.*

