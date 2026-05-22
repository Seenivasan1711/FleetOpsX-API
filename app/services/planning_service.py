"""
PlanningService — AI-1 E1.

Routes plan requests to either the new AI-1 runner (PLANNER_TYPE=ai1 or
the new default) or the legacy planners for backward compatibility.

PLANNER_TYPE values:
  ai1         → new 3-phase runner (default going forward)
  langgraph   → legacy LangGraphPlanner
  ortools     → legacy ORToolsPlanner (no LLM)
  rule_based  → legacy greedy fallback
  multi_agent → legacy multi-agent orchestrator
"""
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.planners.interface import PlannerInterface


def get_planner() -> PlannerInterface:
    planner_type = settings.PLANNER_TYPE.lower()

    if planner_type in ("ai1", "langgraph"):
        from app.planners.langgraph_agent import LangGraphPlanner
        return LangGraphPlanner()

    if planner_type == "ortools":
        from app.planners.ortools_planner import ORToolsPlanner
        return ORToolsPlanner()

    if planner_type == "multi_agent":
        from app.planners.multi_agent_planner import MultiAgentPlanner
        return MultiAgentPlanner()

    from app.planners.rule_based import RuleBasedPlanner
    return RuleBasedPlanner()


class PlanningService:
    def __init__(self, planner: PlannerInterface | None = None):
        self.planner = planner or get_planner()

    def plan_day(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        session_id: str = "",
        session_hints: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a day plan.

        When PLANNER_TYPE=ai1 (or default), uses the new 3-phase runner.
        All other PLANNER_TYPE values use the legacy planner path for
        backward compatibility.
        """
        planner_type = settings.PLANNER_TYPE.lower()
        if planner_type == "ai1":
            return self._run_ai1(
                db=db,
                tenant_id=tenant_id,
                plan_date=plan_date,
                session_id=session_id,
                session_hints=session_hints,
            )
        return self.planner.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)

    def replan(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        context: dict,
    ) -> dict[str, Any]:
        planner_type = settings.PLANNER_TYPE.lower()
        if planner_type == "ai1":
            hints = context.get("hints", [])
            session_id = context.get("session_id", "")
            return self._run_ai1(
                db=db,
                tenant_id=tenant_id,
                plan_date=plan_date,
                session_id=session_id,
                session_hints=hints,
            )
        return self.planner.replan(db=db, tenant_id=tenant_id, plan_date=plan_date, context=context)

    def _run_ai1(
        self,
        *,
        db: Session,
        tenant_id: str,
        plan_date: date,
        session_id: str = "",
        session_hints: list[str] | None = None,
    ) -> dict[str, Any]:
        from app.planners.runner import run_planning
        return run_planning(
            db=db,
            tenant_id=tenant_id,
            plan_date=plan_date,
            session_id=session_id,
            session_hints=session_hints,
        )
