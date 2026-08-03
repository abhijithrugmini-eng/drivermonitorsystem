# 🎯 Complete Design Package for POC Team

**Date**: August 1, 2026  
**Purpose**: Everything the team needs to start Monday  
**Status**: Ready for presentation

---

## 📌 What's New Since Last Update

You asked for:
1. ✅ **Design decision**: Edge vs. Server violations
2. ✅ **Recommendation**: Server detects violations (faster, cleaner)
3. ✅ **Data models**: Event, Violation, Evidence, Alarm
4. ✅ **DrawIO diagram**: POC_ARCHITECTURE.drawio
5. ✅ **Flow diagrams**: Agent-wise flows (5 diagrams)
6. ✅ **Sample models**: Python dataclasses + JSON examples
7. ✅ **Alarm agent**: At server (logs, broadcasts via WebSocket)

---

## 📂 New Design Documents (4 Files)

### 1️⃣ DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md

> **Superseded — see `dms-spec/changes/move-violation-detection-to-edge/`.** The answer below was
> the right call for getting a demo running fast in week one, but it undersold the product: a
> cloud-only detector isn't the story this POC needs to tell. The revised answer is **EDGE**
> (primary), with **SERVER** kept as a fallback for vehicles with no edge device — see
> `CLAUDE.md` § "This POC's selling point" and `.claude/skills/dms-agentic-architecture/SKILL.md`.
> Left below for historical context; don't treat "Answer: SERVER" as current.

**Question**: Should violations be detected at Edge or Server?  
**Answer**: **SERVER** (recommended for POC)

**Why Server is better for POC**:
- ✅ Simpler edge code (just emit events)
- ✅ Faster implementation (3 days instead of 5)
- ✅ Easier testing (curl mock events)
- ✅ Centralized rules (change without redeploy)
- ✅ Better for demo (clean event → violation → alarm flow)

**What it contains**:
- Pros/cons of each option
- Decision matrix
- Implementation path
- Acceptance criteria

---

### 2️⃣ POC_ARCHITECTURE.drawio
**Format**: DrawIO file (open in diagrams.net or local DrawIO)  
**Contents**: Visual architecture showing:
- DMS (YOLO + MediaPipe) → Events
- Event Receiver → Violation Engine
- Violation Engine → Alarm Agent
- Alarm Agent → WebSocket → Dashboard
- Violation Rules (3 drowsy → 1 violation, etc.)
- Data Models (Event, Violation, Alarm)
- Evidence JPG storage

**How to use**:
```bash
# Option 1: Open online
https://app.diagrams.net/
File → Open → Choose POC_ARCHITECTURE.drawio

# Option 2: Send to team
Email: POC_ARCHITECTURE.drawio
They can open in browser or desktop DrawIO

# Option 3: Export as image
File → Export as PNG/SVG
Print for wall
```

---

### 3️⃣ VIOLATION_AND_EVIDENCE_MODELS.md
**Purpose**: Reference for developers  
**Contains**:

#### Event Model
```json
{
  "event_id": "evt_001",
  "timestamp": 1722638401.23,
  "type": "DROWSINESS",
  "confidence": 0.95,
  "metrics": {"ear": 0.18, "duration": 0.75},
  "trip_context": {...},
  "vehicle_context": {...}
}
```

#### Violation Model
```json
{
  "violation_id": "viol_001",
  "violation_type": "DROWSINESS_PATTERN",
  "severity": "CRITICAL",
  "evidence": {
    "event_count": 3,
    "events": [...],
    "first_frame_jpg": "data:image/jpeg;base64,..."
  },
  "alarm_action": {
    "alarm_message": "⚠️ DROWSINESS DETECTED",
    "channels": {...}
  }
}
```

#### Evidence Model
```
JPG of driver at violation moment
- Captured when violation triggered
- Base64 encoded in violation object
- Size: ~50 KB per image
- Displayed on dashboard
```

#### Alarm Model
```json
{
  "alarm_id": "alarm_001",
  "violation_id": "viol_001",
  "message": "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
  "channels": {
    "visual": true,
    "tts": false,
    "websocket": true
  }
}
```

