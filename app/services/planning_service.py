from datetime import date
from typing import Any
from sqlalchemy.orm import Session
from app.planners.interface import PlannerInterface
from app.planners.rule_based import RuleBasedPlanner


class PlanningService:
    def __init__(self, planner: PlannerInterface | None = None):
        self.planner = planner or RuleBasedPlanner()

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        return self.planner.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict) -> dict[str, Any]:
        return self.planner.replan(db=db, tenant_id=tenant_id, plan_date=plan_date, context=context)
