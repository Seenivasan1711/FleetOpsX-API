"""
MultiAgentPlanner — P3-E2

Activated when PLANNER_TYPE=multi_agent.
Runs the 4-node LangGraph orchestrator:
  fetch_context → forecast → call_optimizer → explain

Falls back to ORToolsPlanner if no LLM is configured.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.planners.interface import PlannerInterface

logger = logging.getLogger(__name__)


class MultiAgentPlanner(PlannerInterface):

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        from app.core.llm_factory import get_llm_for_tenant
        from app.planners.orchestrator import build_multi_agent_graph
        from app.models.agent_log import AgentLog

        # Attempt to get configured LLM; fall back to OR-Tools if absent
        llm = None
        try:
            llm = get_llm_for_tenant(db=db, tenant_id=tenant_id)
        except ValueError:
            pass

        if llm is None:
            from app.planners.ortools_planner import ORToolsPlanner
            result = ORToolsPlanner().plan_day(db, tenant_id, plan_date)
            result["planner"] = "multi_agent_no_llm"
            return result

        graph = build_multi_agent_graph()
        final_state = graph.invoke({
            "tenant_id": tenant_id,
            "plan_date": plan_date,
            "db": db,
            "llm": llm,
            "context": {},
            "forecast": {},
            "plan_result": {},
            "explanation": "",
            "logs": [],
        })

        # Persist agent logs
        from uuid import UUID
        plan_id_str = final_state["plan_result"].get("plan_id")
        plan_uuid = UUID(plan_id_str) if plan_id_str else None
        llm_provider = _resolve_provider(db, tenant_id)

        for entry in final_state.get("logs", []):
            db.add(AgentLog(
                tenant_id=tenant_id,
                plan_id=plan_uuid,
                step=entry["step"],
                role=entry["role"],
                content=entry["content"],
                llm_provider=llm_provider,
            ))
        db.commit()

        plan = final_state["plan_result"]
        plan["explanation"] = final_state.get("explanation", "")
        plan["forecast"] = final_state.get("forecast", {})
        plan["planner"] = "multi_agent"
        return plan

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict[str, Any]) -> dict[str, Any]:
        return self.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)


def _resolve_provider(db: Session, tenant_id: str) -> str | None:
    try:
        from uuid import UUID
        from sqlalchemy import select
        from app.models.tenant import TenantConfig
        row = db.execute(
            select(TenantConfig).where(
                TenantConfig.tenant_id == UUID(tenant_id),
                TenantConfig.config_key == "llm_provider",
            )
        ).scalar_one_or_none()
        return row.config_value if row else None
    except Exception:
        return None
