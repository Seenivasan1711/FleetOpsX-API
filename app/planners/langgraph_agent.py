"""
LangGraph Dispatch Agent — P2-E3

Wraps OR-Tools with LLM reasoning and a human-readable explanation.

Node pipeline:
  fetch_context  →  call_optimizer  →  explain  →  END

Fallback chain:
  LLM configured   →  full agent pipeline (fetch → optimize → explain)
  No LLM key       →  skip LLM nodes, fall straight through to ORToolsPlanner
  OR-Tools fails   →  ORToolsPlanner itself falls back to RuleBasedPlanner
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.llm_factory import get_llm_for_tenant
from app.models.agent_log import AgentLog
from app.planners.interface import PlannerInterface


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    tenant_id: str
    plan_date: date           # date object (not string)
    db: Any                   # Session — stays in memory, never serialised
    llm: Any                  # BaseChatModel | None
    context: dict             # summary fetched in fetch_context node
    plan_result: dict         # output from ORToolsPlanner
    explanation: str          # LLM-generated summary
    logs: list                # list of log dicts to persist after graph finishes


# ─── Planner ──────────────────────────────────────────────────────────────────

class LangGraphPlanner(PlannerInterface):

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        # Attempt to get LLM for tenant; if it fails or no key → pure OR-Tools
        llm = None
        try:
            llm = get_llm_for_tenant(db=db, tenant_id=tenant_id)
        except ValueError:
            pass  # no LLM key configured — will fall back below

        if llm is None:
            from app.planners.ortools_planner import ORToolsPlanner
            result = ORToolsPlanner().plan_day(db, tenant_id, plan_date)
            result["planner"] = "langgraph_no_llm"
            return result

        graph = _build_graph()
        final_state = graph.invoke({
            "tenant_id": tenant_id,
            "plan_date": plan_date,
            "db": db,
            "llm": llm,
            "context": {},
            "plan_result": {},
            "explanation": "",
            "logs": [],
        })

        # Resolve llm_provider from tenant KV (best-effort — for logging only)
        llm_provider = _resolve_provider(db, tenant_id)

        # Persist agent logs
        plan_id_str = final_state["plan_result"].get("plan_id")
        from uuid import UUID
        plan_uuid = UUID(plan_id_str) if plan_id_str else None

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
        plan["planner"] = "langgraph"
        return plan

    def replan(self, db: Session, tenant_id: str, plan_date: date, context: dict[str, Any]) -> dict[str, Any]:
        return self.plan_day(db=db, tenant_id=tenant_id, plan_date=plan_date)


# ─── Graph Nodes ──────────────────────────────────────────────────────────────

def _node_fetch_context(state: AgentState) -> AgentState:
    db = state["db"]
    tenant_id = state["tenant_id"]
    plan_date = state["plan_date"]

    from uuid import UUID
    from app.models.driver import Driver
    from app.models.order import Order

    tid = UUID(tenant_id)
    day_start = datetime.combine(plan_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    orders = db.execute(
        select(Order).where(
            Order.tenant_id == tid,
            Order.status == "PENDING",
            Order.scheduled_date >= day_start,
            Order.scheduled_date < day_end,
        )
    ).scalars().all()

    drivers = db.execute(
        select(Driver).where(Driver.tenant_id == tid, Driver.is_active == True)
    ).scalars().all()

    context = {
        "plan_date": str(plan_date),
        "total_orders": len(orders),
        "total_drivers": len(drivers),
        "orders_with_time_windows": sum(1 for o in orders if o.time_window_start),
        "high_priority_orders": sum(1 for o in orders if o.priority in ("HIGH", "CRITICAL")),
    }

    log = {
        "step": "fetch_context",
        "role": "tool",
        "content": (
            f"Fetched {len(orders)} pending orders and {len(drivers)} active drivers "
            f"for {plan_date}. "
            f"{context['high_priority_orders']} high/critical priority, "
            f"{context['orders_with_time_windows']} with time windows."
        ),
    }
    return {**state, "context": context, "logs": state["logs"] + [log]}


def _node_call_optimizer(state: AgentState) -> AgentState:
    from app.planners.ortools_planner import ORToolsPlanner

    result = ORToolsPlanner().plan_day(
        db=state["db"],
        tenant_id=state["tenant_id"],
        plan_date=state["plan_date"],
    )

    log = {
        "step": "call_optimizer",
        "role": "tool",
        "content": (
            f"OR-Tools assigned {result.get('assigned_orders', 0)} of "
            f"{result.get('total_orders', 0)} orders across "
            f"{result.get('total_routes', 0)} routes "
            f"(planner={result.get('planner', 'unknown')})."
        ),
    }
    return {**state, "plan_result": result, "logs": state["logs"] + [log]}


def _node_explain(state: AgentState) -> AgentState:
    llm = state["llm"]
    ctx = state["context"]
    plan = state["plan_result"]

    prompt = (
        "You are a fleet dispatch AI assistant. Summarize the following routing plan "
        "in 2-3 concise, professional sentences for a dispatcher.\n\n"
        f"Date: {ctx.get('plan_date')}\n"
        f"Orders: {plan.get('total_orders', 0)} total, "
        f"{plan.get('assigned_orders', 0)} assigned\n"
        f"Routes: {plan.get('total_routes', 0)} drivers assigned\n"
        f"High/Critical priority: {ctx.get('high_priority_orders', 0)}\n"
        f"Orders with time windows: {ctx.get('orders_with_time_windows', 0)}\n"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        explanation = response.content
    except Exception as exc:
        explanation = (
            f"Plan generated: {plan.get('assigned_orders', 0)} orders assigned "
            f"to {plan.get('total_routes', 0)} drivers. (LLM error: {exc})"
        )

    log = {"step": "explain", "role": "llm", "content": explanation}
    return {**state, "explanation": explanation, "logs": state["logs"] + [log]}


# ─── Graph builder ────────────────────────────────────────────────────────────

def _build_graph():
    wf = StateGraph(AgentState)
    wf.add_node("fetch_context", _node_fetch_context)
    wf.add_node("call_optimizer", _node_call_optimizer)
    wf.add_node("explain", _node_explain)
    wf.set_entry_point("fetch_context")
    wf.add_edge("fetch_context", "call_optimizer")
    wf.add_edge("call_optimizer", "explain")
    wf.add_edge("explain", END)
    return wf.compile()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_provider(db: Session, tenant_id: str) -> str | None:
    """Read llm_provider from TenantConfig KV (best-effort)."""
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
