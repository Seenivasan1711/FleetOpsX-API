"""
Multi-Agent LangGraph Orchestrator — P3-E2

4-node pipeline:
  fetch_context → forecast → call_optimizer → explain → END

fetch_context : gather orders + drivers (from P2 LangGraph agent)
forecast      : day-of-week demand baseline from DeliveryAnalytics (new in P3)
call_optimizer: run OR-Tools with forecast context
explain       : LLM-generated summary including forecast insights

The Monitor Agent runs separately via APScheduler — it is NOT a node here.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    tenant_id: str
    plan_date: date
    db: Any           # Session
    llm: Any          # BaseChatModel | None
    context: dict     # orders/drivers summary
    forecast: dict    # day-of-week demand forecast
    plan_result: dict # output from ORToolsPlanner
    explanation: str
    logs: list


# ─── Nodes ────────────────────────────────────────────────────────────────────

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

    forecast = state.get("forecast", {})
    high_risk = forecast.get("high_risk_zones", [])

    log = {
        "step": "call_optimizer",
        "role": "tool",
        "content": (
            f"OR-Tools assigned {result.get('assigned_orders', 0)} of "
            f"{result.get('total_orders', 0)} orders across "
            f"{result.get('total_routes', 0)} routes."
            + (f" High-risk zones flagged: {', '.join(high_risk)}." if high_risk else "")
        ),
    }
    return {**state, "plan_result": result, "logs": state["logs"] + [log]}


def _node_explain(state: AgentState) -> AgentState:
    llm = state["llm"]
    ctx = state["context"]
    plan = state["plan_result"]
    forecast = state.get("forecast", {})

    forecast_lines = ""
    if forecast.get("expected_order_count"):
        forecast_lines = (
            f"\nForecast (historical baseline): "
            f"{forecast['expected_order_count']} orders expected, "
            f"{forecast.get('recommended_driver_count', '?')} drivers recommended."
        )
    if forecast.get("high_risk_zones"):
        forecast_lines += f"\nHigh-risk zones today: {', '.join(forecast['high_risk_zones'])}."

    prompt = (
        "You are a fleet dispatch AI assistant. Summarize the following routing plan "
        "in 2-3 concise, professional sentences for a dispatcher.\n\n"
        f"Date: {ctx.get('plan_date')}\n"
        f"Orders: {plan.get('total_orders', 0)} total, {plan.get('assigned_orders', 0)} assigned\n"
        f"Routes: {plan.get('total_routes', 0)} drivers assigned\n"
        f"High/Critical priority: {ctx.get('high_priority_orders', 0)}\n"
        f"Orders with time windows: {ctx.get('orders_with_time_windows', 0)}\n"
        f"{forecast_lines}"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        explanation = response.content
    except Exception as exc:
        explanation = (
            f"Plan generated: {plan.get('assigned_orders', 0)} orders assigned "
            f"to {plan.get('total_routes', 0)} drivers."
            + (f" {forecast.get('summary', '')}" if forecast.get("summary") else "")
            + f" (LLM error: {exc})"
        )

    log = {"step": "explain", "role": "llm", "content": explanation}
    return {**state, "explanation": explanation, "logs": state["logs"] + [log]}


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_multi_agent_graph():
    """Build and compile the 4-node orchestrator graph."""
    from app.planners.agents.forecast_agent import _node_forecast

    wf = StateGraph(AgentState)
    wf.add_node("fetch_context", _node_fetch_context)
    wf.add_node("forecast", _node_forecast)
    wf.add_node("call_optimizer", _node_call_optimizer)
    wf.add_node("explain", _node_explain)

    wf.set_entry_point("fetch_context")
    wf.add_edge("fetch_context", "forecast")
    wf.add_edge("forecast", "call_optimizer")
    wf.add_edge("call_optimizer", "explain")
    wf.add_edge("explain", END)

    return wf.compile()
