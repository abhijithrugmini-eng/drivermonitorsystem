# Violation & Evidence Data Models for POC

**Date**: August 1, 2026  
**Purpose**: Reference for developers  
**Scope**: POC Phase (Aug 1-14)

---

## 📋 Quick Summary

| Model | Source | Destination | Purpose |
|-------|--------|-------------|---------|
| **Event** | DMS (Edge) | Server | Raw detection: EAR, MAR, phone, etc. |
| **Violation** | Server | Dashboard | Aggregated: 3 events → 1 violation |
| **Evidence** | Server | Dashboard | JPG of violation moment |
| **Alarm** | Server | Dashboard | Alert message for driver |

---

## 1️⃣ EVENT (Edge → Server)

**Source**: DMS (YOLO + MediaPipe)  
**Destination**: Server (POST /events)  
**Storage**: logs/events.jsonl  
**Frequency**: Every violation detected (~1-5 per minute during demo)

### Full Event Model

```json
{
  "event_id": "evt_20260801_153000_001",
  "timestamp": 1722638401.23,
  "source": "dms_v1.0",
  
  "detection": {
    "type": "DROWSINESS",
    "confidence": 0.95,
    "metrics": {
      "ear": 0.18,
      "duration_seconds": 0.75,
      "blink_rate": 8.5,
      "eyelid_closure_percent": 85
    }
  },
  
  "context": {
    "trip_id": "trip_20260801_morning_commute",
    "elapsed_trip_seconds": 245,
    "frame_index": 5678,
    "camera_id": "cabin_front"
  },
  
  "vehicle": {
    "speed_kmh": 80.5,
    "is_moving": true,
    "throttle_percent": 45,
    "brake_engaged": false
  },
  
  "device": {
    "device_id": "edge_001",
    "device_model": "renesas_rcar",
    "os": "linux",
    "processing_time_ms": 45
  }
}
```

### Event Types & Fields

| Type | Metrics | Confidence Range | Typical Threshold |
|------|---------|------------------|-------------------|
| **DROWSINESS** | `ear`, `duration_seconds`, `blink_rate` | 0.70-0.99 | EAR < 0.21 for 0.7s |
| **YAWNING** | `mar`, `duration_seconds`, `mouth_open_percent` | 0.75-0.99 | MAR > 0.5 for 0.5s |
| **PHONE_USAGE** | `phone_detected`, `hand_on_phone`, `eye_contact_lost` | 0.45-0.95 | YOLO detection + MediaPipe |
| **DISTRACTION** | `head_yaw_degrees`, `head_pitch_degrees`, `gaze_duration` | 0.70-0.99 | Yaw > 30° for 1.0s |
| **NO_FACE** | `face_detected`, `face_count` | binary | No faces in frame |
| **CONTINUOUS_DRIVE** | `drive_duration_hours`, `last_break_minutes` | 0.90 | > 4 hours |

### Python Dataclass Example

```python
from dataclasses import dataclass
from typing import Dict, Any
import time

@dataclass
class Event:
    event_id: str
    timestamp: float
    type: str  # DROWSINESS, PHONE_USAGE, DISTRACTION, etc.
    confidence: float  # 0.0-1.0
    metrics: Dict[str, Any]
    trip_context: Dict[str, Any]
    vehicle_context: Dict[str, Any]
    device_info: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "type": self.type,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "trip_context": self.trip_context,
            "vehicle_context": self.vehicle_context,
            "device_info": self.device_info,
        }
    
    def to_jsonl_line(self) -> str:
        import json
        return json.dumps(self.to_dict())

# Usage in dms.py
event = Event(
    event_id=f"evt_{int(time.time())}_{frame_index}",
    timestamp=time.time(),
    type="DROWSINESS",
    confidence=0.95,
    metrics={"ear": 0.18, "duration_seconds": 0.75},
    trip_context={"trip_id": "trip_123", "elapsed_seconds": 245},
    vehicle_context={"speed_kmh": 80.5, "is_moving": True},
    device_info={"device_id": "edge_001", "processing_time_ms": 45}
)

# Send to server
requests.post("http://server:8000/events", json=event.to_dict())

# Log locally
with open("logs/events.jsonl", "a") as f:
    f.write(event.to_jsonl_line() + "\n")
```

