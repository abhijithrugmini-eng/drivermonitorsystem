# Phase 2 Development Plan: Agent-Based Architecture & Containerization

**Date**: August 1, 2026  
**Status**: Planning & Approval Phase  
**Scope**: Convert POC to distributed agent-based system with containerization  
**Timeline**: Week of Aug 5 onwards

> **Superseded in part — see `dms-spec/changes/move-violation-detection-to-edge/`.** This doc's
> laptop-first, zero-AWS, SQLite backend decision (§ 5 "Backend Architecture") still stands. What's
> changed: the **Violation Detection Agent (VDA)** described in § 2 below moves from `dms-backend`
> to `dms-edge` as the primary, demoed path — local AI analytics running on the vehicle is this
> POC's selling point (`CLAUDE.md` § "This POC's selling point"). `dms-backend` keeps this same VDA
> as a fallback for vehicles with no edge device, and its longer-term direction becomes a Phase 3
> LLM-based analytics agent, not real-time detection. The rule engine described below (thresholds,
> rules, evidence capture) is unchanged in substance — only *where it runs by default* changed. See
> `.claude/skills/dms-edge-dev/SKILL.md` and `.claude/skills/dms-backend-dev/SKILL.md` for the
> current, authoritative split.

---

## 📋 Overview

This document outlines the transition from the Phase 1 POC (centralized server-side violation detection) to Phase 2 (distributed agent-based architecture with containerization for board and laptop deployment).

**Key Shift**: Event-driven agents replacing monolithic services, enabling scalable, deployable edge stack.

---

## 🎯 Phase 2 Objectives

1. ✅ Convert existing monolithic application into discrete, composable agents
2. ✅ Implement Violation Detection Agent with distributed rules engine
3. ✅ Containerize all agents for board and laptop deployment
4. ✅ Refine UI for alarm display simulation
5. ✅ Develop laptop-first backend (zero AWS dependencies)
6. ✅ Create single-click demo deployment script
7. ✅ Establish container registry and deployment workflow

---

## 📦 Component Breakdown

### 1. Agent Conversion (Reference Architecture)

**Status**: Design complete (see linked architecture documents)

**Current Components → Future Agents**:

| Current | Becomes Agent | Responsibility |
|---------|---------------|-----------------|
| DMS (YOLO + MediaPipe) | **DMS Agent** | Frame capture, detection, event emission |
| Event Receiver | **Event Ingestion Agent** | HTTP POST /events, validation, persistence |
| Violation Detection Engine | **Violation Detection Agent** | Rule evaluation, violation creation, evidence capture |
| Alarm Agent | **Alarm & Notification Agent** | Violation processing, message creation, broadcast |
| Dashboard | **Dashboard Agent** | WebSocket subscription, real-time visualization |

**Key Documents**:
- Architecture Reference: [POC_ARCHITECTURE.drawio](POC_ARCHITECTURE.drawio) (Pages 2-3)
- Flow Diagrams: [AGENT_WISE_FLOW_DIAGRAMS.md](AGENT_WISE_FLOW_DIAGRAMS.md)
- Data Models: [VIOLATION_AND_EVIDENCE_MODELS.md](VIOLATION_AND_EVIDENCE_MODELS.md)

---

### 2. Violation Detection Agent (VDA)

**Scope**: Centerpiece of Phase 2

**Architecture**:
- Receives events from DMS Agent
- Maintains sliding window event history
- Evaluates 4 violation rules in parallel
- Creates violations with evidence (JPG)
- Emits violations to Alarm Agent

**Interfaces**:
- **Input**: Event stream (from DMS Agent)
- **Output**: Violation stream (to Alarm Agent)
- **Storage**: violations.jsonl, event history

**Rules Engine**:
```
Rule 1: DROWSINESS_PATTERN
  └─ Trigger: 3+ DROWSINESS in 2 min
  └─ Severity: CRITICAL

Rule 2: PHONE_USAGE
  └─ Trigger: 1+ high-confidence phone detection
  └─ Severity: HIGH

Rule 3: DISTRACTION_PATTERN
  └─ Trigger: 2+ DISTRACTION in 1 min
  └─ Severity: MEDIUM

Rule 4: CONTINUOUS_DRIVE
  └─ Trigger: Drive duration > 4 hours
  └─ Severity: LOW
```

