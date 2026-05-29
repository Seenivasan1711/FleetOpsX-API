"""
Planning execution runner — AI-1 E1 + E6.

Orchestrates the 3-phase agent pipeline:
  Phase 1 (data collection) → Phase 2 (planning) → Phase 3 (reasoning)
  → Final aggregator

Execution model:
  Phase 1 and Phase 3 run sequentially (parallel in E7 via asyncio.gather).
  Phase 2 is always sequential (each agent depends on the previous).

E6 additions:
  - PlanningRun row created at start (separate DB conn — commits independently)
  - Checkpoint appended after every agent completes
  - Failure classification: transient → surface for Celery retry; blocker → BLOCKED_WAITING_USER
  - resume_run(): re-dispatch with same params from last checkpoint
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
    hints = session_hints or []

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
        session_hints=hints,
    )

    # ── E6: create PlanningRun tracking row (separate conn — non-blocking) ────
    _create_run(run_id, tenant_id, plan_date, session_id, hints)

    # ── E4: load instructions + approved learning patterns before Phase 1 ─────
    ctx["instructions"] = _load_instructions(db, tenant_id)
    ctx["learning_patterns"] = _load_learning_patterns(db, tenant_id)

    # ── E5: load carry-forward notes for today (from yesterday's dropped orders)
    ctx["carry_forward_orders"] = _load_carry_forward_orders(db, tenant_id, plan_date)

    # ── Phase 1: data collection ──────────────────────────────────────────────
    logger.info("runner[%s] Phase 1 starting (%d agents)", run_id[:8], len(PHASE_1_AGENTS))
    _run_phase(PHASE_1_AGENTS, ctx, phase=1, abort_on_failure=False)

    # ── Phase 2: planning (sequential, abort on ORTools failure) ─────────────
    logger.info("runner[%s] Phase 2 starting (%d agents)", run_id[:8], len(PHASE_2_AGENTS))
    _run_phase(PHASE_2_AGENTS, ctx, phase=2, abort_on_failure=True)

    if not ctx["plan_result"]:
        _fail_run(run_id, {
            "agent_name": "ORToolsOptimizerAgent", "phase": 2,
            "error_type": "OptimizerFailure",
            "message": "Optimizer failed — no plan generated.",
            "is_transient": False,
        })
        return _empty_result(plan_date, reason="Optimizer failed — no plan generated.")

    # ── Phase 3: reasoning (parallel in E7, sequential for now) ──────────────
    logger.info("runner[%s] Phase 3 starting (%d agents)", run_id[:8], len(PHASE_3_AGENTS))
    _run_phase(PHASE_3_AGENTS, ctx, phase=3, abort_on_failure=False)

    # ── Aggregator ─────────────────────────────────────────────────────────────
    result = _aggregate(ctx, run_id)
    _persist_savings(ctx, db)
    _persist_agent_logs(ctx, db)
    _complete_run(run_id)

    logger.info(
        "runner[%s] complete — %d/%d orders, confidence=%.2f",
        run_id[:8],
        result.get("assigned_orders", 0),
        result.get("total_orders", 0),
        result.get("confidence_score", 0),
    )
    return result


def resume_run(*, db: Session, run_id: str, tenant_id: str) -> dict[str, Any]:
    """
    Resume a FAILED or BLOCKED_WAITING_USER run from the start.

    Loads the original call params from PlanningRun.params and re-dispatches
    via the Celery task so the retry path handles transient failure logic.
    Returns the new run_id.
    """
    from uuid import UUID as _UUID
    from sqlalchemy import select
    from app.models.planning_run import PlanningRun

    row = db.execute(
        select(PlanningRun).where(
            PlanningRun.id == _UUID(run_id),
            PlanningRun.tenant_id == _UUID(tenant_id),
        )
    ).scalar_one_or_none()

    if not row:
        raise ValueError(f"PlanningRun {run_id} not found")
    if row.status not in ("FAILED", "BLOCKED_WAITING_USER"):
        raise ValueError(f"Run {run_id} has status {row.status} — only FAILED/BLOCKED runs can be resumed")

    params = row.params or {}
    new_run_id = str(uuid.uuid4())

    from app.workers.tasks import run_planning_task
    run_planning_task.apply_async(
        kwargs={
            "tenant_id": params.get("tenant_id", tenant_id),
            "plan_date_str": params.get("plan_date", str(row.plan_date)),
            "session_id": params.get("session_id", ""),
            "run_id": new_run_id,
            "session_hints": params.get("session_hints", []),
        }
    )
    return {"run_id": new_run_id, "resumed_from": run_id, "status": "IN_PROGRESS"}


# ─── Phase executor ────────────────────────────────────────────────────────────

_PHASE_START_PCT = {1: 0.0,  2: 35.0, 3: 80.0}
_PHASE_WEIGHT_PCT = {1: 35.0, 2: 45.0, 3: 20.0}


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
    E6: checkpoints written after every agent; failure classified on abort.
    E7: agent_started / agent_completed events published to Redis.
    """
    from app.planners.event_publisher import publish_event

    run_id = ctx.get("run_id", "")
    n = len(agents)
    start_pct = _PHASE_START_PCT.get(phase, 0.0)
    weight_pct = _PHASE_WEIGHT_PCT.get(phase, 10.0)

    publish_event(run_id, "phase_started", {"phase": phase, "agent_count": n})

    for i, agent in enumerate(agents):
        t0 = time.monotonic()
        logger.info("runner Phase %d → %s starting", phase, agent.name)
        publish_event(run_id, "agent_started", {
            "agent_name": agent.name,
            "phase": phase,
            "progress_pct": round(start_pct + i / n * weight_pct, 1),
        })
        _update_run_agent(run_id, phase, agent.name)

        raw_exc: Exception | None = None
        try:
            result: AgentResult = agent.run(ctx)
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.exception("runner Phase %d → %s raised unexpectedly: %s", phase, agent.name, exc)
            raw_exc = exc
            result = AgentResult(
                agent_name=agent.name,
                status="failed",
                output={},
                warnings=[str(exc)],
                elapsed_ms=elapsed,
                log_entry={"step": agent.name, "role": "tool", "content": f"UNHANDLED: {exc}"},
            )

        ctx["agent_outputs"][agent.name] = result
        progress_pct = round(start_pct + (i + 1) / n * weight_pct, 1)
        _checkpoint_agent(run_id, result, phase, progress_pct)
        publish_event(run_id, "agent_completed", {
            "agent_name": result["agent_name"],
            "phase": phase,
            "status": result["status"],
            "elapsed_ms": result["elapsed_ms"],
            "output_preview": _preview(result["output"]),
            "warnings": result.get("warnings", []),
            "progress_pct": progress_pct,
        })

        logger.info(
            "runner Phase %d → %s %s (%dms)",
            phase, agent.name, result["status"], result["elapsed_ms"],
        )

        if result["status"] == "failed" and abort_on_failure:
            logger.error("runner Phase %d aborted after %s failure", phase, agent.name)
            from app.planners.failure_classifier import classify_failure
            failure_type = classify_failure(raw_exc) if raw_exc else "blocker"
            _fail_run(run_id, {
                "agent_name": agent.name,
                "phase": phase,
                "error_type": type(raw_exc).__name__ if raw_exc else "AgentFailure",
                "message": str(raw_exc) if raw_exc else result["warnings"][0] if result["warnings"] else "Agent returned failed status",
                "is_transient": failure_type == "transient",
            })
            if raw_exc and failure_type == "transient":
                raise raw_exc  # bubble up so Celery task can retry
            break

    publish_event(run_id, "phase_completed", {"phase": phase})


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


