"""Shared BaseAgent contract — duplicated per-component per
.claude/skills/dms-agentic-architecture/SKILL.md ("Why not a shared installable library").
"""
from __future__ import annotations

from typing import Protocol, TypeVar

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class BaseAgent(Protocol[TIn, TOut]):
    name: str  # stable id — used in logs, and becomes the node name if this is ever
               # wrapped as a LangGraph node

    def run(self, input_: TIn) -> TOut:
        """Given a typed input, produce a typed output. Avoid hidden global state —
        anything the agent needs across calls should be an explicit attribute on
        the agent instance, not a module-level global."""
        ...
