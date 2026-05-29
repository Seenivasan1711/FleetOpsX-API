"""
LearningUpdaterAgent — Phase 3 (parallel).

Detects recurring planning patterns from this run's results and writes
PENDING_APPROVAL rows to planning_learning. Dispatchers must explicitly
approve before patterns influence future runs — never applied silently.

Patterns detected:
  high_drop_rate     — >25% of orders unassigned consistently
  zone_concentration — many orders in same zone could use dedicated driver
  repeated_replan    — session required >2 rounds before confirmation
  constraint_conflict — planning instructions flagged warnings this run

De-duplication: if the same pattern_type already has a PENDING_APPROVAL
row created within the last 7 days, increments times_observed instead
of creating a duplicate.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from uuid import UUID

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)

_DEDUP_WINDOW_DAYS = 7
_DROP_RATE_THRESHOLD = 0.25   # 25%


class LearningUpdaterAgent:
    name = "LearningUpdaterAgent"
    phase = 3
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()

        detected: list[dict] = self._detect_patterns(ctx)
        persisted = 0

        if detected:
            try:
                persisted = self._persist_patterns(ctx, detected)
            except Exception as exc:
                logger.warning("%s: failed to persist learning patterns: %s", self.name, exc)

        elapsed = int((time.monotonic() - t0) * 1000)
        log_entry = {
            "step": self.name,
            "role": "tool",
            "content": f"Detected {len(detected)} pattern(s), persisted {persisted}.",
        }
        ctx["logs"].append(log_entry)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output={"patterns_detected": len(detected), "patterns_persisted": persisted},
            warnings=[],
            elapsed_ms=elapsed,
            log_entry=log_entry,
        )

    # ── Pattern detection ─────────────────────────────────────────────────────

    def _detect_patterns(self, ctx: AgentContext) -> list[dict]:
        patterns: list[dict] = []
        plan = ctx.get("plan_result", {})
        total = plan.get("total_orders", 0)
        assigned = plan.get("assigned_orders", 0)
        dropped = total - assigned
        constraint_warnings = ctx.get("constraint_warnings", [])

        # 1. High drop rate
        if total > 0 and dropped / total >= _DROP_RATE_THRESHOLD:
            pct = dropped / total * 100
            patterns.append({
                "pattern_type": "high_drop_rate",
                "pattern_text": (
                    f"{pct:.0f}% of orders could not be assigned ({dropped}/{total}). "
                    f"Consider adding driver capacity or reducing daily order volume."
                ),
                "trigger_conditions": {
                    "plan_date": str(ctx.get("plan_date")),
                    "drop_rate": round(dropped / total, 3),
                    "total_orders": total,
                    "assigned_orders": assigned,
                },
            })

        # 2. Zone concentration (many orders in same postal zone)
        zone_counts: dict[str, int] = {}
        for order in ctx.get("orders", []):
            zone = getattr(order, "delivery_postal_code", None) or getattr(order, "zone", None)
            if zone:
                zone_counts[zone] = zone_counts.get(zone, 0) + 1

        if zone_counts:
            top_zone, top_count = max(zone_counts.items(), key=lambda x: x[1])
            if total > 0 and top_count / total >= 0.4:
                patterns.append({
                    "pattern_type": "zone_concentration",
                    "pattern_text": (
                        f"Zone '{top_zone}' accounts for {top_count}/{total} orders ({top_count/total*100:.0f}%). "
                        f"A dedicated driver for this zone could improve efficiency."
                    ),
                    "trigger_conditions": {
                        "plan_date": str(ctx.get("plan_date")),
                        "top_zone": top_zone,
                        "top_zone_order_count": top_count,
                        "total_orders": total,
                    },
                })

        # 3. Repeated replan — session required multiple rounds
        session_id = ctx.get("session_id", "")
        if session_id:
            try:
                from sqlalchemy import func, select
                from app.models.route_plan import RoutePlan
                db = ctx.get("db")
                if db:
                    max_ver = db.execute(
                        select(func.max(RoutePlan.version_number)).where(
                            RoutePlan.session_id == UUID(session_id)
                        )
                    ).scalar() or 1
                    if max_ver >= 3:
                        patterns.append({
                            "pattern_type": "repeated_replan",
                            "pattern_text": (
                                f"This planning session required {max_ver} rounds. "
                                f"Consider adding planning instructions to reduce iteration."
                            ),
                            "trigger_conditions": {
                                "plan_date": str(ctx.get("plan_date")),
                                "session_id": session_id,
                                "rounds": max_ver,
                            },
                        })
            except Exception:
                pass

        # 4. Constraint conflicts
        if len(constraint_warnings) >= 2:
            patterns.append({
                "pattern_type": "constraint_conflict",
                "pattern_text": (
                    f"{len(constraint_warnings)} planning instruction(s) could not be fully satisfied. "
                    f"Review and update your instructions to match available resources."
                ),
                "trigger_conditions": {
                    "plan_date": str(ctx.get("plan_date")),
                    "warnings": constraint_warnings[:5],
                },
            })

        return patterns

    # ── Persistence ────────────────────────────────────────────────────────────

    def _persist_patterns(self, ctx: AgentContext, patterns: list[dict]) -> int:
        from uuid import UUID as _UUID
        from sqlalchemy import select, update as sa_update
        from app.models.planning_learning import PlanningLearning

        db = ctx["db"]
        tenant_uuid = _UUID(ctx["tenant_id"])
        dedup_cutoff = datetime.utcnow() - timedelta(days=_DEDUP_WINDOW_DAYS)
        persisted = 0

        for p in patterns:
            # Check for recent duplicate
            existing = db.execute(
                select(PlanningLearning).where(
                    PlanningLearning.tenant_id == tenant_uuid,
                    PlanningLearning.pattern_type == p["pattern_type"],
                    PlanningLearning.status == "PENDING_APPROVAL",
                    PlanningLearning.created_at >= dedup_cutoff,
                )
            ).scalar_one_or_none()

            if existing:
                existing.times_observed += 1
            else:
                db.add(PlanningLearning(
                    tenant_id=tenant_uuid,
                    pattern_type=p["pattern_type"],
                    pattern_text=p["pattern_text"],
                    trigger_conditions=p.get("trigger_conditions"),
                    times_observed=1,
                    status="PENDING_APPROVAL",
                ))
                persisted += 1

        db.commit()
        return persisted
