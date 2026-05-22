"""
PlanningAgent protocol — AI-1 E1.

Every pluggable agent implements this interface.

To add a new agent:
  1. Create app/planners/agents/my_agent.py and implement this protocol.
  2. Add it to the correct phase list in app/planners/registry.py.
  Nothing else changes.
"""
from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from app.planners.context import AgentContext, AgentResult


@runtime_checkable
class PlanningAgent(Protocol):
    name: str
    phase: Literal[1, 2, 3]
    execution: Literal["parallel", "sequential"]

    def run(self, ctx: AgentContext) -> AgentResult:
        """
        Execute the agent.

        Agents write their outputs directly into ctx (ctx is a plain dict at
        runtime) AND return an AgentResult for logging and tracking.

        Agents must NOT raise — catch all exceptions, set status="failed",
        and include the error in log_entry. The runner decides whether to
        continue or abort based on the agent's phase and status.
        """
        ...