**Key Features**:
- ✅ Stateful (maintains event history window)
- ✅ Real-time rule evaluation
- ✅ JPG evidence capture at violation moment
- ✅ Severity scoring
- ✅ Configurable thresholds (per rule)

---

### 3. Containerization Strategy

> **Note (Phase 1, implemented today)**: the 5-agent container breakdown below is the aspirational
> Phase 2 architecture and has not been built. What actually exists today is the simpler Phase 1
> split — `dms-backend` (one FastAPI service, not yet split into ingestion/violation-detection/alarm
> agents) and `dms-ui` — and **that** already has an optional Docker path: a `Dockerfile` in each of
> `dms-backend/` and `dms-ui/`, plus a root `docker-compose.yml` that builds and runs both (backend
> on `:8000`, UI via nginx on `:5173`). No registry, no board deployment, no single-click
> download-and-verify script — just `docker compose up` on a laptop with Docker Desktop, as a
> drop-in alternative to the local venv/`npm run dev` workflow. See `dms-backend-dev` and
> `dms-ui-dev` skills § "Optional: Docker", and the root `README.md`. Everything below this note is
> still Phase 2 scope (not started).

**Container Registry**: Google Container Registry (GCR) or Docker Hub

**Container Grouping**: `dms` (Driver Safety Monitoring)

**Containers**:

```
dms/
├── dms-dms-agent:latest
│   └─ YOLO + MediaPipe + event emission
├── dms-event-ingestion-agent:latest
│   └─ HTTP endpoint + validation
├── dms-violation-detection-agent:latest
│   └─ Rule engine + violation creation
├── dms-alarm-agent:latest
│   └─ Message creation + broadcast
└── dms-dashboard:latest
    └─ React UI + WebSocket client
```

**Deployment Options**:

#### Option A: Board Deployment
```bash
# Pull and run agents on Renesas board
docker pull gcr.io/your-project/dms-dms-agent:latest
docker run --network=host dms-dms-agent:latest
```

#### Option B: Laptop Deployment (Standalone)
```bash
# Single Docker Compose stack on laptop
docker-compose -f dms-stack.yml up
# (Contains all 5 agents in one docker-compose.yml)
```

---

### 4. UI Refinements

**Current State**: Basic violation card display

**Phase 2 Refinements**:

1. **Digital Alarm Display Simulation**
   - Simulate on-device alarm (visual indicator)
   - Show alert message with visual effects
   - Map violation severity to alarm intensity
   - Optional: LED simulator (for board demo)

2. **Agent Status Panel**
   - Show which agents are running
   - Health indicators per agent
   - Event/violation throughput metrics

3. **Playback & Replay**
   - Replay demo video with live violation detection
   - Pause/resume/scrub timeline
   - Export violation timeline as report

---

### 5. Backend Architecture (Laptop-First)

**Principle**: Zero AWS dependencies, local-first deployment

**Stack**:
- **API Framework**: FastAPI (lightweight, async-ready)
- **Storage**: 
  - Events: `events.jsonl` (local file)
  - Violations: `violations.jsonl` (local file)
  - Alarms: `alarms.jsonl` (local file)
- **Database**: None for POC (JSONL sufficient)
- **Message Queue**: In-process (no external queue)
- **WebSocket**: FastAPI WebSocket (built-in)

**Deployment**:
- Single Python process on laptop
- No database setup required
- No cloud account needed
- All data stored locally

**Optional Phase 2B**: Add SQLite for structured queries (still local)

---

## 🚀 Deployment & Demo Strategy

### Single-Click Demo Script

**Goal**: Non-technical user can demo POC on any laptop in 1 click

**Script Flow**:
```bash
./demo-start.sh
  ├─ Detect OS (Windows/Mac/Linux)
  ├─ Check Docker installed
  ├─ Download containers from Google Drive
  ├─ Extract + verify checksums
  ├─ Start docker-compose stack
  ├─ Wait for health checks
  ├─ Download demo video (drowsy_drive.mp4)
  ├─ Start DMS against demo video
  ├─ Open dashboard browser (localhost:3000)
  └─ Display status: "✅ Demo ready"
```

**Files to include**:
- `demo-start.sh` (main script)
- `dms-stack.yml` (docker-compose)
- `demo-config.json` (default thresholds)
- `README-DEMO.md` (instructions)

---

## 🔐 Approvals Required

### Docker Desktop / Docker Installation