---

## 2️⃣ VIOLATION (Server Output)

**Source**: Server Violation Detection Engine  
**Destination**: Dashboard (WebSocket /violations/stream)  
**Storage**: logs/violations.jsonl  
**Frequency**: When rule is triggered (1-2 per minute during demo)

### Full Violation Model

```json
{
  "violation_id": "viol_20260801_153000_drw001",
  "timestamp": 1722638401.24,
  
  "violation_type": "DROWSINESS_PATTERN",
  "severity": "CRITICAL",
  "status": "ACTIVE",
  "rule_id": "drowsiness_3in2min",
  
  "rule_details": {
    "rule_name": "3 Drowsiness Events in 2 Minutes",
    "rule_description": "If 3 or more DROWSINESS events occur within 2 minutes, flag as violation",
    "rule_version": "1.0",
    "triggered_at": 1722638401.24
  },
  
  "evidence": {
    "event_count": 3,
    "events": [
      {
        "event_id": "evt_001",
        "timestamp": 1722638200.0,
        "type": "DROWSINESS",
        "ear": 0.18,
        "duration": 0.73
      },
      {
        "event_id": "evt_002",
        "timestamp": 1722638260.0,
        "type": "DROWSINESS",
        "ear": 0.16,
        "duration": 0.68
      },
      {
        "event_id": "evt_003",
        "timestamp": 1722638401.23,
        "type": "DROWSINESS",
        "ear": 0.18,
        "duration": 0.75
      }
    ],
    "first_event_timestamp": 1722638200.0,
    "last_event_timestamp": 1722638401.23,
    "time_window_seconds": 201.23,
    "first_frame_jpg": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEA...",
    "first_frame_size_kb": 48
  },
  
  "severity_score": {
    "base_score": 0.95,
    "context_modifiers": {
      "vehicle_speed_kmh": 80,
      "is_night_driving": false,
      "time_since_break_minutes": 120
    },
    "final_score": 0.95
  },
  
  "alarm_action": {
    "alarm_triggered": true,
    "alarm_id": "alarm_20260801_153000_001",
    "alarm_message": "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
    "alarm_timestamp": 1722638401.24,
    "channels": {
      "visual": {
        "enabled": true,
        "display_type": "RED_BANNER",
        "priority": "CRITICAL"
      },
      "tts": {
        "enabled": false,
        "reason": "Phase 2 feature - not enabled in POC"
      },
      "websocket": {
        "enabled": true,
        "broadcast_status": "SENT",
        "clients_notified": 2
      }
    }
  },
  
  "driver_action": {
    "acknowledged": false,
    "acknowledge_timestamp": null,
    "driver_response": null
  },
  
  "lifecycle": {
    "created_at": 1722638401.24,
    "updated_at": 1722638401.24,
    "lifecycle_status": "ACTIVE",
    "can_acknowledge": true,
    "can_resolve": false
  }
}
```

### Violation Types & Rules

#### Rule 1: DROWSINESS_PATTERN
```
Condition: 3 or more DROWSINESS events within 2 minutes
Severity: CRITICAL
Evidence: Array of 3 events + first frame JPG
Action: Broadcast alarm immediately
Dashboard: Red banner, high priority
```

#### Rule 2: PHONE_USAGE
```
Condition: 1 PHONE_USAGE event with confidence > 0.85
Severity: HIGH
Evidence: Single event + frame JPG
Action: Broadcast alarm immediately
Dashboard: Orange banner, medium priority
```

#### Rule 3: DISTRACTION_PATTERN
```
Condition: 2+ DISTRACTION events within 1 minute
Severity: MEDIUM
Evidence: Array of 2+ events + first frame JPG
Action: Broadcast alert
Dashboard: Yellow banner, medium priority
```

#### Rule 4: CONTINUOUS_DRIVE
```
Condition: Driving > 4 hours without break
Severity: LOW
Evidence: Trip duration + timestamp range
Action: Broadcast suggestion
Dashboard: Blue banner, low priority
```