**Features**:
- Full JSON examples
- Python dataclass examples (copy-paste ready)
- Violation rules (3 drowsy → violation, 1 phone → violation)
- Storage format (JSONL)
- End-to-end flow example
- Checklist for developers

---

### 4️⃣ AGENT_WISE_FLOW_DIAGRAMS.md
**Purpose**: Show each component's job  
**Contains 5 flow diagrams**:

1. **DMS Agent** (Edge)
   - Detect behaviors (YOLO + MediaPipe)
   - Emit events
   - POST to server
   - Log locally

2. **Event Receiver** (Server)
   - Accept POST /events
   - Validate
   - Store in memory + disk
   - Route to violation engine

3. **Violation Detection Engine** (Server)
   - Check rules (3 drowsy in 2 min, etc.)
   - Create violations
   - Capture JPG evidence
   - Route to alarm agent

4. **Alarm Agent** (Server)
   - Process violations
   - Create alarm messages
   - Log alarms
   - Broadcast via WebSocket

5. **Dashboard** (React)
   - Connect WebSocket
   - Listen for violations
   - Display cards with JPG evidence
   - Update counters
   - Color-code by severity

**Features**:
- ASCII flow diagrams (easy to read)
- Pseudocode for each component
- Integration flow (end-to-end)
- Ready to print and post

---

## 🎯 Design Summary Table

| Component | Role | Input | Output | Responsibility |
|-----------|------|-------|--------|-----------------|
| **DMS** | Detect | Video | Events | YOLO + MediaPipe |
| **Event Receiver** | Accept | Events | Validated | HTTP POST /events |
| **Violation Engine** | Aggregate | Events | Violations | Apply rules |
| **Alarm Agent** | Alert | Violations | Alarms | Log + broadcast |
| **Dashboard** | Display | Alarms | UI | Show violation cards |

---

## 📊 Violation Rules (Summary)

### Rule 1: DROWSINESS_PATTERN
```
Condition: 3+ DROWSINESS events in 2 minutes
Severity: CRITICAL
Evidence: Array of 3 events + JPG
Action: RED banner with alarm message
```

### Rule 2: PHONE_USAGE
```
Condition: 1+ PHONE_USAGE event (confidence > 0.85)
Severity: HIGH
Evidence: Single event + JPG
Action: ORANGE banner
```

### Rule 3: DISTRACTION_PATTERN
```
Condition: 2+ DISTRACTION events in 1 minute
Severity: MEDIUM
Evidence: Array of 2 events + JPG
Action: YELLOW banner
```

### Rule 4: CONTINUOUS_DRIVE (Optional)
```
Condition: Driving > 4 hours without break
Severity: LOW
Evidence: Trip duration + timestamp
Action: BLUE banner
```

---

## 🔄 Data Flow Visualization

```
┌─────────────────────────────────────────────────┐
│  EDGE (DMS)                                     │
│  ┌─────────┐                                    │
│  │ YOLO +  │────→ Detect Behaviors             │
│  │MediaPipe│                                    │
│  └─────────┘                                    │
│      │                                          │
│      └─→ {event_id, type, ear, ...}            │
│            POST /events                         │
└─────────┬──────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│  SERVER (FastAPI)                               │
│  ┌──────────────┐                              │
│  │Event Receiver│────→ Validate, Store        │
│  └──────────────┘     events.jsonl             │
│      │                                          │
│      └─→ Violation Detection Engine            │
│         ┌────────────────────┐                 │
│         │ Rule: 3 in 2 min?  │────→ YES        │
│         │ Rule: Phone?       │                 │
│         │ Rule: 2 in 1 min?  │                 │
│         └────────────────────┘                 │
│      │                                          │
│      └─→ {violation_id, type, evidence, ...}  │
│         + first_frame.jpg (base64)             │
│            │                                    │
│            └─→ Alarm Agent                     │
│               ┌──────────────┐                 │
│               │Log + Broadcast                 │
│               └──────────────┘                 │
│                  │                              │
│                  └─→ WebSocket broadcast       │
└─────────┬──────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│  DASHBOARD (React)                              │
│  ┌──────────────┐                              │
│  │WebSocket     │────→ Receive Violation       │
│  │Listener      │     Update State             │
│  └──────────────┘     Re-render                │
│      │                                          │
│      └─→ Show:                                  │
│         ✅ Violation card (RED/ORANGE/YELLOW) │
│         ✅ JPG evidence                        │
│         ✅ Alarm message                       │
│         ✅ Event count                         │
│         ✅ Timestamp                           │
└─────────────────────────────────────────────────┘
```

