"""
RiskScorerAgent — Phase 3 (parallel).

Computes a confidence score (0.0–1.0) from multiple signals:
  - Order coverage ratio (assigned / total)
  - High-priority order coverage
  - Time window satisfaction
  - Number of constraint warnings (E4)
  - Forecast vs actual order count delta
  - Existing warning count from Phase 2

Replaces and improves the confidence scoring in the legacy _node_analyze.
"""
from __future__ import annotations

import logging
import time

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)

_FLOOR = 0.1
_CEILING = 1.0


class RiskScorerAgent:
    name = "RiskScorerAgent"
    phase = 3
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        plan = ctx["plan_result"]
        orders = ctx.get("orders", [])
        forecast = ctx.get("forecast", {})
        constraint_warnings = ctx.get("constraint_warnings", [])

        total = plan.get("total_orders", 0) or len(orders)
        assigned = plan.get("assigned_orders", 0)
        score = _CEILING
        signals: list[str] = []

        # Signal 1: coverage ratio
        if total > 0:
            coverage = assigned / total
            if coverage < 1.0:
                penalty = (1 - coverage) * 0.4
                score -= penalty
                signals.append(f"Coverage {coverage * 100:.0f}% (−{penalty:.2f})")

        # Signal 2: high-priority orders dropped
        high_p_orders = [o for o in orders if getattr(o, "priority", "NORMAL") in ("HIGH", "CRITICAL")]
        if high_p_orders and total > 0:
            assigned_ids = {a.get("order_id") for a in plan.get("assignments", [])}
            dropped_high_p = sum(
                1 for o in high_p_orders if str(o.id) not in assigned_ids
            )
            if dropped_high_p > 0:
                penalty = min(0.2, dropped_high_p * 0.05)
                score -= penalty
                signals.append(f"{dropped_high_p} high-priority order(s) dropped (−{penalty:.2f})")

        # Signal 3: time-window orders
        tw_orders = [o for o in orders if getattr(o, "time_window_start", None)]
        if len(tw_orders) > 10:
            penalty = 0.05
            score -= penalty
            signals.append(f"{len(tw_orders)} time-window orders — tight routing (−{penalty:.2f})")

        # Signal 4: constraint warnings (E4 — zero until ConstraintValidatorAgent is built)
        if constraint_warnings:
            penalty = min(0.15, len(constraint_warnings) * 0.05)
            score -= penalty
            signals.append(f"{len(constraint_warnings)} instruction warning(s) (−{penalty:.2f})")

        # Signal 5: forecast vs actual
        expected = forecast.get("expected_order_count", 0)
        if expected > 0 and total > 0:
            delta_ratio = abs(total - expected) / expected
            if delta_ratio > 0.3:
                penalty = 0.05
                score -= penalty
                signals.append(f"Actual orders deviate {delta_ratio * 100:.0f}% from forecast (−{penalty:.2f})")

        score = round(max(_FLOOR, min(_CEILING, score)), 3)
        ctx["confidence_score"] = score

        elapsed = int((time.monotonic() - t0) * 1000)
        summary = f"Confidence: {score:.0%}. " + (
            "Signals: " + " | ".join(signals) if signals else "All clear."
        )
        log_entry = {"step": self.name, "role": "tool", "content": summary}
        ctx["logs"].append(log_entry)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output={"confidence_score": score, "signals": signals},
            warnings=[],
            elapsed_ms=elapsed,
            log_entry=log_entry,
        )