### Python Dataclass Example

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ViolationSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ViolationStatus(Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

@dataclass
class Evidence:
    event_count: int
    events: List[Dict[str, Any]]
    first_event_timestamp: float
    last_event_timestamp: float
    first_frame_jpg: Optional[str] = None  # base64 encoded
    first_frame_size_kb: Optional[float] = None

@dataclass
class AlarmAction:
    alarm_triggered: bool
    alarm_message: str
    alarm_timestamp: float
    channels: Dict[str, bool] = field(default_factory=lambda: {
        "visual": True,
        "tts": False,
        "websocket": True
    })

@dataclass
class Violation:
    violation_id: str
    timestamp: float
    violation_type: str  # DROWSINESS_PATTERN, PHONE_USAGE, etc.
    severity: ViolationSeverity
    status: ViolationStatus
    rule_id: str
    evidence: Evidence
    alarm_action: AlarmAction
    severity_score: float
    
    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "timestamp": self.timestamp,
            "violation_type": self.violation_type,
            "severity": self.severity.value,
            "status": self.status.value,
            "rule_id": self.rule_id,
            "evidence": {
                "event_count": self.evidence.event_count,
                "events": self.evidence.events,
                "first_frame_jpg": self.evidence.first_frame_jpg,
            },
            "alarm_action": {
                "alarm_triggered": self.alarm_action.alarm_triggered,
                "alarm_message": self.alarm_action.alarm_message,
                "alarm_timestamp": self.alarm_action.alarm_timestamp,
            },
            "severity_score": self.severity_score,
        }

# Usage in server
violation = Violation(
    violation_id="viol_001",
    timestamp=time.time(),
    violation_type="DROWSINESS_PATTERN",
    severity=ViolationSeverity.CRITICAL,
    status=ViolationStatus.ACTIVE,
    rule_id="drowsiness_3in2min",
    evidence=Evidence(
        event_count=3,
        events=[...],  # list of 3 events
        first_event_timestamp=...,
        last_event_timestamp=time.time(),
        first_frame_jpg=base64_jpg_string
    ),
    alarm_action=AlarmAction(
        alarm_triggered=True,
        alarm_message="⚠️ DROWSINESS DETECTED",
        alarm_timestamp=time.time()
    ),
    severity_score=0.95
)

# Broadcast via WebSocket
await broadcast_violation(violation.to_dict())
```

---

## 3️⃣ EVIDENCE (JPG of Violation)

**Source**: DMS (first frame when violation triggered)  
**Destination**: Dashboard (in violation object)  
**Format**: Base64 JPEG  
**Size**: ~40-60 KB per image  
**Frequency**: 1 per violation

### How to Capture Evidence (POC)

```python
import cv2
import base64
from io import BytesIO

def capture_frame_as_jpg_base64(frame: cv2.Mat, quality: int = 70) -> str:
    """Capture frame and encode as base64 JPEG"""
    # Compress JPEG
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    
    # Encode as base64
    jpg_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return f"data:image/jpeg;base64,{jpg_base64}"

# Usage in DMS (when violation detected)
violation_frame = current_frame.copy()
jpg_evidence = capture_frame_as_jpg_base64(violation_frame)

# Include in violation
violation.evidence.first_frame_jpg = jpg_evidence
```

### How to Display in React

```jsx
// In Dashboard.jsx
import React from 'react';

