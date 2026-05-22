"""
ExplainAgent — Phase 3 (parallel).

Generates a human-readable summary and structured reasoning steps for the
dispatcher. Improved over the legacy explain node — LLM now receives actual
route distances, zone risk data, and session hints.

Falls back to a template summary if no LLM is configured.
"""
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class ExplainAgent:
    name = "ExplainAgent"
    phase = 3
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        plan = ctx["plan_result"]
        llm = ctx["llm"]

        total = plan.get("total_orders", 0)
        assigned = plan.get("assigned_orders", 0)
        routes = plan.get("total_routes", 0)
        total_km = plan.get("total_distance_km", 0)
        est_min = plan.get("est_duration_min", 0)
        dropped = total - assigned
        coverage_pct = (assigned / total * 100) if total else 100

        high_priority = sum(
            1 for o in ctx.get("orders", [])
            if getattr(o, "priority", "NORMAL") in ("HIGH", "CRITICAL")
        )
        with_windows = sum(1 for o in ctx.get("orders", []) if getattr(o, "time_window_start", None))

        forecast = ctx.get("forecast", {})
        high_risk_zones = forecast.get("high_risk_zones", [])
        constraint_warnings = ctx.get("constraint_warnings", [])
        session_hints = ctx.get("session_hints", [])

        if llm is None:
            explanation, reasoning_steps = self._template_summary(
                total, assigned, routes, total_km, est_min, dropped
            )
        else:
            explanation, reasoning_steps = self._llm_summary(
                llm=llm,
                plan_date=str(ctx["plan_date"]),
                total=total,
                assigned=assigned,
                routes=routes,
                total_km=total_km,
                est_min=est_min,
                high_priority=high_priority,
                with_windows=with_windows,
                high_risk_zones=high_risk_zones,
                constraint_warnings=constraint_warnings,
                session_hints=session_hints,
                forecast_summary=forecast.get("summary", ""),
            )

        ctx["explanation"] = explanation
        ctx["reasoning_steps"] = reasoning_steps

        elapsed = int((time.monotonic() - t0) * 1000)
        log_entry = {"step": self.name, "role": "llm", "content": explanation}
        ctx["logs"].append(log_entry)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output={"explanation": explanation, "reasoning_steps": reasoning_steps},
            warnings=[],
            elapsed_ms=elapsed,
            log_entry=log_entry,
        )

    # ── Template fallback (no LLM) ─────────────────────────────────────────

    def _template_summary(
        self, total: int, assigned: int, routes: int,
        total_km: float, est_min: int, dropped: int,
    ) -> tuple[str, list[str]]:
        hrs = est_min // 60
        mins = est_min % 60
        dur_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"
        drop_str = f" {dropped} order(s) could not be assigned." if dropped else ""
        explanation = (
            f"Plan generated: {assigned} of {total} orders assigned across "
            f"{routes} routes. Total distance: {total_km:.1f} km, "
            f"estimated duration: {dur_str}.{drop_str}"
        )
        return explanation, []

    # ── LLM summary ────────────────────────────────────────────────────────

    def _llm_summary(
        self, *, llm, plan_date: str, total: int, assigned: int,
        routes: int, total_km: float, est_min: int, high_priority: int,
        with_windows: int, high_risk_zones: list[str],
        constraint_warnings: list[str], session_hints: list[str],
        forecast_summary: str,
    ) -> tuple[str, list[str]]:
        hrs = est_min // 60
        mins = est_min % 60
        dur_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"

        hints_block = ""
        if session_hints:
            hints_block = f"\nDispatcher hints applied: {'; '.join(session_hints)}"

        risk_block = ""
        if high_risk_zones:
            risk_block = f"\nHigh-risk zones today: {', '.join(high_risk_zones)} (historically low on-time rate)."

        constraint_block = ""
        if constraint_warnings:
            constraint_block = f"\nConstraint notes: {'; '.join(constraint_warnings)}"

        forecast_block = f"\nForecast context: {forecast_summary}" if forecast_summary else ""

        prompt = (
            "You are a fleet dispatch AI assistant. Analyse the routing plan and respond with:\n"
            "1. SUMMARY: 2-3 concise professional sentences for a dispatcher.\n"
            "2. REASONING:\n"
            "   - Step 1: <one line about order volume vs driver capacity>\n"
            "   - Step 2: <one line about priority and time-window coverage>\n"
            "   - Step 3: <one line about route efficiency — total distance, duration>\n"
            "   - Step 4: <one line about risk factors or notable patterns>\n\n"
            f"Date: {plan_date}\n"
            f"Orders: {total} total, {assigned} assigned, {total - assigned} unassigned\n"
            f"Routes: {routes} drivers\n"
            f"Total distance: {total_km:.1f} km | Est. duration: {dur_str}\n"
            f"High/Critical priority: {high_priority}\n"
            f"Orders with time windows: {with_windows}\n"
            f"Coverage: {(assigned / total * 100) if total else 100:.0f}%"
            f"{forecast_block}{risk_block}{hints_block}{constraint_block}"
        )

        explanation = ""
        reasoning_steps: list[str] = []
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content
            if "SUMMARY:" in raw and "REASONING:" in raw:
                parts = raw.split("REASONING:", 1)
                explanation = parts[0].replace("SUMMARY:", "").strip()
                for line in parts[1].splitlines():
                    line = line.strip()
                    if line.startswith("- Step"):
                        step_text = line.split(":", 1)[-1].strip() if ":" in line else line
                        if step_text:
                            reasoning_steps.append(step_text)
            else:
                explanation = raw
        except Exception as exc:
            explanation, _ = self._template_summary(
                total, assigned, routes, total_km, est_min, total - assigned
            )
            explanation += f" (LLM error: {exc})"

        return explanation, reasoning_steps
