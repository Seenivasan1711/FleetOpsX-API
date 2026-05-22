"""
Planning execution runner — AI-1 E1.

Orchestrates the 3-phase agent pipeline:
  Phase 1 (data collection) → Phase 2 (planning) → Phase 3 (reasoning)
  → Final aggregator

Execution model for E1:
  Phase 1 and Phase 3 agents run sequentially now, structured so they can
  be switched to Celery group (E6) or asyncio.gather (E7) with minimal changes.
  Phase 2 is always sequential (each agent depends on the previous).

Failure handling (full version in E6):
  - Agent failures in Phase 1: log and continue (partial data is better than no plan)
  - Agent failures in Phase 2 (ORTools): raises — plan cannot proceed without a route result
  - Agent failures in Phase 3: log and continue (plan is still usable without full reasoning)
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.planners.context import AgentContext, AgentResult, make_context
from app.planners.agent_protocol import PlanningAgent

logger = logging.getLogger(__name__)


def run_planning(
    *,
    db: Session,
    tenant_id: str,
    plan_date: date,
    session_id: str = "",
    run_id: str = "",
    session_hints: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute the full 3-phase planning pipeline and return a plan result dict.

    The returned dict has the same shape as the existing PlanningService.plan_day()
    contract so existing API routes need no changes.
    """
    from app.planners.registry import PHASE_1_AGENTS, PHASE_2_AGENTS, PHASE_3_AGENTS
    from app.core.llm_factory import get_llm_for_tenant

    run_id = run_id or str(uuid.uuid4())

    llm = None
    try:
        llm = get_llm_for_tenant(db=db, tenant_id=tenant_id)
    except ValueError:
        pass  # no LLM configured — agents degrade gracefully

    ctx = make_context(
        tenant_id=tenant_id,
        plan_date=plan_date,
        db=db,
        llm=llm,
        run_id=run_id,
        session_id=session_id,
        session_hints=session_hints or [],
    )

    # ── E4 hook: load instructions + learning patterns before Phase 1 ─────────
    # (implemented in E4 — these stay empty lists for now)

    # ── Phase 1: data collection ──────────────────────────────────────────────
    logger.info("runner[%s] Phase 1 starting (%d agents)", run_id[:8], len(PHASE_1_AGENTS))
    _run_phase(PHASE_1_AGENTS, ctx, phase=1, abort_on_failure=False)

    # ── Phase 2: planning (sequential, abort on ORTools failure) ─────────────
    logger.info("runner[%s] Phase 2 starting (%d agents)", run_id[:8], len(PHASE_2_AGENTS))
    _run_phase(PHASE_2_AGENTS, ctx, phase=2, abort_on_failure=True)

    if not ctx["plan_result"]:
        # ORTools failed and we aborted — return a safe empty result
        return _empty_result(plan_date, reason="Optimizer failed — no plan generated.")

    # ── Phase 3: reasoning (parallel in E7, sequential for now) ──────────────
    logger.info("runner[%s] Phase 3 starting (%d agents)", run_id[:8], len(PHASE_3_AGENTS))
    _run_phase(PHASE_3_AGENTS, ctx, phase=3, abort_on_failure=False)

    # ── Aggregator ─────────────────────────────────────────────────────────────
    result = _aggregate(ctx, run_id)
    _persist_savings(ctx, db)
    _persist_agent_logs(ctx, db)
    logger.info(
        "runner[%s] complete — %d/%d orders, confidence=%.2f",
        run_id[:8],
        result.get("assigned_orders", 0),
        result.get("total_orders", 0),
        result.get("confidence_score", 0),
    )
    return result


# ─── Phase executor ────────────────────────────────────────────────────────────

def _run_phase(
    agents: list[PlanningAgent],
    ctx: AgentContext,
    *,
    phase: int,
    abort_on_failure: bool,
) -> None:
    """
    Run agents for a phase. Agents mutate ctx directly and return AgentResult.

    abort_on_failure=True: if any agent returns status="failed", stop the phase.
    abort_on_failure=False: continue even if an agent fails (partial data).
    """
    for agent in agents:
        t0 = time.monotonic()
        logger.info("runner Phase %d → %s starting", phase, agent.name)
        try:
            result: AgentResult = agent.run(ctx)
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.exception("runner Phase %d → %s raised unexpectedly: %s", phase, agent.name, exc)
            result = AgentResult(
                agent_name=agent.name,
                status="failed",
                output={},
                warnings=[str(exc)],
                elapsed_ms=elapsed,
                log_entry={"step": agent.name, "role": "tool", "content": f"UNHANDLED: {exc}"},
            )

        ctx["agent_outputs"][agent.name] = result
        logger.info(
            "runner Phase %d → %s %s (%dms)",
            phase, agent.name, result["status"], result["elapsed_ms"],
        )

        if result["status"] == "failed" and abort_on_failure:
            logger.error(
                "runner Phase %d aborted after %s failure", phase, agent.name
            )
            break


# ─── Aggregator ────────────────────────────────────────────────────────────────