**Status**: ⏳ Pending approval from Leadership

**Ticket**: To be raised with IT/Leadership

**Requirement**: 
- Docker Desktop installation on team laptops
- Docker container registry access (Docker Hub or GCR)
- Network access to pull images

**Impact if NOT approved**:
- Cannot containerize agents
- Cannot use single-click demo
- Must deploy agents manually on each laptop/board

**Mitigation** (if not approved):
- Provide Python venv-based deployment (slower, more manual)
- Host pre-built binaries for download

---

## 📅 Implementation Timeline

### Week 1 (Aug 5-9)
- [ ] Get Docker approval from Leadership
- [ ] Design agent interfaces (message contracts)
- [ ] Create Violation Detection Agent skeleton
- [ ] Start Dockerfile definitions

### Week 2 (Aug 12-16)
- [ ] Implement VDA rule engine
- [ ] Build evidence (JPG) capture
- [ ] Create docker-compose stack
- [ ] Test container communication

### Week 3 (Aug 19-23)
- [ ] Refine UI alarm display
- [ ] Create demo-start.sh script
- [ ] End-to-end testing (laptop → board)
- [ ] Documentation for deployment

### Week 4 (Aug 26-30)
- [ ] Performance tuning
- [ ] Security hardening
- [ ] Prepare for Phase 2 release
- [ ] Team training on new stack

---

## 📊 Success Criteria

### By End of Phase 2

**Technical**:
- ✅ 5 agents running independently in containers
- ✅ Single docker-compose up brings entire stack live
- ✅ Violations detected with <500ms latency
- ✅ Evidence (JPG) captured in every violation
- ✅ Dashboard updates in real-time via WebSocket

**Operational**:
- ✅ Single-click demo script works on clean laptop
- ✅ No manual setup steps (Docker pull + compose up)
- ✅ All data stored locally (no cloud dependencies)
- ✅ Runs on both board and laptop identically

**Deployment**:
- ✅ Containers pushed to registry (`dms/*`)
- ✅ demo-start.sh fully functional
- ✅ Fallback deployment guide (if Docker not approved)

---

## ⚠️ Dependencies & Blockers

| Blocker | Owner | Status | Mitigation |
|---------|-------|--------|-----------|
| Docker Desktop approval | Leadership/IT | ⏳ Pending ticket | Manual venv deployment (slower) |
| Network access to registry | IT | ⏳ Pending | Use Docker Hub (public) instead of GCR |
| Board availability for testing | Hardware team | ✅ Available | Laptop-first development, test board later |
| Violation Detection Agent design review | Team | 📋 Scheduled | Architecture doc provided (Page 3) |

---

## 🔄 Development Process

### Code Review
- All agent code reviewed before merge
- Dockerfile reviewed for security
- docker-compose.yml reviewed for configuration

### Testing
- Unit tests per agent
- Integration tests (agent communication)
- End-to-end test (demo video → violation detection)
- Performance test (latency, throughput)

### Documentation
- Agent API specifications (input/output contracts)
- Deployment guides (laptop, board, cloud)
- Troubleshooting runbook
- Demo script instructions

---

## 📝 References

| Document | Purpose | Location |
|----------|---------|----------|
| Architecture (Agents) | System design | POC_ARCHITECTURE.drawio (Page 3) |
| Flow Diagrams | Per-agent responsibilities | AGENT_WISE_FLOW_DIAGRAMS.md |
| Data Models | Event, Violation, Evidence, Alarm | VIOLATION_AND_EVIDENCE_MODELS.md |
| Violation Rules | Trigger conditions, severity | VIOLATION_AND_EVIDENCE_MODELS.md § Rules |
| Demo Script | Single-click deployment | TBD (demo-start.sh) |
| Docker Compose | Container orchestration | TBD (dms-stack.yml) |

---

## 💬 Questions & Discussion Points

1. **Container Registry**: GCR or Docker Hub?
2. **Database**: JSONL only, or add SQLite in Phase 2B?
3. **Message Queue**: In-process or RabbitMQ/Kafka for future?
4. **Board Deployment**: Immediately or after laptop stability?
5. **Demo Script**: Shell script or Python click CLI?

---

**Status**: Ready for team review & leadership approval  
**Next Step**: Leadership approval on Docker + kick-off planning meeting  
**Owner**: You (Server/Architecture Lead)