# ─── E4 loaders ───────────────────────────────────────────────────────────────

def _load_instructions(db: Session, tenant_id: str) -> list[str]:
    """Return rule_text for all active planning instructions, ordered by priority."""
    try:
        from uuid import UUID
        from sqlalchemy import select
        from app.models.planning_instruction import PlanningInstruction

        rows = db.execute(
            select(PlanningInstruction.rule_text)
            .where(
                PlanningInstruction.tenant_id == UUID(tenant_id),
                PlanningInstruction.is_active == True,
            )
            .order_by(PlanningInstruction.priority, PlanningInstruction.created_at)
        ).scalars().all()
        return list(rows)
    except Exception as exc:
        logger.warning("runner: failed to load planning instructions: %s", exc)
        return []


def _load_learning_patterns(db: Session, tenant_id: str) -> list[dict]:
    """Return APPROVED learning patterns as plain dicts for ctx injection."""
    try:
        from uuid import UUID
        from sqlalchemy import select
        from app.models.planning_learning import PlanningLearning

        rows = db.execute(
            select(PlanningLearning)
            .where(
                PlanningLearning.tenant_id == UUID(tenant_id),
                PlanningLearning.status == "APPROVED",
            )
            .order_by(PlanningLearning.created_at.desc())
        ).scalars().all()
        return [
            {
                "pattern_type": r.pattern_type,
                "pattern_text": r.pattern_text,
                "trigger_conditions": r.trigger_conditions,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("runner: failed to load learning patterns: %s", exc)
        return []


# ─── E6 run tracking (separate DB connections — commits are independent) ───────

def _create_run(run_id: str, tenant_id: str, plan_date, session_id: str, hints: list[str]) -> None:
    if not run_id:
        return
    try:
        from datetime import datetime
        from uuid import UUID as _UUID
        from app.core.db import SessionLocal
        from app.models.planning_run import PlanningRun
        from app.planners.event_publisher import publish_event

        db2 = SessionLocal()
        try:
            db2.add(PlanningRun(
                id=_UUID(run_id),
                tenant_id=_UUID(tenant_id),
                session_id=_UUID(session_id) if session_id else None,
                plan_date=plan_date,
                status="IN_PROGRESS",
                current_phase=0,
                checkpoints=[],
                params={
                    "tenant_id": tenant_id,
                    "plan_date": str(plan_date),
                    "session_id": session_id,
                    "session_hints": hints,
                },
                started_at=datetime.utcnow(),
            ))
            db2.commit()
        finally:
            db2.close()

        publish_event(run_id, "run_started", {
            "tenant_id": tenant_id,
            "plan_date": str(plan_date),
            "session_id": session_id,
        })
    except Exception as exc:
        logger.debug("E6 _create_run failed (non-fatal): %s", exc)


def _update_run_agent(run_id: str, phase: int, agent_name: str) -> None:
    if not run_id:
        return
    try:
        from uuid import UUID as _UUID
        from app.core.db import SessionLocal
        from app.models.planning_run import PlanningRun

        db2 = SessionLocal()
        try:
            run = db2.get(PlanningRun, _UUID(run_id))
            if run:
                run.current_phase = phase
                run.current_agent = agent_name
                db2.commit()
        finally:
            db2.close()
    except Exception as exc:
        logger.debug("E6 _update_run_agent failed (non-fatal): %s", exc)


def _checkpoint_agent(run_id: str, result: AgentResult, phase: int, progress_pct: float = 0.0) -> None:
    if not run_id:
        return
    try:
        from datetime import datetime
        from uuid import UUID as _UUID
        from app.core.db import SessionLocal
        from app.models.planning_run import PlanningRun

        db2 = SessionLocal()
        try:
            run = db2.get(PlanningRun, _UUID(run_id))
            if run:
                checkpoints = list(run.checkpoints or [])
                checkpoints.append({
                    "agent_name": result["agent_name"],
                    "phase": phase,
                    "status": result["status"],
                    "elapsed_ms": result["elapsed_ms"],
                    "output_preview": _preview(result["output"]),
                    "warnings": result.get("warnings", []),
                    "progress_pct": progress_pct,
                    "completed_at": datetime.utcnow().isoformat(),
                })
                run.checkpoints = checkpoints
                run.current_agent = result["agent_name"]
                db2.commit()
        finally:
            db2.close()
    except Exception as exc:
        logger.debug("E6 _checkpoint_agent failed (non-fatal): %s", exc)


def _complete_run(run_id: str) -> None:
    if not run_id:
        return
    try:
        from datetime import datetime
        from uuid import UUID as _UUID
        from app.core.db import SessionLocal
        from app.models.planning_run import PlanningRun
        from app.planners.event_publisher import publish_event

        db2 = SessionLocal()
        try:
            run = db2.get(PlanningRun, _UUID(run_id))
            if run:
                run.status = "COMPLETED"
                run.completed_at = datetime.utcnow()
                db2.commit()
        finally:
            db2.close()

        publish_event(run_id, "run_completed", {"progress_pct": 100.0})
    except Exception as exc:
        logger.debug("E6 _complete_run failed (non-fatal): %s", exc)


def _fail_run(run_id: str, error_info: dict) -> None:
    if not run_id:
        return
    try:
        from datetime import datetime
        from uuid import UUID as _UUID
        from app.core.db import SessionLocal
        from app.models.planning_run import PlanningRun
        from app.planners.event_publisher import publish_event

        new_status = "BLOCKED_WAITING_USER" if not error_info.get("is_transient") else "FAILED"
        db2 = SessionLocal()
        try:
            run = db2.get(PlanningRun, _UUID(run_id))
            if run:
                run.status = new_status
                run.error_info = error_info
                run.completed_at = datetime.utcnow()
                db2.commit()
        finally:
            db2.close()

        publish_event(run_id, "run_failed", {
            "status": new_status,
            "error_type": error_info.get("error_type"),
            "message": error_info.get("message"),
            "is_transient": error_info.get("is_transient", False),
        })
    except Exception as exc:
        logger.debug("E6 _fail_run failed (non-fatal): %s", exc)


def _load_carry_forward_orders(db: Session, tenant_id: str, plan_date) -> list[dict]:
    """Load PENDING carry-forward notes targeted at plan_date (yesterday's dropped orders)."""
    try:
        from uuid import UUID
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        from app.models.carry_forward_note import CarryForwardNote

        rows = db.execute(
            select(CarryForwardNote)
            .where(
                CarryForwardNote.tenant_id == UUID(tenant_id),
                CarryForwardNote.to_date == plan_date,
                CarryForwardNote.status == "PENDING",
            )
            .options(joinedload(CarryForwardNote.suggested_driver))
        ).scalars().all()

        result = []
        for r in rows:
            driver_name = None
            if r.suggested_driver:
                driver_name = getattr(r.suggested_driver, "full_name", None)
            result.append({
                "order_id": str(r.order_id),
                "from_date": str(r.from_date),
                "to_date": str(r.to_date),
                "suggested_driver_id": str(r.suggested_driver_id) if r.suggested_driver_id else None,
                "suggested_driver_name": driver_name,
                "context_note": r.context_note,
            })
        return result
    except Exception as exc:
        logger.warning("runner: failed to load carry-forward orders: %s", exc)
        return []


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
