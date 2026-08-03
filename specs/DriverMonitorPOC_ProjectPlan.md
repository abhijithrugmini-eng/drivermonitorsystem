**Driver Monitor POC**

Project Plan — Edge AI \+ Agentic Framework

Version 1.0  ·  July 2026  ·  Capability Showcase POC

# **1\. Executive Summary**

The Driver Monitor POC **is a capability showcase** demonstrating Edge AI and Agentic AI applied to truck driver safety monitoring. The system detects behavioural events (drowsiness, phone use, sudden illness) at the edge, applies an agent-based decision layer, and reports incidents to fleet administrators via a cloud dashboard.

**Tech Stack:** OpenCV \+ pre-trained models (MediaPipe, YOLOv8, MoveNet) on Jetson Orin/RPi · LangGraph agentic layer · AWS IoT Core, DynamoDB, SNS/SES · React dashboard.

**Timeline:** 12 weeks · 5 team members · 6 phases.

# **2\. Team & Responsibilities**

| Name | Role | Phases |
| :---- | :---- | :---- |
| **Abhijith** | Solution Architect | P0, P3 (review), P5 (lead) |
| **Edge Expert** | Edge / Hardware | P1 (lead), P2 (support), P5 |
| **AI Expert 1** | AI / CV Models | P2 (lead), P3 (lead), P5 |
| **AI Expert 2** | Agentic & Cloud | P2 (test video), P3 (co-lead), P4 (cloud events), P5 |
| **UI Developer** | Dashboard / Frontend | P4 (lead), P5 |

# **3\. Phase Overview**

| Phase | Title | Weeks | Owner |
| :---- | :---- | :---- | :---- |
| **P0** | Architecture & Stack Lock | Weeks 1–2 | Architect (Abhijith) |
| **P1** | Edge Hardware \+ Camera Setup | Weeks 3–6 | Edge Expert |
| **P2** | AI Model Selection \+ CV Pipeline | Weeks 3–6 | AI Expert 1 \+ AI Expert 2 (test video) |
| **P3** | Agentic Layer (LangGraph) | Weeks 7–9 | AI Expert 1 \+ AI Expert 2 \+ Architect review |
| **P4** | Cloud Infra \+ Fleet Dashboard | Weeks 5–10 | UI Developer \+ AI Expert 2 (cloud events) |
| **P5** | Integration \+ Demo | Weeks 11–12 | All 5 |

# **4\. Phase Details**

**P0: Architecture & Stack Lock**

**Timeline:** Weeks 1–2

**Owner:** Architect (Abhijith)

**Goal:** Define the full end-to-end blueprint before parallel work begins. This is the gate phase.

**Key Tasks:**

• Select edge hardware candidates (Jetson Orin / RPi \+ Coral TPU)

• Choose AI model shortlist per behaviour (drowsiness, phone, posture)

• Decide agentic framework: LangGraph (recommended) or alternative

• Define AWS services: IoT Core / MQTT, S3, DynamoDB, SNS/SES

• Document API contracts between Edge ↔ Cloud

• Establish shared test video library requirements

**Deliverable:** Architecture decision record (ADR). Team alignment meeting. All 4 members briefed before Phase 1 begins.

**Dependency:** Gates all other phases.

**P1: Edge Hardware \+ Camera Setup**

**Timeline:** Weeks 3–6

**Owner:** Edge Expert

**Goal:** Source, configure and validate the edge inference device with live camera feeds.

**Key Tasks:**

• Procure edge device (Jetson Orin Nano or equivalent)

• Install Ubuntu, CUDA drivers, OpenCV

• Connect and configure in-cabin camera(s)

• Validate OpenCV frame capture pipeline

• Benchmark inference latency targets

• Document device spec and setup runbook

**Deliverable:** Live edge device streaming camera frames. Latency benchmark report.

**Dependency:** Unblocks AI model integration (P2 overlap).

**P2: AI Model Selection \+ CV Pipeline**

**Timeline:** Weeks 3–6

**Owner:** AI Expert 1 \+ AI Expert 2 (test video)

**Goal:** Identify, integrate and validate pre-trained CV models for all driver behaviours.

**Key Tasks:**

• Build shared mock/test video library (AI Expert 2 — parallel to hardware)

