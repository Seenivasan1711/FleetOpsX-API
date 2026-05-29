"""
Planning Session Service — AI-1 E3.

Manages the iterative planning session lifecycle:
  create_session → run_round → confirm_session / discard_session
  lock_expired_sessions (called by APScheduler every 30 min)

Each session owns N versioned RoutePlan rows linked via session_id.
The runner is called once per create/round; the resulting plan_id is
tagged back onto the RoutePlan row and the session's active_plan_id.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import Session

from app.models.planning_session import PlanningSession
from app.models.route_plan import RoutePlan

logger = logging.getLogger(__name__)

_DEFAULT_CUTOFF = "19:00"


# ─── Public API ────────────────────────────────────────────────────────────────

def create_session(
    db: Session,
    *,
    tenant_id: str,
    plan_date: date,
    user_id: UUID | None = None,
    initial_hints: list[str] | None = None,
) -> tuple[PlanningSession, dict[str, Any]]:
    """
    Open a new planning session for plan_date, run Round 1, return (session, plan_result).
    Raises ValueError if an OPEN session already exists for the same tenant+date.
    """
    existing = db.execute(
        select(PlanningSession).where(
            PlanningSession.tenant_id == UUID(tenant_id),
            PlanningSession.plan_date == plan_date,
            PlanningSession.status == "OPEN",
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(
            f"An OPEN planning session already exists for {plan_date} "
            f"(session_id={existing.id}). Use POST /plan/sessions/{{id}}/rounds to refine it."
        )

    cutoff_at = _compute_cutoff(db, tenant_id, plan_date)
    hints = initial_hints or []

    session = PlanningSession(
        tenant_id=UUID(tenant_id),
        plan_date=plan_date,
        status="OPEN",
        cutoff_at=cutoff_at,
        created_by=user_id,
        accumulated_hints=hints,
    )
    db.add(session)
    db.flush()  # materialise session.id before running the planner

    plan_result = _run_and_tag(
        db=db,
        tenant_id=tenant_id,
        session=session,
        version=1,
        parent_plan_id=None,
        round_hints=hints,
    )
    db.commit()
    db.refresh(session)
    return session, plan_result


def run_round(
    db: Session,
    *,
    tenant_id: str,
    session_id: UUID,
    new_hints: list[str],
) -> tuple[PlanningSession, dict[str, Any]]:
    """
    Run a new AI planning round within an existing OPEN session.
    new_hints are appended to the session's accumulated_hints before calling the runner.
    """
    session = _require_open_session(db, tenant_id, session_id)

    prev_plan_id = session.active_plan_id
    current_version = _max_version(db, session.id)

    # Accumulate hints so the runner always sees the full history
    accumulated = list(session.accumulated_hints or []) + new_hints
    session.accumulated_hints = accumulated

    plan_result = _run_and_tag(
        db=db,
        tenant_id=tenant_id,
        session=session,
        version=current_version + 1,
        parent_plan_id=prev_plan_id,
        round_hints=new_hints,
    )
    db.commit()
    db.refresh(session)
    return session, plan_result


def get_session(db: Session, *, tenant_id: str, session_id: UUID) -> PlanningSession:
    session = db.execute(
        select(PlanningSession).where(
            PlanningSession.id == session_id,
            PlanningSession.tenant_id == UUID(tenant_id),
        )
    ).scalar_one_or_none()
    if not session:
        raise ValueError(f"Planning session {session_id} not found")
    return session


def list_sessions(
    db: Session,
    *,
    tenant_id: str,
    plan_date: date | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[PlanningSession]:
    q = select(PlanningSession).where(
        PlanningSession.tenant_id == UUID(tenant_id)
    ).order_by(PlanningSession.created_at.desc()).limit(limit)

    if plan_date:
        q = q.where(PlanningSession.plan_date == plan_date)
    if status:
        q = q.where(PlanningSession.status == status.upper())

    return list(db.execute(q).scalars().all())


def list_session_versions(db: Session, *, session_id: UUID) -> list[RoutePlan]:
    return list(
        db.execute(
            select(RoutePlan)
            .where(RoutePlan.session_id == session_id)
            .order_by(RoutePlan.version_number)
        ).scalars().all()
    )


def confirm_session(
    db: Session,
    *,
    tenant_id: str,
    session_id: UUID,
    plan_id: UUID,
) -> PlanningSession:
    """Lock the session and mark the chosen plan version as PUBLISHED."""
    session = _require_open_session(db, tenant_id, session_id)

    # Verify plan_id belongs to this session
    plan = db.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.session_id == session_id,
        )
    ).scalar_one_or_none()
    if not plan:
        raise ValueError(f"Plan {plan_id} does not belong to session {session_id}")

    # Promote chosen plan, mark others SUPERSEDED
    db.execute(
        sa_update(RoutePlan)
        .where(RoutePlan.session_id == session_id, RoutePlan.id != plan_id)
        .values(status="SUPERSEDED")
    )
    plan.status = "PUBLISHED"
    session.active_plan_id = plan_id
    session.status = "COMPLETED"

    db.commit()
    db.refresh(session)
    return session


def discard_session(
    db: Session,
    *,
    tenant_id: str,
    session_id: UUID,
) -> None:
    """Discard an OPEN session — marks it EXPIRED and all its plans SUPERSEDED."""
    session = _require_open_session(db, tenant_id, session_id)
    session.status = "EXPIRED"
    db.execute(
        sa_update(RoutePlan)
        .where(RoutePlan.session_id == session_id)
        .values(status="SUPERSEDED")
    )
    db.commit()


def lock_expired_sessions(db: Session) -> int:
    """
    Lock all OPEN sessions whose cutoff_at has passed.
    Called by APScheduler every 30 minutes.
    Returns the number of sessions locked.
    """
    now = datetime.utcnow()
    result = db.execute(
        sa_update(PlanningSession)
        .where(
            PlanningSession.status == "OPEN",
            PlanningSession.cutoff_at <= now,
        )
        .values(status="LOCKED")
        .returning(PlanningSession.id)
    )
    db.commit()
    locked_ids = result.fetchall()
    return len(locked_ids)


# ─── Internals ─────────────────────────────────────────────────────────────────

def _run_and_tag(
    db: Session,
    *,
    tenant_id: str,
    session: PlanningSession,
    version: int,
    parent_plan_id: UUID | None,
    round_hints: list[str],
) -> dict[str, Any]:
    """Call run_planning, then tag the resulting RoutePlan with session metadata."""
    from app.planners.runner import run_planning

    result = run_planning(
        db=db,
        tenant_id=tenant_id,
        plan_date=session.plan_date,
        session_id=str(session.id),
        session_hints=list(session.accumulated_hints or []),
    )

    plan_id_str = result.get("plan_id")
    if plan_id_str:
        plan_uuid = UUID(plan_id_str)
        db.execute(
            sa_update(RoutePlan)
            .where(RoutePlan.id == plan_uuid)
            .values(
                session_id=session.id,
                version_number=version,
                parent_plan_id=parent_plan_id,
                round_hints=round_hints,
            )
        )
        session.active_plan_id = plan_uuid

    return result


def _require_open_session(db: Session, tenant_id: str, session_id: UUID) -> PlanningSession:
    session = db.execute(
        select(PlanningSession).where(
            PlanningSession.id == session_id,
            PlanningSession.tenant_id == UUID(tenant_id),
        )
    ).scalar_one_or_none()
    if not session:
        raise ValueError(f"Planning session {session_id} not found")
    if session.status != "OPEN":
        raise ValueError(
            f"Session {session_id} is {session.status} — only OPEN sessions can be modified"
        )
    return session


def _max_version(db: Session, session_id: UUID) -> int:
    from sqlalchemy import func
    row = db.execute(
        select(func.max(RoutePlan.version_number)).where(RoutePlan.session_id == session_id)
    ).scalar()
    return row or 0


def _compute_cutoff(db: Session, tenant_id: str, plan_date: date) -> datetime:
    """Resolve cutoff datetime from TenantConfig planning_cutoff_time (default 19:00 local)."""
    cutoff_str = _DEFAULT_CUTOFF
    try:
        from sqlalchemy import select as sa_select
        from app.models.tenant import TenantConfig
        row = db.execute(
            sa_select(TenantConfig).where(
                TenantConfig.tenant_id == UUID(tenant_id),
                TenantConfig.config_key == "planning_cutoff_time",
            )
        ).scalar_one_or_none()
        if row:
            cutoff_str = row.config_value
    except Exception as exc:
        logger.warning("Could not read planning_cutoff_time for tenant %s: %s", tenant_id, exc)

    try:
        h, m = cutoff_str.split(":")
        cutoff_time = time(int(h), int(m))
    except ValueError:
        logger.warning("Invalid planning_cutoff_time %r — using default %s", cutoff_str, _DEFAULT_CUTOFF)
        cutoff_time = time(19, 0)

    return datetime.combine(plan_date, cutoff_time)
