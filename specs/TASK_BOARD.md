# Task Board — 2 Week POC Sprint
**Presentable to Team | Quick & Dirty | Demo-Focused**

---

## 🎯 Project at a Glance

**Goal**: Real-time driver monitoring dashboard for AI capability showcase  
**Timeline**: 2 weeks (Aug 1-14)  
**Team**: 4 people  
**Status**: Ready to start

---

## 👥 Team Breakdown

| Person | Role | Tasks |
|--------|------|-------|
| **AI Engineer** | Edge Detection | Emit violation events from DMS |
| **Edge Expert** | Hardware/Network | Device setup + event transmission |
| **UI Guy** | Frontend | Real-time dashboard + charts |
| **You** | Server/Architecture | FastAPI backend + event hub |

---

## 📋 TASKS BY OWNER

---

## **AI ENGINEER: Event Detection (3 Days)**

### Task 1: Event Format Definition
```
[ ] Create JSON event structure in dms.py
    {
      "type": "DROWSINESS",
      "severity": "CRITICAL",
      "timestamp": 1722638401.23,
      "metrics": {"ear": 0.18, "duration": 0.75},
      "trip_stats": {...}
    }

[ ] Remove TTS stub (skip audio)
[ ] Keep JSONL logging for debugging
```
**Acceptance**: Events print as valid JSON, no errors  
**Time**: 1 day

---

### Task 2: Event Transmission to Server
```
[ ] Add requests library import
[ ] After each violation:
    requests.post(
      f"http://server:8000/events",
      json=event_data,
      timeout=1
    )

[ ] Handle network errors (don't crash DMS)
[ ] Test with server running on localhost:8000
```
**Acceptance**: Events reach server, visible in logs  
**Time**: 1 day

---

### Task 3: Demo Tuning
```
[ ] Run drowsy_drive.mp4 video
[ ] Count drowsiness events (check logs)
[ ] Adjust EAR_THRESHOLD in config.py
[ ] Adjust EAR_CONSEC_SECS for timing
[ ] Goal: 3-5 drowsiness events in 2-min clip
[ ] Test phone detection (if in video)
[ ] Test distraction (head turning)
```
**Acceptance**: Demo video triggers expected violations  
**Time**: 1 day

---

## **EDGE EXPERT: Device Setup & Network (2 Days)**

### Task 1: Environment Verification
```
[ ] Verify Python 3.8+ installed
[ ] pip install opencv-python mediapipe onnxruntime requests
[ ] Download drowsy_drive.mp4 (or create test video)
[ ] Run: python main.py --video videos/drowsy_drive.mp4
[ ] Measure baseline FPS (should be 10-30 FPS)
[ ] Note: target device IP address (e.g., 192.168.1.10)
```
**Acceptance**: DMS runs, FPS acceptable, video plays  
**Time**: 1 day

---

### Task 2: Network Integration Script
```
[ ] Create scripts/start_poc.sh:

    #!/bin/bash
    SERVER_URL=${1:-"http://localhost:8000"}
    VIDEO=${2:-"videos/drowsy_drive.mp4"}
    
    python main.py --video "$VIDEO" --server-url "$SERVER_URL" --no-display

[ ] Make executable: chmod +x scripts/start_poc.sh
[ ] Test with server running:
    ./scripts/start_poc.sh http://localhost:8000
    
[ ] Verify: DMS connects to server before starting
[ ] Fallback: if server unreachable, runs locally (log events only)
```
**Acceptance**: Script starts DMS, connects to server  
**Time**: 1 day

---

## **UI GUY: Dashboard (4 Days)**

### Task 1: React App Skeleton (Day 1)
```
[ ] npx create-react-app web
[ ] Create src/Dashboard.jsx
[ ] Layout:
    - Header: "DMS Real-Time Dashboard"
    - Stats panel: 3 cards (Drowsiness, Phone, Distraction)
    - Event log: scrollable list
    - Chart area: placeholder

[ ] Install Recharts: npm install recharts
[ ] Test: npm start → loads at localhost:3000
```
**Acceptance**: App loads, no console errors  
**Time**: 1 day

---

### Task 2: WebSocket + Real-Time Updates (Day 2)
```
[ ] Connect to WebSocket:
    const ws = new WebSocket('ws://localhost:8000/events/stream');
    
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents([event, ...events.slice(0, 100)]);
    };

[ ] Display events in list:
    - Type (badge with color)
    - Timestamp
    - Metrics (EAR, duration)
    
[ ] Update counters in real-time:
    drowsiness_count, phone_count, distraction_count
    
[ ] Scroll event list to show newest first
```
**Acceptance**: Events appear as they come in, counters update  
**Time**: 1.5 days

