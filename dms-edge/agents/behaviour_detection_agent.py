"""Behaviour Detection Agent — a thin wrapper around the frozen, vendored
src/dms.py's DriverMonitoringSystem. No detection logic lives here; it is 100%
delegation to the reference CV pipeline.

See .claude/skills/dms-edge-dev/SKILL.md "Behaviour Detection Agent".
"""
from __future__ import annotations

import numpy as np

from src.dms import DriverMonitoringSystem, EventSink
from src.events import DMSEvent


class BehaviourDetectionAgent(EventSink):
    """BaseAgent[Frame, list[DMSEvent]]. Also usable directly as an EventSink so it
    can sit alongside the file logger / SSE sink in main.py's fan-out — the
    DriverMonitoringSystem it wraps calls self.emit() synchronously during
    process_frame(), which run() collects into the returned list."""

    name = "behaviour_detection_agent"

    def __init__(self) -> None:
        self._dms = DriverMonitoringSystem(sink=self)
        self._pending: list[DMSEvent] = []
        self.last_frame: np.ndarray | None = None  # annotated frame from the most recent run()

    def emit(self, event: DMSEvent) -> None:
        self._pending.append(event)

    def close(self) -> None:
        pass

    @property
    def dms(self) -> DriverMonitoringSystem:
        return self._dms

    def run(self, input_: np.ndarray, frame_index: int = 0, frame_dt: float = 0.0) -> list[DMSEvent]:
        self._pending = []
        self.last_frame = self._dms.process_frame(input_, frame_index=frame_index, frame_dt=frame_dt)
        events, self._pending = self._pending, []
        return events