export function ViolationCard({ violation }) {
  return (
    <div className="violation-card">
      <h3>{violation.violation_type}</h3>
      
      {/* Evidence JPG */}
      {violation.evidence.first_frame_jpg && (
        <img
          src={violation.evidence.first_frame_jpg}
          alt="Violation Evidence"
          style={{ width: '100%', maxWidth: '300px', borderRadius: '5px' }}
        />
      )}
      
      <p>Severity: {violation.severity}</p>
      <p>Message: {violation.alarm_action.alarm_message}</p>
    </div>
  );
}
```

---

## 4️⃣ ALARM (Server-Side)

**Source**: Server Alarm Agent  
**Destination**: Dashboard (WebSocket /alarms/stream)  
**Storage**: logs/alarms.jsonl  
**Frequency**: Same as violations

### Full Alarm Model

```json
{
  "alarm_id": "alarm_20260801_153000_001",
  "timestamp": 1722638401.24,
  "violation_id": "viol_20260801_153000_drw001",
  
  "alarm_type": "DROWSINESS_ALERT",
  "severity": "CRITICAL",
  "message": "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
  
  "audience": "DRIVER",
  "priority": 1,
  
  "dispatch": {
    "visual": {
      "enabled": true,
      "method": "RED_BANNER",
      "display_seconds": 10,
      "blink_interval_ms": 500
    },
    "audio": {
      "enabled": false,
      "method": "tts",
      "reason": "Phase 2 feature"
    },
    "websocket": {
      "enabled": true,
      "broadcast_timestamp": 1722638401.25,
      "clients_reached": 2
    }
  },
  
  "status": {
    "sent_at": 1722638401.24,
    "acknowledged_at": null,
    "dismissed_at": null,
    "state": "PENDING_ACK"
  }
}
```

---

## 📊 Storage Format: JSONL (One JSON per line)

### events.jsonl
```
{"event_id":"evt_001","timestamp":1722638200.0,"type":"DROWSINESS",...}
{"event_id":"evt_002","timestamp":1722638260.0,"type":"DROWSINESS",...}
{"event_id":"evt_003","timestamp":1722638401.23,"type":"DROWSINESS",...}
```

### violations.jsonl
```
{"violation_id":"viol_001","timestamp":1722638401.24,"violation_type":"DROWSINESS_PATTERN",...}
{"violation_id":"viol_002","timestamp":1722638500.0,"violation_type":"PHONE_USAGE",...}
```

### alarms.jsonl
```
{"alarm_id":"alarm_001","timestamp":1722638401.24,"violation_id":"viol_001",...}
{"alarm_id":"alarm_002","timestamp":1722638500.0,"violation_id":"viol_002",...}
```

---

## 🔗 Sample End-to-End Flow

```
1. DMS detects drowsy eyes (EAR=0.18)
   → Event 1: {"type": "DROWSINESS", "ear": 0.18, "duration": 0.73}
   → POST /events → Server stores in events.jsonl

2. DMS detects drowsy eyes again (1 min later)
   → Event 2: {"type": "DROWSINESS", "ear": 0.16, "duration": 0.68}
   → POST /events → Server stores in events.jsonl

3. DMS detects drowsy eyes again (2 min after first event)
   → Event 3: {"type": "DROWSINESS", "ear": 0.18, "duration": 0.75}
   → POST /events → Server stores in events.jsonl

4. Server Violation Engine triggers (3 events in 2 min):
   → Violation: {"violation_type": "DROWSINESS_PATTERN", "severity": "CRITICAL"}
   → Store in violations.jsonl
   → Capture first frame as JPG

5. Server Alarm Agent receives violation:
   → Alarm: {"message": "⚠️ DROWSINESS DETECTED", "severity": "CRITICAL"}
   → Store in alarms.jsonl
   → Broadcast via WebSocket

6. Dashboard receives WebSocket message:
   → Display red banner: "DROWSINESS DETECTED"
   → Show violation card with JPG evidence
   → Increment "Drowsiness Count" to 1

7. Customer sees on dashboard:
   ✅ Violation card with timestamp
   ✅ JPG of driver's face at violation moment
   ✅ Raw events that triggered violation
   ✅ Alarm message
```

---

## 📋 Checklist for Developers

### AI Engineer (Event Model)
- [ ] Implement Event dataclass
- [ ] Emit Event after each violation detection
- [ ] Include all metrics (EAR, MAR, etc.)
- [ ] POST to server:8000/events
- [ ] Log to events.jsonl locally

### Server Developer (Violation + Alarm Models)
- [ ] Implement Violation dataclass
- [ ] Implement Alarm dataclass
- [ ] Create violation rules engine
- [ ] Capture frame as JPG evidence
- [ ] Store violations to violations.jsonl
- [ ] Store alarms to alarms.jsonl
- [ ] Broadcast violations via WebSocket

### UI Developer (Display)
- [ ] Connect to /violations/stream
- [ ] Parse violation JSON
- [ ] Display violation card with JPG
- [ ] Show alarm message
- [ ] Update violation counters

---

**Status**: Ready for development  
**Reference**: DESIGN_DECISION_EDGE_VS_SERVER_VIOLATIONS.md for architecture choice  
**Next**: Share these models with your team before kickoff Monday

