import json
import logging
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.planners.cost_model import PLAN_MODES
from app.models.route_plan import RoutePlan, Route, RouteStop
from app.models.order import Order
from app.schemas.plan_options import PlanSummary, PlanOptionsResponse

logger = logging.getLogger(__name__)


# ─── Option generation ────────────────────────────────────────────────────────

def generate_options(db: Session, tenant_id: str, plan_date: date) -> PlanOptionsResponse:
    """
    Run OR-Tools for each plan mode (fastest / economical / balanced).
    Then enrich with a single LLM call that explains all three and recommends one.
    Returns real OR-Tools KPIs — LLM only explains, never invents numbers.
    """
    from app.planners.ortools_planner import ORToolsPlanner
    planner = ORToolsPlanner()

    raw: dict[str, dict] = {}
    for mode in PLAN_MODES:
        result = planner.plan_day(
            db=db,
            tenant_id=tenant_id,
            plan_date=plan_date,
            plan_mode=mode,
            commit_assignments=False,
        )
        if result.get("plan_id"):
            raw[mode] = result

    # LLM enrichment — single call covers all modes
    enrichments, recommendation = _enrich_with_llm(db, tenant_id, raw)

    summaries: list[PlanSummary] = []
    for mode in PLAN_MODES:
        r = raw.get(mode)
        if not r:
            continue
        ai = enrichments.get(mode, {})
        summaries.append(PlanSummary(
            mode=mode,
            plan_id=r["plan_id"],
            total_distance_km=r.get("total_distance_km", 0.0),
            est_duration_min=r.get("est_duration_min", 0),
            est_fuel_cost=r.get("est_fuel_cost", 0.0),
            orders_covered=r.get("assigned_orders", 0),
            total_orders=r.get("total_orders", 0),
            total_routes=r.get("total_routes", 0),
            ai_summary=ai.get("summary"),
            confidence_score=ai.get("confidence"),
            reasoning_steps=ai.get("reasoning", []),
            warnings=ai.get("warnings", []),
        ))

    # Cross-mode savings baseline: fastest distance as the "unoptimized" reference
    fastest_km = raw.get("fastest", {}).get("total_distance_km")

    return PlanOptionsResponse(
        plan_date=plan_date,
        options=summaries,
        recommendation=recommendation,
        naive_distance_km=fastest_km,
    )


def _enrich_with_llm(
    db: Session,
    tenant_id: str,
    raw: dict[str, dict],
) -> tuple[dict[str, dict], str | None]:
    """
    Single LLM call: explain all mode scenarios grounded in real OR-Tools data.
    Returns ({mode: ai_fields}, recommended_mode) — both empty/None if LLM unavailable.
    """
    if not raw:
        return {}, None

    try:
        from app.core.llm_factory import get_llm_for_tenant
        llm = get_llm_for_tenant(db, tenant_id)
    except Exception:
        return {}, None

    scenario_lines = []
    for mode, r in raw.items():
        assigned = r.get("assigned_orders", 0)
        total = r.get("total_orders", 0)
        coverage = round(assigned / max(total, 1) * 100)
        h, m = divmod(r.get("est_duration_min", 0), 60)
        scenario_lines.append(
            f"  {mode.upper()}:\n"
            f"    Distance: {r.get('total_distance_km', 0):.1f} km\n"
            f"    Duration: {h}h {m}m\n"
            f"    Fuel cost: ₹{r.get('est_fuel_cost', 0):.0f}\n"
            f"    Coverage: {coverage}% ({assigned}/{total} orders)\n"
            f"    Routes: {r.get('total_routes', 0)} drivers"
        )

    prompt = (
        "You are FleetOpsX AI analyzing REAL route optimization results computed by OR-Tools VRPTW solver.\n\n"
        "Scenarios for " + str(list(raw.keys())[0] and raw[list(raw.keys())[0]].get("plan_date", "today")) + ":\n\n"
        + "\n\n".join(scenario_lines)
        + "\n\nFor each scenario write:\n"
        "- summary: one sentence for a fleet dispatcher (be specific about the tradeoff)\n"
        "- confidence: 0.0–1.0 based on order coverage\n"
        "- reasoning: 2–3 concrete bullet points grounded in the numbers above\n"
        "- warnings: any operational concerns (empty list if none)\n\n"
        "Also choose which scenario a typical dispatcher should pick.\n\n"
        'Return ONLY valid JSON — no markdown:\n'
        '{"scenarios":[{"mode":"fastest","summary":"...","confidence":0.0,"reasoning":["..."],"warnings":[]},'
        '{"mode":"economical",...},{"mode":"balanced",...}],"recommendation":"balanced"}'
    )

    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        raw_text = response.content.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        data = json.loads(raw_text)
        enrichments = {s["mode"]: s for s in data.get("scenarios", [])}
        recommendation = data.get("recommendation")
        logger.info("LLM plan enrichment OK — recommendation: %s", recommendation)
        return enrichments, recommendation
    except Exception as exc:
        logger.warning("LLM plan enrichment failed (%s) — returning unenriched summaries", exc)
        return {}, None


# ─── Confirm ──────────────────────────────────────────────────────────────────

def confirm_plan(db: Session, tenant_id: str, plan_id: UUID, plan_date: date) -> dict | None:
    """
    Apply order assignments from the selected plan, mark it PUBLISHED,
    and CANCEL other DRAFT plans for the same date.
    Also writes a PlanHistory row so the history page reflects every dispatch.
    """
    from uuid import uuid4
    tid = UUID(tenant_id)

    plan = db.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.tenant_id == tid,
        )
    ).scalar_one_or_none()

    if plan is None:
        return None

    routes = db.execute(
        select(Route).where(Route.plan_id == plan_id, Route.tenant_id == tid)
    ).scalars().all()

    assignments = []
    for route in routes:
        stops = db.execute(
            select(RouteStop)
            .where(RouteStop.route_id == route.id, RouteStop.tenant_id == tid)
            .order_by(RouteStop.sequence)
        ).scalars().all()

        for stop in stops:
            order = db.get(Order, stop.order_id)
            if order:
                order.assigned_driver_id = route.driver_id
                order.status = "ASSIGNED"
                assignments.append({
                    "order_id": str(order.id),
                    "driver_id": str(route.driver_id),
                    "sequence": stop.sequence,
                })

    plan.status = "PUBLISHED"

    db.execute(
        update(RoutePlan)
        .where(
            RoutePlan.tenant_id == tid,
            RoutePlan.plan_date == plan_date,
            RoutePlan.id != plan_id,
            RoutePlan.status == "DRAFT",
        )
        .values(status="CANCELLED")
    )

    # Auto-write PlanHistory row
    try:
        from app.models.plan_history import PlanHistory
        db.add(PlanHistory(
            id=uuid4(),
            tenant_id=tid,
            plan_date=plan_date,
            scenario_type=plan.plan_mode or "balanced",
            total_routes=plan.total_routes or 0,
            total_orders=plan.total_orders or 0,
            assigned_orders=plan.assigned_orders or 0,
            source="or_tools",
        ))
    except Exception:
        pass

    db.commit()

    return {
        "plan_id": str(plan.id),
        "plan_date": str(plan_date),
        "status": "PUBLISHED",
        "total_orders": plan.total_orders,
        "assigned_orders": plan.assigned_orders,
        "total_routes": plan.total_routes,
        "assignments": assignments,
    }