---

## 📋 Monday Kickoff Agenda (30 min)

### 8:30 AM (Pre-standup: 5 min)
- Everyone reads START_HERE_POC.md

### 8:35 AM (Design walkthrough: 10 min)
1. Show POC_ARCHITECTURE.drawio
2. Walk through: Event → Violation → Alarm → Dashboard
3. Point out: JPG evidence in violation card
4. Point out: Alarm agent at server (not edge)

### 8:45 AM (Model review: 10 min)
1. Show VIOLATION_AND_EVIDENCE_MODELS.md
2. Point out: Event JSON structure
3. Point out: Violation JSON structure
4. Point out: JPG as base64 in violation
5. Point out: Python dataclasses (copy-paste ready)

### 8:55 AM (Task assignment: 5 min)
- AI Eng: Use Event model + dataclass from VIOLATION_AND_EVIDENCE_MODELS.md
- You (Server): Use Violation model + Alarm model
- UI Guy: Use Dashboard pseudocode from AGENT_WISE_FLOW_DIAGRAMS.md

### 9:00 AM (Daily standup: 15 min)
- Confirm everyone has documents
- Answer questions
- Start work

---

## 🚀 What Each Developer Should Read

### AI Engineer
1. **QUICK_REFERENCE.md** § Config Values
2. **VIOLATION_AND_EVIDENCE_MODELS.md** § Event Model
3. **AGENT_WISE_FLOW_DIAGRAMS.md** § DMS Agent

**Key Takeaway**: Emit events with Event dataclass. POST to server. Include EAR, duration, confidence.

### Edge Expert
1. **QUICK_REFERENCE.md** § Network Setup
2. **AGENT_WISE_FLOW_DIAGRAMS.md** § DMS Agent
3. **DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md** § Architecture

**Key Takeaway**: Set up environment. Verify network. DMS will send events via HTTP.

### UI Guy
1. **QUICK_REFERENCE.md** § Command Cheatsheet
2. **AGENT_WISE_FLOW_DIAGRAMS.md** § Dashboard
3. **VIOLATION_AND_EVIDENCE_MODELS.md** § Violation Model

**Key Takeaway**: Connect to `/violations/stream`. Display violation cards with JPG. Show counters.

### You (Server)
1. **DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md** (full)
2. **VIOLATION_AND_EVIDENCE_MODELS.md** (full)
3. **AGENT_WISE_FLOW_DIAGRAMS.md** (all 5 diagrams)
4. **POC_ARCHITECTURE.drawio** (visual)

**Key Takeaway**: Build Event Receiver + Violation Engine + Alarm Agent. Server orchestrates violation detection.

---

## 📧 Email to Send Team Monday Morning

```
Subject: POC Sprint Kickoff - 9:00 AM Monday

Team,

We're ready to start the 2-week Driver Monitoring POC sprint!

PRINT & POST:
- TASK_BOARD.md (tasks per person)
- QUICK_REFERENCE.md (daily cheat sheet)

READ BEFORE 9:00 AM STANDUP:
- START_HERE_POC.md (5 min)
- DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md (10 min)
  → We're using SERVER to detect violations (faster, cleaner)

YOUR ROLE-SPECIFIC DOCUMENTS:
- AI Engineer: Read AGENT_WISE_FLOW_DIAGRAMS.md § DMS Agent
- Edge Expert: Read QUICK_REFERENCE.md § Network Setup
- UI Guy: Read AGENT_WISE_FLOW_DIAGRAMS.md § Dashboard
- You (Server): Read all of VIOLATION_AND_EVIDENCE_MODELS.md

VISUAL REFERENCE:
- Open POC_ARCHITECTURE.drawio (shows full flow)
- Open AGENT_WISE_FLOW_DIAGRAMS.md (shows per-component responsibilities)

SAMPLE CODE:
- Python dataclasses in VIOLATION_AND_EVIDENCE_MODELS.md
- Pseudocode in AGENT_WISE_FLOW_DIAGRAMS.md

QUESTIONS BEFORE KICKOFF:
- Slack: #poc-sprint
- Or ask in standup

See you Monday 9:00 AM!
```