def _aggregate(ctx: AgentContext, run_id: str) -> dict[str, Any]:
    """Merge Phase 2+3 outputs into the final plan response dict."""
    plan = ctx["plan_result"]

    # Collect all warnings from all agents
    all_warnings: list[str] = list(ctx.get("constraint_warnings", []))
    for result in ctx["agent_outputs"].values():
        all_warnings.extend(result.get("warnings", []))

    return {
        # ── Core plan fields (from ORToolsOptimizerAgent) ──────────────────
        "plan_id": plan.get("plan_id"),
        "plan_date": plan.get("plan_date", str(ctx["plan_date"])),
        "status": plan.get("status", "DRAFT"),
        "plan_mode": plan.get("plan_mode", "balanced"),
        "total_orders": plan.get("total_orders", 0),
        "assigned_orders": plan.get("assigned_orders", 0),
        "total_routes": plan.get("total_routes", 0),
        "total_distance_km": plan.get("total_distance_km", 0),
        "est_duration_min": plan.get("est_duration_min", 0),
        "est_fuel_cost": plan.get("est_fuel_cost", 0),
        "assignments": plan.get("assignments", []),
        # ── AI fields (from Phase 3 agents) ────────────────────────────────
        "ai_summary": ctx.get("explanation", ""),
        "confidence_score": ctx.get("confidence_score", None),
        "reasoning_steps": ctx.get("reasoning_steps", []),
        "warnings": all_warnings,
        # ── E2: savings vs naive baseline ────────────────────────────────────
        "km_saved": ctx["baseline_result"].get("km_saved"),
        "hrs_saved": ctx["baseline_result"].get("hrs_saved"),
        "baseline_km": ctx["baseline_result"].get("baseline_km"),
        # ── Metadata ────────────────────────────────────────────────────────
        "planner": "ai1_runner",
        "run_id": run_id,
        "session_id": ctx.get("session_id", ""),
        # ── Agent pipeline outputs (for real-time UI in E7) ─────────────────
        "agent_pipeline": {
            name: {
                "status": r["status"],
                "elapsed_ms": r["elapsed_ms"],
                "warnings": r["warnings"],
                "output_preview": _preview(r["output"]),
            }
            for name, r in ctx["agent_outputs"].items()
        },
        # ── Carry-forward (populated in E5) ─────────────────────────────────
        "carry_forward_notes": ctx.get("carry_forward_notes", []),
        # ── Forecast context ─────────────────────────────────────────────────
        "forecast": {
            "summary": ctx["forecast"].get("summary", ""),
            "high_risk_zones": ctx["forecast"].get("high_risk_zones", []),
            "expected_order_count": ctx["forecast"].get("expected_order_count", 0),
        },
    }


def _preview(output: dict) -> str:
    """One-line preview of an agent's output for the agent_pipeline summary."""
    if not output:
        return ""
    keys = list(output.keys())[:3]
    parts = []
    for k in keys:
        v = output[k]
        if isinstance(v, (int, float)):
            parts.append(f"{k}={v}")
        elif isinstance(v, list):
            parts.append(f"{k}=[{len(v)}]")
        elif isinstance(v, str) and len(v) < 60:
            parts.append(f"{k}={v!r}")
    return ", ".join(parts)


# ─── Savings persistence (E2) ─────────────────────────────────────────────────

def _persist_savings(ctx: AgentContext, db: Session) -> None:
    """Write baseline_km, km_saved, hrs_saved back to the RoutePlan row."""
    try:
        baseline = ctx.get("baseline_result", {})
        if not baseline or baseline.get("km_saved") is None:
            return
        plan_id_str = ctx["plan_result"].get("plan_id")
        if not plan_id_str:
            return

        from uuid import UUID
        from sqlalchemy import update as sa_update
        from app.models.route_plan import RoutePlan

        db.execute(
            sa_update(RoutePlan)
            .where(RoutePlan.id == UUID(plan_id_str))
            .values(
                baseline_km=baseline.get("baseline_km"),
                baseline_hrs=baseline.get("baseline_hrs"),
                km_saved=baseline.get("km_saved"),
                hrs_saved=baseline.get("hrs_saved"),
            )
        )
        db.commit()
    except Exception as exc:
        logger.warning("runner: failed to persist savings: %s", exc)


# ─── AgentLog persistence ──────────────────────────────────────────────────────

def _persist_agent_logs(ctx: AgentContext, db: Session) -> None:
    """Write all agent log entries to the agent_logs table."""
    try:
        from app.models.agent_log import AgentLog
        plan_id_str = ctx["plan_result"].get("plan_id")
        from uuid import UUID
        plan_uuid = UUID(plan_id_str) if plan_id_str else None

        llm_provider = _resolve_provider(db, ctx["tenant_id"])

        for entry in ctx["logs"]:
            db.add(AgentLog(
                tenant_id=ctx["tenant_id"],
                plan_id=plan_uuid,
                step=entry.get("step", ""),
                role=entry.get("role", "tool"),
                content=entry.get("content", ""),
                llm_provider=llm_provider,
            ))
        db.commit()
    except Exception as exc:
        logger.warning("runner: failed to persist agent logs: %s", exc)


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


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _empty_result(plan_date: date, reason: str) -> dict[str, Any]:
    return {
        "plan_id": None,
        "plan_date": str(plan_date),
        "status": "FAILED",
        "plan_mode": "balanced",
        "total_orders": 0,
        "assigned_orders": 0,
        "total_routes": 0,
        "total_distance_km": 0,
        "est_duration_min": 0,
        "est_fuel_cost": 0,
        "assignments": [],
        "ai_summary": reason,
        "confidence_score": 0.0,
        "reasoning_steps": [],
        "warnings": [reason],
        "km_saved": None,
        "hrs_saved": None,
        "baseline_km": None,
        "planner": "ai1_runner",
        "run_id": "",
        "session_id": "",
        "agent_pipeline": {},
        "carry_forward_notes": [],
        "forecast": {},
    }