---

### Task 3: Charts + Interactivity (Day 3-4)
```
[ ] Add Recharts LineChart:
    X-axis: Time (rolling 5 min window)
    Y-axis: Violation count
    
[ ] Click event → show detail modal:
    Full event JSON (metrics, timestamp, etc.)
    
[ ] Add "Clear" button to reset counters
    
[ ] Polish:
    - Responsive design (mobile-friendly)
    - Color scheme (red for CRITICAL, orange for others)
    - Smooth animations
```
**Acceptance**: Charts update, modals work, responsive  
**Time**: 1.5 days

---

## **YOU (SERVER): FastAPI Backend (3 Days)**

### Task 1: Basic Endpoints (Day 1)
```
[ ] Create src/server/app.py with FastAPI
[ ] POST /events
    - Accept JSON event from edge
    - Store in list (in-memory)
    - Save to logs/events.jsonl
    - Return: {"status": "received"}
    
[ ] GET /violations/summary
    - Count events by type
    - Return: {"DROWSINESS": 3, "PHONE_USAGE": 1, ...}
    
[ ] Enable CORS (for localhost:3000)
    
[ ] Test endpoints:
    curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d '{"type":"TEST"}'
    curl http://localhost:8000/violations/summary
```
**Acceptance**: Endpoints respond with correct JSON  
**Time**: 1 day

---

### Task 2: WebSocket Streaming (Day 2)
```
[ ] GET /events/stream (WebSocket endpoint)
    - Client connects → accept connection
    - Send last 100 events
    - Keep connection open
    - Broadcast new events to all clients
    - Handle client disconnect
    
[ ] Modify POST /events to broadcast:
    for client in connected_clients:
        send(client, event)
        
[ ] Test with UI:
    - Start server
    - Open dashboard
    - Verify events stream in real-time
    - Open dashboard in 2nd browser
    - Both should receive same events
```
**Acceptance**: Multiple UIs receive events in real-time  
**Time**: 1 day

---

### Task 3: Demo Mode + Polish (Day 3)
```
[ ] Add --demo flag:
    python src/server/app.py --demo
    
[ ] Demo mode sends fake events every 5 sec:
    random type: DROWSINESS, PHONE_USAGE, DISTRACTION
    timestamp: current time
    metrics: random values
    
[ ] Verify end-to-end:
    1. Start server (normal mode)
    2. Start DMS → events flow
    3. Open dashboard → see events
    4. NO data loss, NO crashes
    
[ ] Document: create README.md with:
    - How to run server locally
    - How to run on target device
    - Environment variables
    - API endpoints summary
```
**Acceptance**: Demo mode works, end-to-end verified  
**Time**: 1 day

---

## 📅 Weekly Timeline

### **WEEK 1: Foundation + Integration**

| Day | AI Engineer | Edge Expert | UI Guy | You (Server) |
|-----|------------|-------------|--------|--------------|
| **Mon** | Event format | Environment setup | App skeleton | FastAPI endpoints |
| **Tue** | Event transmission | Network script | WebSocket | WebSocket streaming |
| **Wed** | Demo tuning | Network testing | Charts setup | Demo mode |
| **Thu** | Fine-tune thresholds | Verify flow | UI polish | End-to-end test |
| **Fri** | Final tuning | Edge-to-server test | Final polish | All systems go |

### **WEEK 2: Demo Ready**

| Day | All Team |
|-----|----------|
| **Mon** | Full system test on target device |
| **Tue-Wed** | Customer demos / RFP showcase |
| **Thu** | Bug fixes + feedback |
| **Fri** | Wrap-up + next steps |

---

## 🎯 Daily Standup Template (15 min, 9:00 AM)

**Questions each person answers**:

1. **Yesterday**: What did you complete?
2. **Today**: What will you do?
3. **Blockers**: Anything blocking you?

**Example**:
```
AI Engineer:
  Yesterday: Finished event format, started transmission
  Today: Complete transmission + start demo tuning
  Blockers: None

Edge Expert:
  Yesterday: Environment setup complete, server IP = 192.168.1.10
  Today: Create start_poc.sh script
  Blockers: Waiting on server endpoint from You

UI Guy:
  Yesterday: React app skeleton, working on WebSocket
  Today: Finish WebSocket + start charts
  Blockers: Need server on port 8000 running for testing

You:
  Yesterday: POST /events and GET /summary endpoints done
  Today: Implement WebSocket /events/stream
  Blockers: Need clarification on event schema from AI Eng
```

