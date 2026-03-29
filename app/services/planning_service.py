from datetime import date
from typing import Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.planners.interface import PlannerInterface


def get_planner() -> PlannerInterface:
    """
    Return the correct planner based on PLANNER_TYPE in .env.

    PLANNER_TYPE options:
      rule_based  → RuleBasedPlanner   (Phase 1, greedy nearest-driver)
      ortools     → ORToolsPlanner     (Phase 2, VRPTW solver)
      langgraph   → LangGraphPlanner   (Phase 2, LLM agent + OR-Tools)
    """
    planner_type = settings.PLANNER_TYPE.lower()

    if planner_type == "ortools":
        from app.planners.ortools_planner import ORToolsPlanner
        return ORToolsPlanner()

    if planner_type == "langgraph":
        from app.planners.langgraph_agent import LangGraphPlanner
        return LangGraphPlanner()

    # Default — rule_based
    from app.planners.rule_based import RuleBasedPlanner
    return RuleBasedPlanner()


class PlanningService:
    def __init__(self, planner: PlannerInterface | None = None):
        self.planner = planner or get_planner()

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        return self.planner.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict) -> dict[str, Any]:
        return self.planner.replan(db=db, tenant_id=tenant_id, plan_date=plan_date, context=context)