---

## ✅ Pre-Kickoff Checklist (Sunday Night)

- [ ] Read DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md
- [ ] Print TASK_BOARD.md (2 pages) × 4
- [ ] Print QUICK_REFERENCE.md (2 pages) × 4
- [ ] Post TASK_BOARD.md on wall
- [ ] Open POC_ARCHITECTURE.drawio (test it opens)
- [ ] Email 6 documents to team (see list below)
- [ ] Confirm video files exist (drowsy_drive.mp4)
- [ ] Confirm Python + npm installed

**6 Documents to Email Team**:
1. START_HERE_POC.md
2. TASK_BOARD.md
3. QUICK_REFERENCE.md
4. DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md
5. VIOLATION_AND_EVIDENCE_MODELS.md
6. AGENT_WISE_FLOW_DIAGRAMS.md

(Plus: POC_ARCHITECTURE.drawio as attachment)

---

## 🎯 Success Criteria for Design

By EOD Day 1 (Monday):
- ✅ Team understands: Events → Server → Violations → Dashboard
- ✅ Team understands: Alarm agent at server (not edge)
- ✅ AI Eng knows Event model
- ✅ You (Server) knows Violation + Alarm models
- ✅ UI Guy knows how to display violations with JPG

By EOD Day 2 (Tuesday):
- ✅ AI Eng emits events with Event dataclass
- ✅ Server receives and validates events
- ✅ Violation detection engine is triggered

By EOD Day 3 (Wednesday):
- ✅ First violation created with JPG evidence
- ✅ Alarm agent broadcasts violation via WebSocket
- ✅ Dashboard displays violation card with JPG

---

## 🔗 File Cross-References

**If you need...**        | **Read this**
--------------------------|----------------------------------
Complete architecture      | POC_ARCHITECTURE.drawio
Design decision            | DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md
Data models              | VIOLATION_AND_EVIDENCE_MODELS.md
Flow diagrams           | AGENT_WISE_FLOW_DIAGRAMS.md
Daily tasks            | TASK_BOARD.md
Quick commands         | QUICK_REFERENCE.md
Code snippets          | POC_SPRINT_2WEEKS.md
Alarm agent logic      | AGENT_WISE_FLOW_DIAGRAMS.md § Alarm Agent
JPG evidence capture   | VIOLATION_AND_EVIDENCE_MODELS.md § Evidence Model

---

## 📌 TL;DR

**The Design in 3 Sentences**:

1. **DMS (edge) emits Events** when it detects drowsiness, phone, etc. → POST to server
2. **Server (FastAPI) receives Events**, checks violation rules (3 drowsy in 2 min = violation), and creates Violations with JPG evidence → broadcasts via WebSocket
3. **Dashboard (React) displays Violations** with JPG, alarm message, event count → user sees what triggered the alert

**The Diagram**: Open POC_ARCHITECTURE.drawio

**The Code**: Copy dataclasses from VIOLATION_AND_EVIDENCE_MODELS.md

---

**Status**: ✅ Ready for Monday Kickoff  
**Next Action**: Present POC_ARCHITECTURE.drawio + VIOLATION_AND_EVIDENCE_MODELS.md to team  
**Timeline**: 2 weeks (Aug 1-14)  
**Confidence**: HIGH (clear design, simple flow, proven tech)

---

*Everything is ready. Print the documents. Send the email. Run the standup. Execute.*