---

## ✅ Checklist: Definition of Done

### **End of Week 1 (Friday Aug 8)**
- [ ] AI Eng: DMS emits events in JSON format
- [ ] Edge Exp: Device setup complete, start script working
- [ ] UI Guy: Dashboard loads, WebSocket connects
- [ ] You: Server receives events, broadcasts to UI
- [ ] Team: Events flow end-to-end (no errors)

### **End of Week 2 (Friday Aug 15)**
- [ ] Demo works on target device (board or laptop)
- [ ] Thresholds tuned (drowsy video generates 3-5 violations)
- [ ] Dashboard shows real-time updates
- [ ] No crashes during 5-minute demo run
- [ ] All team members can run demo independently
- [ ] Ready for customer demos / RFP presentation

---

## 📊 Risk Matrix (Low Risk!)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Server down → DMS crashes | Low | High | Handle network errors in DMS |
| Dashboard doesn't update | Low | Medium | Test WebSocket early (Day 1) |
| Video doesn't have expected violations | Medium | Low | Manually tune thresholds (Day 3) |
| Device network connectivity | Low | Medium | Test on target device early (Day 1) |

---

## 💡 Tips for Success

### **AI Engineer**
- Test event transmission early (Day 1 end, not Day 3)
- Use `timeout=0.5` so DMS doesn't wait for server
- Print events to console while debugging

### **Edge Expert**
- Verify network connectivity BEFORE full integration
- Use `curl` to test server endpoints manually
- Document the device IP clearly

### **UI Guy**
- Start with console.log to verify data flow
- Test WebSocket with server running
- Use browser DevTools → Network tab to debug

### **You (Server)**
- Start simple (POST/GET before WebSocket)
- Test with `curl` from command line
- Add print statements for debugging
- Use `--demo` flag for testing without DMS

---

## 🎬 Demo Script (Memorize This)

**Duration**: 5 minutes | **Audience**: Customers / RFP reviewers

```
1. INTRO (0-30s)
   "This is a real-time driver monitoring system using AI.
    We detect safety risks: drowsiness, phone usage, distraction."

2. SETUP (30s-1m)
   [Open dashboard at http://localhost:3000]
   "Real-time dashboard showing violations as they happen."

3. START DETECTION (1m-1:30s)
   [Run: ./scripts/start_poc.sh]
   "System is now processing video and detecting behaviors."

4. WATCH VIOLATIONS (1:30m-3:00m)
   [Let video play, violations appear on dashboard]
   "First drowsiness event... eyes closed for 0.73 seconds
    Second event... 0.68 seconds
    Third event... now we have a violation pattern detected
    All in real-time, sub-second latency"

5. SHOW DETAILS (3:00m-4:00m)
   [Click on violation in dashboard]
   "Full metrics here: eye aspect ratio, duration, timestamp
    This data feeds into fleet management, insurance, safety training"

6. CLOSE (4:00m-5:00m)
   "This is production-ready edge AI for driver safety.
    Detects behavior in real-time, zero latency.
    Ready to integrate with your fleet management systems.
    Questions?"
```

---

## 📁 Code Structure (What You'll Create)

```
DriverMonitorPOC/
├── src/
│   ├── dms.py (MODIFY: add event emission)
│   ├── server/
│   │   └── app.py (CREATE: FastAPI backend)
│   └── config.py (MODIFY: thresholds for demo tuning)
├── web/
│   └── src/
│       └── Dashboard.jsx (CREATE: React component)
├── scripts/
│   └── start_poc.sh (CREATE: launch script)
├── videos/
│   └── drowsy_drive.mp4 (USE: test video)
├── logs/
│   └── events.jsonl (AUTO-GENERATED: event log)
└── POC_SPRINT_2WEEKS.md (THIS FILE: reference guide)
```

---

## 🚀 Ready to Start?

**Print this page and post on team wall!**

### Day 1 Actions (Monday morning):
- [ ] AI Engineer: Start event format task
- [ ] Edge Expert: Set up environment
- [ ] UI Guy: Create React app skeleton
- [ ] You: Create FastAPI endpoints
- [ ] Team: Daily standup at 9:00 AM

### First Milestone (EOD Wednesday):
- [ ] Events flow from DMS → Server → Dashboard
- [ ] No crashes, visible in logs

### Second Milestone (EOD Friday):
- [ ] Demo tuning complete
- [ ] Ready for Week 2 customer demos

---

**You've got this! 🎉**

---

**Document Version**: 1.0  
**Ready to Present**: YES  
**Printable**: YES (fits on A3 poster)
