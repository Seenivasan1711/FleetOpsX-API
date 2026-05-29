"""
CarryForwardAgent — Phase 3 (parallel).

For every order dropped from today's plan:
  1. Looks for an available driver on Day+1 then Day+2 via driver_availability_3day.
  2. Creates a CarryForwardNote in DB (PENDING) with a human-readable context_note.
  3. Appends the note dict to ctx["carry_forward_notes"] so it appears in the API response.

Also settles yesterday's carry_forward_notes for today's date:
  - Orders that were assigned today → FULFILLED
  - Orders still dropped → leave PENDING (a new note will be created pointing to Day+1/Day+2)

De-duplication: if a PENDING note already exists for the same order_id + to_date, skip.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from uuid import UUID

from app.planners.context import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class CarryForwardAgent:
    name = "CarryForwardAgent"
    phase = 3
    execution = "parallel"

    def run(self, ctx: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        notes: list[dict] = []
        created = 0
        fulfilled = 0

        try:
            plan = ctx.get("plan_result", {})
            assignments = plan.get("assignments", [])
            plan_date: date = ctx["plan_date"]
            avail_map: dict[str, dict] = ctx.get("driver_availability_3day", {})

            # Build set of assigned order IDs
            assigned_ids: set[str] = {str(a["order_id"]) for a in assignments if "order_id" in a}

            # All order IDs collected by Phase 1
            all_order_ids: set[str] = {str(o.id) for o in ctx.get("orders", [])}
            dropped_ids = all_order_ids - assigned_ids

            if dropped_ids:
                created, notes = self._create_notes(ctx, dropped_ids, plan_date, avail_map)

            fulfilled = self._settle_fulfilled(ctx, assigned_ids, plan_date)

        except Exception as exc:
            logger.warning("%s: unexpected error: %s", self.name, exc)

        ctx["carry_forward_notes"] = notes

        elapsed = int((time.monotonic() - t0) * 1000)
        log_entry = {
            "step": self.name,
            "role": "tool",
            "content": (
                f"{len(notes)} carry-forward note(s) generated "
                f"({created} new, {fulfilled} fulfilled from prior day)."
            ),
        }
        ctx["logs"].append(log_entry)

        return AgentResult(
            agent_name=self.name,
            status="completed",
            output={
                "carry_forward_count": len(notes),
                "notes_created": created,
                "notes_fulfilled": fulfilled,
            },
            warnings=(
                [f"{len(notes)} order(s) dropped — carry-forward notes created."]
                if notes else []
            ),
            elapsed_ms=elapsed,
            log_entry=log_entry,
        )

    # ── Create notes for dropped orders ────────────────────────────────────────

    def _create_notes(
        self,
        ctx: AgentContext,
        dropped_ids: set[str],
        plan_date: date,
        avail_map: dict[str, dict],
    ) -> tuple[int, list[dict]]:
        from sqlalchemy import select
        from app.models.carry_forward_note import CarryForwardNote

        db = ctx["db"]
        tid = UUID(ctx["tenant_id"])
        day1 = plan_date + timedelta(days=1)
        day2 = plan_date + timedelta(days=2)

        # Drivers available on Day+1 (preferred) and Day+2 (fallback)
        drivers_day1 = [
            (did, info) for did, info in avail_map.items() if info.get("day1") == "available"
        ]
        drivers_day2 = [
            (did, info) for did, info in avail_map.items() if info.get("day2") == "available"
        ]

        # Existing PENDING notes to avoid duplicates
        existing = set()
        rows = db.execute(
            select(CarryForwardNote.order_id, CarryForwardNote.to_date).where(
                CarryForwardNote.tenant_id == tid,
                CarryForwardNote.status == "PENDING",
                CarryForwardNote.to_date.in_([day1, day2]),
            )
        ).all()
        for oid, tdate in rows:
            existing.add((str(oid), str(tdate)))

        created = 0
        notes: list[dict] = []

        for order_id_str in sorted(dropped_ids):
            order_uuid = UUID(order_id_str)

            # Pick Day+1 first, then Day+2
            to_date, driver_id_str, driver_name = self._pick_driver(
                order_id_str, day1, day2, drivers_day1, drivers_day2
            )
            if to_date is None:
                to_date = day1  # no driver match — still record the note

            key = (order_id_str, str(to_date))
            if key in existing:
                continue

            note_text = self._build_note(driver_name, to_date, plan_date)

            db.add(CarryForwardNote(
                tenant_id=tid,
                order_id=order_uuid,
                from_date=plan_date,
                to_date=to_date,
                suggested_driver_id=UUID(driver_id_str) if driver_id_str else None,
                context_note=note_text,
                status="PENDING",
            ))
            notes.append({
                "order_id": order_id_str,
                "from_date": str(plan_date),
                "to_date": str(to_date),
                "suggested_driver_id": driver_id_str,
                "suggested_driver_name": driver_name,
                "context_note": note_text,
            })
            created += 1

        if created:
            db.commit()

        return created, notes

    def _pick_driver(
        self,
        order_id_str: str,
        day1: date,
        day2: date,
        drivers_day1: list,
        drivers_day2: list,
    ) -> tuple[date | None, str | None, str | None]:
        """Return (to_date, driver_id, driver_name) — prefers Day+1."""
        # Simple round-robin: use order_id hash to spread load
        order_hash = hash(order_id_str)
        if drivers_day1:
            idx = order_hash % len(drivers_day1)
            did, info = drivers_day1[idx]
            return day1, did, info.get("name")
        if drivers_day2:
            idx = order_hash % len(drivers_day2)
            did, info = drivers_day2[idx]
            return day2, did, info.get("name")
        return None, None, None

    def _build_note(self, driver_name: str | None, to_date: date, from_date: date) -> str:
        days_ahead = (to_date - from_date).days
        day_label = "tomorrow" if days_ahead == 1 else f"in {days_ahead} days ({to_date})"
        if driver_name:
            return (
                f"Order dropped from {from_date} plan. "
                f"Driver {driver_name} is available {day_label} — suggested for reassignment."
            )
        return (
            f"Order dropped from {from_date} plan. "
            f"No driver matched for {day_label} — manual reassignment needed."
        )

    # ── Settle yesterday's notes ────────────────────────────────────────────────

    def _settle_fulfilled(
        self, ctx: AgentContext, assigned_ids: set[str], plan_date: date
    ) -> int:
        from sqlalchemy import select
        from app.models.carry_forward_note import CarryForwardNote

        db = ctx["db"]
        tid = UUID(ctx["tenant_id"])

        pending_today = db.execute(
            select(CarryForwardNote).where(
                CarryForwardNote.tenant_id == tid,
                CarryForwardNote.to_date == plan_date,
                CarryForwardNote.status == "PENDING",
            )
        ).scalars().all()

        fulfilled = 0
        for note in pending_today:
            if str(note.order_id) in assigned_ids:
                note.status = "FULFILLED"
                fulfilled += 1

        if fulfilled:
            db.commit()

        return fulfilled
