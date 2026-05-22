"""
ORToolsOptimizerAgent — Phase 2 (sequential).

Wraps the existing ORToolsPlanner (VRPTW solver) as a PlanningAgent.
The solver does its own DB queries internally — we pass the session from ctx.
"""
from __future__ import annotations

import logging
import time

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class ORToolsOptimizerAgent:
    name = "ORToolsOptimizerAgent"
    phase = 2
    execution = "sequential"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        try:
            from app.planners.ortools_planner import ORToolsPlanner

            result = ORToolsPlanner().plan_day(
                db=ctx["db"],
                tenant_id=ctx["tenant_id"],
                plan_date=ctx["plan_date"],
            )

            ctx["plan_result"] = result
            elapsed = int((time.monotonic() - t0) * 1000)

            assigned = result.get("assigned_orders", 0)
            total = result.get("total_orders", 0)
            routes = result.get("total_routes", 0)
            dropped = total - assigned

            warnings = []
            if dropped > 0:
                warnings.append(f"{dropped} order(s) could not be assigned — check capacity or time windows.")

            log_entry = {
                "step": self.name,
                "role": "tool",
                "content": (
                    f"OR-Tools assigned {assigned} of {total} orders "
                    f"across {routes} routes "
                    f"(planner={result.get('planner', 'unknown')}, "
                    f"{elapsed}ms)."
                ),
            }
            ctx["logs"].append(log_entry)

            return AgentResult(
                agent_name=self.name,
                status="completed",
                output=result,
                warnings=warnings,
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )

        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.exception("%s failed: %s", self.name, exc)
            log_entry = {"step": self.name, "role": "tool", "content": f"ERROR: {exc}"}
            ctx["logs"].append(log_entry)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                output={},
                warnings=[str(exc)],
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )
