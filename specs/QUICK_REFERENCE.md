# Quick Reference Cheat Sheet — 2 Week POC

**Print this. Post on desk. Use daily.**

---

## 🎯 The Goal in One Sentence
**Demo real-time AI driver monitoring with a dashboard in 2 weeks with 4 people.**

---

## 👥 Who Does What

| Person | Task | Daily Time |
|--------|------|-----------|
| **AI Engineer** | DMS → emit JSON events | 3 days |
| **Edge Expert** | Device + network scripts | 2 days |
| **UI Guy** | React dashboard + charts | 4 days |
| **You** | FastAPI server + WebSocket | 3 days |

---

## 🏗️ The Architecture (Draw This on Whiteboard)

```
DMS (Laptop/Board)
    ↓ POST /events (JSON)
FastAPI Server (8000)
    ↓ WebSocket /events/stream
React Dashboard (3000)
    ↓
Customer sees: Real-time violations
```

**That's it. Everything else is details.**

---

## 📋 Tasks by Priority

### **MUST HAVE (Week 1)**
1. ✅ DMS sends JSON to server (AI Eng)
2. ✅ Server receives + broadcasts (You)
3. ✅ Dashboard shows events (UI Guy)
4. ✅ Events flow end-to-end (Everyone)

### **NICE TO HAVE (Week 2)**
1. Charts
2. Event detail modal
3. Demo tuning
4. Polish UI

---

## 🔧 Key Config Values (Manual Tuning for Demo)

**File**: `src/config.py`

| Parameter | Current | For Demo |
|-----------|---------|----------|
| `EAR_THRESHOLD` | 0.21 | **Adjust ±0.02 if drowsiness misses** |
| `EAR_CONSEC_SECS` | 0.7 | **Adjust ±0.2 for faster/slower alerts** |
| `YOLO_CONFIDENCE` | 0.45 | **Increase to 0.6 for phone detection** |

**Rule of thumb**: Lower threshold = more sensitive = more events (good for demo).

---

## 🌐 Network Setup

### **Local Testing** (all on same machine)
```bash
# Terminal 1: Start server
python src/server/app.py

# Terminal 2: Open dashboard
open http://localhost:3000

# Terminal 3: Start DMS
python main.py --video videos/drowsy_drive.mp4 --server-url http://localhost:8000
```

### **On Target Device** (board/laptop)
```bash
# Get device IP: ifconfig | grep inet
DEVICE_IP=192.168.1.10

# Terminal 1: Start server on any machine
python src/server/app.py --host 0.0.0.0

# Terminal 2: Start DMS on device
python main.py --video videos/drowsy_drive.mp4 --server-url http://<SERVER_IP>:8000
```

---

## 🐛 Debugging Checklist

### **Events not reaching server?**
- [ ] Is server running? `curl http://localhost:8000/violations/summary`
- [ ] Is DMS sending? Check logs: `tail -f logs/events.jsonl`
- [ ] Network? `ping <server_ip>`

### **Dashboard not updating?**
- [ ] WebSocket connected? Open browser DevTools → Network → Filter "WS"
- [ ] Server receiving events? Check server logs

### **Events in server but not in dashboard?**
- [ ] Browser console errors? (Ctrl+Shift+I → Console)
- [ ] Try hard refresh: Ctrl+Shift+R
- [ ] Check WebSocket URL is correct

---

## 📝 Command Cheatsheet

### **AI Engineer**
```bash
# Test DMS + see events
python main.py --video videos/drowsy_drive.mp4 --no-display

# View event log
tail -f logs/events.jsonl

# Count events
grep "DROWSINESS" logs/events.jsonl | wc -l
```

### **Edge Expert**
```bash
# Check Python deps
python -c "import cv2, mediapipe, onnxruntime; print('OK')"

# Test network
curl http://localhost:8000/violations/summary

# Get device IP
ifconfig | grep inet
```

### **UI Guy**
```bash
# Start React dev server
cd web && npm start

# Check for errors
npm run build  # will show type errors

# Install dependency
npm install recharts
```

### **You (Server)**
```bash
# Run server
python src/server/app.py

# Run in demo mode (fake events)
DEMO_MODE=1 python src/server/app.py

# Test endpoints
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"type":"TEST","severity":"LOW"}'
```

---

## ✅ Daily Checklist (Do This Each Morning)

- [ ] Standup: 9:00 AM (15 min)
  - What did you do yesterday?
  - What will you do today?
  - Any blockers?
  
- [ ] Run integration test:
  ```bash
  # Terminal 1: server
  python src/server/app.py
  
  # Terminal 2: DMS
  python main.py --video videos/drowsy_drive.mp4
  
  # Terminal 3: UI
  open http://localhost:3000
  
  # Check: Do you see events on dashboard?
  ```

- [ ] Update task status in TASK_BOARD.md

---

## 🎬 Demo Walkthrough (5 minutes)

**Practice this until you can do it blind.**

```
[00:00] Open dashboard (localhost:3000)
        "Here's our AI driver monitoring dashboard"

[00:30] Start DMS
        "./scripts/start_poc.sh"
        "Processing video... AI detecting behaviors"

[01:00] Watch first event appear
        "First drowsiness detected. Eyes closed 0.75 seconds"

[02:00] Watch pattern emerge
        "3rd event... now we have a violation pattern"

[03:00] Click event detail
        "Full metrics here: EAR 0.18, timestamp, GPS location"

[04:00] Show stats
        "3 drowsiness events in 2 minutes"
        "System detected safety risk in real-time"

[04:30] Close
        "This is AI that matters. Saves lives."

[05:00] "Questions?"
```

---

## 🚨 Critical Path (What Blocks Others)

1. **AI Eng → You**: Need event schema by EOD Mon
2. **You → UI Guy**: Need server endpoint by EOD Tue
3. **UI Guy + You**: Need WebSocket working by EOD Wed
4. **All**: Full integration test by EOD Thu

**If blocked**: Escalate immediately (don't wait for standup).

---

## 📞 Help

| Problem | Fix |
|---------|-----|
| "Port 8000 already in use" | `lsof -i :8000` then `kill -9 <PID>` |
| "MediaPipe not found" | `pip install mediapipe` |
| "WebSocket connection refused" | Check server is running: `curl http://localhost:8000/violations/summary` |
| "Dashboard blank" | Open DevTools (F12) → Console → look for errors |
| "DMS crashes" | Check `src/config.py` — EAR_THRESHOLD might be too aggressive |

---

## 🎯 Success Metrics (Write These Down)

By EOD Week 1:
- [ ] Events reach server in < 1 sec
- [ ] Dashboard updates in real-time
- [ ] No crashes during 5-minute demo

By EOD Week 2:
- [ ] Demo works on target device
- [ ] Customer can see it and say "Wow"
- [ ] All glitches fixed

---

## 🏁 Finish Line

**Friday Aug 15, EOD**: You're done.

At that point:
- Team has seen 5+ customer demos
- Feedback captured for Phase 2
- Everyone understands what worked

---

**Print This. Use Daily. Win.**

**v1.0 | Aug 1, 2026**
