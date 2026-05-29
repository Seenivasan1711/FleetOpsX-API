"""
ConstraintValidatorAgent — Phase 2 (sequential), runs before ORToolsOptimizerAgent.

Validates active planning instructions against today's plan context:
  - LLM path: sends instructions + context summary → LLM flags which rules can't be met
  - Template path (no LLM): heuristic checks (headcount, priority orders, capacity)

Also surfaces approved learning patterns as informational notes.

Outputs: ctx["constraint_warnings"] — list of warning strings passed to later agents
         and included in the final plan response.
"""
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class ConstraintValidatorAgent:
    name = "ConstraintValidatorAgent"
    phase = 2
    execution = "sequential"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        instructions = ctx.get("instructions", [])
        patterns = ctx.get("learning_patterns", [])

        warnings: list[str] = []
        notes: list[str] = []

        if not instructions and not patterns:
            elapsed = int((time.monotonic() - t0) * 1000)
            log_entry = {"step": self.name, "role": "tool", "content": "No instructions configured — skipped."}
            ctx["logs"].append(log_entry)
            ctx["constraint_warnings"] = []
            return AgentResult(
                agent_name=self.name,
                status="completed",
                output={"warnings": [], "notes": []},
                warnings=[],
                elapsed_ms=elapsed,
                log_entry=log_entry,
            )

        llm = ctx.get("llm")

        if llm and instructions:
            warnings = self._llm_validate(ctx, llm, instructions)
        elif instructions:
            warnings = self._template_validate(ctx, instructions)

        # Surface approved learning patterns as advisory notes
        for p in patterns:
            note = p.get("pattern_text", "")
            if note:
                notes.append(f"[Learning] {note}")

        ctx["constraint_warnings"] = warnings

        all_messages = warnings + notes
        elapsed = int((time.monotonic() - t0) * 1000)
        log_entry = {
            "step": self.name,
            "role": "tool",
            "content": (
                f"Validated {len(instructions)} instruction(s). "
                f"{len(warnings)} warning(s), {len(notes)} learning note(s)."
            ),
        }
        ctx["logs"].append(log_entry)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output={"warnings": warnings, "notes": notes},
            warnings=warnings,
            elapsed_ms=elapsed,
            log_entry=log_entry,
        )

    # ── LLM validation ────────────────────────────────────────────────────────

    def _llm_validate(self, ctx: AgentContext, llm, instructions: list[str]) -> list[str]:
        orders = ctx.get("orders", [])
        drivers = ctx.get("drivers", [])
        vehicles = ctx.get("vehicles", [])
        forecast = ctx.get("forecast", {})
        session_hints = ctx.get("session_hints", [])

        high_priority = sum(
            1 for o in orders if getattr(o, "priority", "NORMAL") in ("HIGH", "CRITICAL")
        )
        rules_block = "\n".join(f"{i+1}. {r}" for i, r in enumerate(instructions))
        hints_block = (
            f"\nDispatcher session hints: {'; '.join(session_hints)}" if session_hints else ""
        )

        carry_forward = ctx.get("carry_forward_orders", [])
        cf_block = ""
        if carry_forward:
            cf_lines = [
                f"    - Order {c['order_id'][:8]}... → {c.get('suggested_driver_name', 'unassigned')} "
                f"(from {c.get('from_date', '?')})"
                for c in carry_forward[:5]
            ]
            cf_block = f"\n  Carry-forward from previous day: {len(carry_forward)} order(s)\n" + "\n".join(cf_lines)

        prompt = (
            "You are a fleet planning compliance checker.\n"
            "Given the planning rules below and the current fleet context, "
            "identify which rules CANNOT be fully satisfied today. "
            "For each violation, output exactly one line starting with 'WARN:' "
            "followed by a concise explanation (under 20 words). "
            "If all rules can be satisfied, output only: OK\n\n"
            f"PLANNING RULES:\n{rules_block}\n\n"
            f"FLEET CONTEXT:\n"
            f"  Orders: {len(orders)} total, {high_priority} high/critical priority\n"
            f"  Active drivers: {len(drivers)}\n"
            f"  Active vehicles: {len(vehicles)}\n"
            f"  Forecast: {forecast.get('summary', 'N/A')}"
            f"{cf_block}"
            f"{hints_block}"
        )

        warnings: list[str] = []
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if raw != "OK":
                for line in raw.splitlines():
                    line = line.strip()
                    if line.upper().startswith("WARN:"):
                        text = line[5:].strip()
                        if text:
                            warnings.append(text)
        except Exception as exc:
            logger.warning("%s LLM validation error: %s — falling back to template checks", self.name, exc)
            warnings = self._template_validate(ctx, instructions)

        return warnings

    # ── Template validation (no LLM) ─────────────────────────────────────────

    def _template_validate(self, ctx: AgentContext, instructions: list[str]) -> list[str]:
        warnings: list[str] = []
        orders = ctx.get("orders", [])
        drivers = ctx.get("drivers", [])
        vehicles = ctx.get("vehicles", [])
        high_priority = sum(
            1 for o in orders if getattr(o, "priority", "NORMAL") in ("HIGH", "CRITICAL")
        )

        for rule in instructions:
            rule_lower = rule.lower()

            if any(k in rule_lower for k in ("high priority", "critical first", "priority first")):
                if high_priority == 0:
                    warnings.append(
                        f"Rule '{rule[:60]}' references priority orders but none exist today."
                    )

            if any(k in rule_lower for k in ("all orders", "100%", "full coverage")):
                if len(drivers) == 0:
                    warnings.append(
                        f"Rule '{rule[:60]}' requires full coverage but no drivers are available."
                    )

            if "dedicated driver" in rule_lower or "same driver" in rule_lower:
                if len(drivers) < 2:
                    warnings.append(
                        f"Rule '{rule[:60]}' requires dedicated drivers but only {len(drivers)} available."
                    )

        return warnings