• Integrate drowsiness model: MediaPipe Face Mesh \+ EAR/MAR scoring

• Integrate phone detection: YOLOv8 fine-tuned on in-cabin dataset

• Integrate sudden illness / posture anomaly: pose estimation (MoveNet)

• Run inference on test video library first

• Port models to edge device, tune for latency

• Publish detection events with confidence scores and timestamps

**Deliverable:** Detection pipeline running on edge device. Confidence score outputs per behaviour.

**Dependency:** Required input for Agentic Layer (P3).

**P3: Agentic Layer (LangGraph)**

**Timeline:** Weeks 7–9

**Owner:** AI Expert 1 \+ AI Expert 2 \+ Architect review

**Goal:** Wrap detections in an AI agent that decides what to do and triggers actions.

**Key Tasks:**

• Design LangGraph state graph: detection events as state inputs

• Define node logic: alert thresholds, severity classification

• Implement escalation rules: alert → notify fleet admin, emergency → SOS

• Build action tools: SNS push, SES email, event log to DynamoDB

• Architect review of graph design and escalation logic

• Unit test agent with simulated detection events

**Deliverable:** Working LangGraph agent that accepts detection events and fires appropriate actions.

**Dependency:** Requires P2 detection outputs. Feeds P4 cloud events.

**P4: Cloud Infra \+ Fleet Dashboard**

**Timeline:** Weeks 5–10

**Owner:** UI Developer \+ AI Expert 2 (cloud events)

**Goal:** Build AWS backend and fleet admin dashboard. Can start in parallel from Week 5\.

**Key Tasks:**

• Set up AWS IoT Core MQTT broker for edge-to-cloud ingestion

• DynamoDB schema for driver events and incident records

• SNS topic \+ SES template for fleet admin alerts

• React dashboard: driver status cards, incident feed, live alert stream

• REST API (API Gateway \+ Lambda) for dashboard data

• Connect dashboard to live MQTT event stream

**Deliverable:** Fleet admin dashboard showing real-time driver status and incident feed.

**Dependency:** Cloud events wired from P3 agent actions.

**P5: Integration \+ Demo**

**Timeline:** Weeks 11–12

**Owner:** All 5

**Goal:** End-to-end system integration, scenario simulation, and POC demo recording.

**Key Tasks:**

• Wire edge → agent → cloud → dashboard full pipeline

• Simulate Scenario 1: driver drowsiness detected, fleet admin notified

• Simulate Scenario 2: phone usage detected, alert logged

• Simulate Scenario 3: sudden slump / possible illness, SOS escalation

• Record demo video walkthrough

• Prepare capability showcase presentation

**Deliverable:** Live end-to-end POC demo. Recorded showcase video. Architecture summary deck.

**Dependency:** All previous phases complete.

# **5\. Key Risks**

| Risk | Impact | Mitigation |
| :---- | :---- | :---- |
| Hardware procurement delay | High | Start with RPi+USB cam simulation while Jetson ships |
| Model accuracy on in-cabin video | Medium | Use test video library early; fine-tune if needed |
| LangGraph complexity for 2 new AI experts | Medium | Architect leads design session; start with simple linear graph |
| AWS infra setup time | Low | Use CDK/Terraform for repeatable infra; IoT Core has free tier |

# **6\. Open Source Stack Reference**

| Layer | Tool / Model | Purpose |
| :---- | :---- | :---- |
| Edge OS | Ubuntu 22 \+ CUDA | Base OS on Jetson Orin |
| Computer Vision | OpenCV 4 | Frame capture, preprocessing |
| Drowsiness | MediaPipe Face Mesh | EAR/MAR eye & mouth scoring |
| Phone Detection | YOLOv8 (Ultralytics) | Object detection, in-cabin tuned |
| Posture / Illness | MoveNet (TF Lite) | Pose estimation, anomaly score |
| Agentic Layer | LangGraph \+ LangChain | Decision graph, action tools |
| Edge-to-Cloud | AWS IoT Core (MQTT) | Secure event ingestion |
| Storage | DynamoDB | Driver events, incident log |
| Alerting | AWS SNS / SES | Push \+ email to fleet admin |
| Dashboard | React \+ API Gateway | Fleet admin UI |

