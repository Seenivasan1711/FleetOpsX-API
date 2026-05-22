"""
LangGraph Dispatch Agent — P2-E3 / PP-E1

Wraps OR-Tools with LLM reasoning, pre-planning risk analysis, and chain-of-thought explanation.

Node pipeline:
  fetch_context  →  analyze  →  call_optimizer  →  explain  →  END

Fallback chain:
  LLM configured   →  full agent pipeline
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
    warnings: list            # pre-planning risk flags from analyze node
    confidence_score: float   # 0.0–1.0, refined through analyze + explain
    reasoning_steps: list     # chain-of-thought strings from explain node
    explanation: str          # LLM-generated human-readable summary
    logs: list                # list of log dicts to persist after graph finishes


# ─── Planner ──────────────────────────────────────────────────────────────────

class LangGraphPlanner(PlannerInterface):

    def plan_day(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
        # Delegate to the unified AI-1 runner (E1). The old graph is kept below
        # for reference but is no longer invoked via this path.
        from app.planners.runner import run_planning
        return run_planning(db=db, tenant_id=tenant_id, plan_date=plan_date)

    def _plan_day_legacy(self, db: Session, tenant_id: str, plan_date: date) -> dict[str, Any]:
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
            "warnings": [],
            "confidence_score": 1.0,
            "reasoning_steps": [],
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
        plan["ai_summary"] = final_state.get("explanation", "")
        plan["confidence_score"] = final_state.get("confidence_score", None)
        plan["reasoning_steps"] = final_state.get("reasoning_steps", [])
        plan["warnings"] = final_state.get("warnings", [])
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


def _node_analyze(state: AgentState) -> AgentState:
    """Rules-based pre-planning risk analysis. Flags issues and sets initial confidence."""
    ctx = state["context"]
    warnings: list[str] = []

    total_orders = ctx.get("total_orders", 0)
    total_drivers = ctx.get("total_drivers", 0)
    high_priority = ctx.get("high_priority_orders", 0)
    with_windows = ctx.get("orders_with_time_windows", 0)

    if total_drivers == 0:
        warnings.append("No active drivers available — plan cannot be generated.")

    if total_orders == 0:
        warnings.append("No pending orders for this date.")

    if total_drivers > 0 and total_orders > total_drivers * 15:
        warnings.append(
            f"High load: {total_orders} orders for {total_drivers} driver(s) "
            f"({total_orders // total_drivers} avg per driver)."
        )

    if high_priority > 0 and high_priority == total_orders:
        warnings.append(
            f"All {high_priority} orders are HIGH/CRITICAL priority — expect tight routing."
        )
    elif high_priority > total_orders * 0.5:
        warnings.append(
            f"{high_priority} of {total_orders} orders are HIGH/CRITICAL priority."
        )

    if with_windows > 0 and total_drivers > 0 and with_windows > total_drivers * 8:
        warnings.append(
            f"{with_windows} orders have time windows — OR-Tools may leave some unassigned."
        )

    # Initial confidence: penalise 0.1 per warning, floor at 0.3
    confidence = max(0.3, 1.0 - len(warnings) * 0.1)

    log = {
        "step": "analyze",
        "role": "tool",
        "content": (
            f"Pre-planning analysis complete. {len(warnings)} warning(s) identified. "
            f"Initial confidence: {confidence:.2f}. "
            + (" | ".join(warnings) if warnings else "All clear.")
        ),
    }
    return {**state, "warnings": warnings, "confidence_score": confidence, "logs": state["logs"] + [log]}


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
    warnings = state.get("warnings", [])
    current_confidence = state.get("confidence_score", 1.0)

    total = plan.get("total_orders", 0)
    assigned = plan.get("assigned_orders", 0)
    unassigned = total - assigned
    coverage_pct = (assigned / total * 100) if total else 100

    # Refine confidence based on actual plan outcome
    coverage_penalty = (1 - coverage_pct / 100) * 0.5
    refined_confidence = max(0.1, current_confidence - coverage_penalty)

    prompt = (
        "You are a fleet dispatch AI assistant. Analyse the routing plan below and respond with:\n"
        "1. SUMMARY: 2-3 concise professional sentences for a dispatcher.\n"
        "2. REASONING:\n"
        "   - Step 1: <one line about order volume vs driver capacity>\n"
        "   - Step 2: <one line about priority handling>\n"
        "   - Step 3: <one line about time-window coverage>\n"
        "   - Step 4: <one line about confidence assessment>\n\n"
        f"Date: {ctx.get('plan_date')}\n"
        f"Orders: {total} total, {assigned} assigned, {unassigned} unassigned\n"
        f"Routes: {plan.get('total_routes', 0)} drivers\n"
        f"High/Critical priority: {ctx.get('high_priority_orders', 0)}\n"
        f"Orders with time windows: {ctx.get('orders_with_time_windows', 0)}\n"
        f"Pre-planning warnings: {'; '.join(warnings) if warnings else 'None'}\n"
        f"Coverage: {coverage_pct:.0f}%\n"
    )

    reasoning_steps: list[str] = []
    explanation = ""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content

        # Parse SUMMARY and REASONING sections
        if "SUMMARY:" in raw and "REASONING:" in raw:
            parts = raw.split("REASONING:", 1)
            summary_block = parts[0].replace("SUMMARY:", "").strip()
            reasoning_block = parts[1].strip()
            explanation = summary_block
            for line in reasoning_block.splitlines():
                line = line.strip()
                if line.startswith("- Step"):
                    step_text = line.split(":", 1)[-1].strip() if ":" in line else line
                    if step_text:
                        reasoning_steps.append(step_text)
        else:
            explanation = raw
    except Exception as exc:
        explanation = (
            f"Plan generated: {assigned} orders assigned to "
            f"{plan.get('total_routes', 0)} drivers. (LLM error: {exc})"
        )

    log = {"step": "explain", "role": "llm", "content": explanation}
    return {
        **state,
        "explanation": explanation,
        "reasoning_steps": reasoning_steps,
        "confidence_score": refined_confidence,
        "logs": state["logs"] + [log],
    }


# ─── Graph builder ────────────────────────────────────────────────────────────

def _build_graph():
    wf = StateGraph(AgentState)
    wf.add_node("fetch_context", _node_fetch_context)
    wf.add_node("analyze", _node_analyze)
    wf.add_node("call_optimizer", _node_call_optimizer)
    wf.add_node("explain", _node_explain)
    wf.set_entry_point("fetch_context")
    wf.add_edge("fetch_context", "analyze")
    wf.add_edge("analyze", "call_optimizer")
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
