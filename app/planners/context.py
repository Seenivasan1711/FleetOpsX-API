"""
Planning agent shared context and result types — AI-1 E1.

AgentContext is passed through all 3 phases. Every agent reads from it
and writes its outputs back into the same dict (plain dict at runtime).

AgentResult is the per-agent return value used for logging and tracking.
"""
from __future__ import annotations

from datetime import date
from typing import Any, TypedDict


class AgentContext(TypedDict):
    # ── Identity ────────────────────────────────────────────────────────────
    tenant_id: str
    plan_date: date
    db: Any            # sqlalchemy Session — not serialised, stays in process
    llm: Any           # BaseChatModel | None
    run_id: str        # planning run identifier (MongoDB doc key in E6)
    session_id: str    # planning session identifier (E3)
    session_hints: list[str]   # accumulated dispatcher hints for this session

    # ── Pre-loaded cross-cutting config (loaded before Phase 1) ─────────────
    instructions: list[str]       # active rules from planning_instructions table (E4)
    learning_patterns: list[dict] # approved historical patterns (E4)
    carry_forward_orders: list[dict]  # deferred orders from previous day (E5)

    # ── Phase 1 outputs — data collection ───────────────────────────────────
    orders: list[Any]           # Order ORM objects for plan_date
    drivers: list[Any]          # Driver ORM objects available today
    vehicles: list[Any]         # Vehicle ORM objects active today
    driver_availability_3day: dict[str, dict]  # driver_id → {day0, day1, day2} (E5)
    forecast: dict[str, Any]    # DOW demand baseline from ForecastAgent

    # ── Phase 2 outputs — planning ──────────────────────────────────────────
    constraint_warnings: list[str]   # from ConstraintValidatorAgent (E4)
    plan_result: dict[str, Any]      # from ORToolsOptimizerAgent
    baseline_result: dict[str, Any]  # naive baseline km/hrs (E2)

    # ── Phase 3 outputs — reasoning ─────────────────────────────────────────
    explanation: str
    reasoning_steps: list[str]
    confidence_score: float
    warnings: list[str]
    carry_forward_notes: list[dict]  # dropped orders with driver suggestions (E5)

    # ── Tracking ────────────────────────────────────────────────────────────
    agent_outputs: dict[str, Any]   # keyed by agent.name → AgentResult
    logs: list[dict]                # all agent log entries for AgentLog persistence


class AgentResult(TypedDict):
    agent_name: str
    status: str          # "completed" | "failed" | "skipped"
    output: dict[str, Any]
    warnings: list[str]
    elapsed_ms: int
    log_entry: dict[str, Any]   # content to write to AgentLog table


def make_context(
    *,
    tenant_id: str,
    plan_date: date,
    db: Any,
    llm: Any = None,
    run_id: str = "",
    session_id: str = "",
    session_hints: list[str] | None = None,
) -> AgentContext:
    """Return a fully initialised AgentContext with safe defaults."""
    return AgentContext(
        tenant_id=tenant_id,
        plan_date=plan_date,
        db=db,
        llm=llm,
        run_id=run_id,
        session_id=session_id,
        session_hints=session_hints or [],
        instructions=[],
        learning_patterns=[],
        carry_forward_orders=[],
        orders=[],
        drivers=[],
        vehicles=[],
        driver_availability_3day={},
        forecast={},
        constraint_warnings=[],
        plan_result={},
        baseline_result={},
        explanation="",
        reasoning_steps=[],
        confidence_score=1.0,
        warnings=[],
        carry_forward_notes=[],
        agent_outputs={},
        logs=[],
    )
