"""Alarm Agent — the escalation tier. Turns a new-or-updated Violation from the
Violation Detection Agent into an Alarm (severity message + recommended-action
text already carried on the violation) and fires the in-cabin alert.

Two tiers, both local (see .claude/skills/dms-edge-dev/SKILL.md "Alarm Agent"):
1. Immediate — src/dms.py's speak() stub (frozen, unchanged): fires on the very
   first qualifying detection, before this agent even runs.
2. Escalation — this agent (new): fires once a genuine pattern is confirmed.

Ported from dms-backend/app/rule_agents/notification_rules.py (ALARM_MESSAGES,
SEVERITY_PRIORITY) — same templates, no LLM.

Simulated in-cabin response (driver_ack_latency_seconds, speed_before/after_kmh):
no real edge feedback channel exists for this POC, same as dms-backend's
notifier.upsert_alarm. dms-backend keeps these values stable across a growing
violation's repeat updates (only re-rolled when new); this agent is stateless
and re-rolls them on every fire instead — a deliberate simplification flagged as
unresolved in design.md's "Risks / open questions" and settled here in favor of
the simpler, stateless agent. Visually near-identical in a demo either way.
"""
from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass

from storage import models

ALARM_MESSAGES = {
    "DROWSINESS_PATTERN": "⚠️ DROWSINESS DETECTED. PULL OVER SAFELY.",
    "PHONE_USAGE": "⚠️ PHONE USAGE DETECTED. EYES ON THE ROAD.",
    "DISTRACTION_PATTERN": "⚠️ DISTRACTION DETECTED. STAY FOCUSED.",
    "CONTINUOUS_DRIVE": "⚠️ CONTINUOUS DRIVING > 4 HOURS. TAKE A BREAK.",
}

SEVERITY_PRIORITY = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}


@dataclass
class Alarm:
    """Output — maps 1:1 onto design.md's AlarmIn contract that CloudHubAgent pushes."""

    alarm_id: str
    violation_id: str
    fired_at: float
    message: str
    severity: str
    priority: int
    driver_ack_latency_seconds: float | None = None
    speed_before_kmh: float | None = None
    speed_after_kmh: float | None = None


class AlarmAgent:
    """BaseAgent[Violation, Alarm]."""

    name = "alarm_agent"

    def run(self, input_: models.Violation, speed_kmh: float | None = None) -> Alarm:
        violation = input_
        message = ALARM_MESSAGES.get(violation.violation_type, "⚠️ VIOLATION DETECTED.")
        fired_at = violation.last_event_timestamp or time.time()

        speed_before = speed_kmh if speed_kmh is not None else round(random.uniform(60, 90), 1)
        alarm = Alarm(
            alarm_id=f"alarm_{uuid.uuid4().hex[:12]}",
            violation_id=violation.violation_id,
            fired_at=fired_at,
            message=message,
            severity=violation.severity,
            priority=SEVERITY_PRIORITY.get(violation.severity, 3),
            driver_ack_latency_seconds=round(random.uniform(3, 12), 1),
            speed_before_kmh=speed_before,
            speed_after_kmh=round(speed_before * random.uniform(0.55, 0.75), 1),
        )

        print(f"[{self.name}] {message} (violation={violation.violation_id}, severity={violation.severity})")
        return alarm
