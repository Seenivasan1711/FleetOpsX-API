"""
Planning Sessions API — AI-1 E3.

POST   /plan/sessions             — open session + run round 1
GET    /plan/sessions             — list sessions for tenant
GET    /plan/sessions/{id}        — session detail with all versioned plans
POST   /plan/sessions/{id}/rounds — new AI round (adds hints, reruns planner)
POST   /plan/sessions/{id}/confirm — lock a specific plan version
DELETE /plan/sessions/{id}        — discard open session
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.schemas.planning_session import (
    ConfirmRequest,
    PlanningSessionOut,
    PlanVersionSummary,
    RoundCreate,
    SessionCreate,
    SessionDetailOut,
    SessionWithPlanOut,
)
import app.services.planning_session_service as svc
from app.services.planning_chat_agent import get_open_session

router = APIRouter(prefix="/plan/sessions", tags=["Planning Sessions"])


@router.get("/active", response_model=Optional[PlanningSessionOut])
def get_active_session(
    plan_date: Optional[date] = Query(None, description="Defaults to today"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Return the OPEN planning session for the given date (default: today), or null.
    Used by the UI to decide whether planning chat mode should be active.
    """
    target_date = plan_date or date.today()
    session = get_open_session(db, str(current_user.tenant_id), target_date)
    if not session:
        return None
    return PlanningSessionOut.model_validate(session)


@router.post("", response_model=SessionWithPlanOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Open a new planning session for plan_date and run the first AI planning round.
    Returns the session object and the full plan result dict.
    Raises 409 if an OPEN session already exists for this tenant + date.
    """
    try:
        session, plan = svc.create_session(
            db,
            tenant_id=str(current_user.tenant_id),
            plan_date=body.plan_date,
            user_id=current_user.id,
            initial_hints=body.hints,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return SessionWithPlanOut(
        session=PlanningSessionOut.model_validate(session),
        plan=plan,
    )


@router.get("", response_model=List[PlanningSessionOut])
def list_sessions(
    plan_date: Optional[date] = Query(None),
    session_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """List planning sessions for the current tenant (most recent first)."""
    sessions = svc.list_sessions(
        db,
        tenant_id=str(current_user.tenant_id),
        plan_date=plan_date,
        status=session_status,
    )
    return [PlanningSessionOut.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return a session with all versioned RoutePlan summaries."""
    try:
        session = svc.get_session(db, tenant_id=str(current_user.tenant_id), session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    plans = svc.list_session_versions(db, session_id=session_id)
    versions = [
        PlanVersionSummary(
            plan_id=p.id,
            version_number=p.version_number or 1,
            status=p.status,
            km_saved=p.km_saved,
            hrs_saved=p.hrs_saved,
            total_orders=p.total_orders or 0,
            assigned_orders=p.assigned_orders or 0,
            round_hints=p.round_hints or [],
            created_at=p.created_at,
        )
        for p in plans
    ]

    return SessionDetailOut(
        session=PlanningSessionOut.model_validate(session),
        versions=versions,
    )


@router.post("/{session_id}/rounds", response_model=SessionWithPlanOut)
def run_round(
    session_id: UUID,
    body: RoundCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Run a new AI planning round within an existing OPEN session.
    Provide new dispatcher hints; they are accumulated with previous rounds.
    """
    try:
        session, plan = svc.run_round(
            db,
            tenant_id=str(current_user.tenant_id),
            session_id=session_id,
            new_hints=body.hints,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return SessionWithPlanOut(
        session=PlanningSessionOut.model_validate(session),
        plan=plan,
    )


@router.post("/{session_id}/confirm", response_model=PlanningSessionOut)
def confirm_session(
    session_id: UUID,
    body: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Lock the session and promote the chosen plan version to PUBLISHED.
    All other versions for this session are marked SUPERSEDED.
    """
    try:
        session = svc.confirm_session(
            db,
            tenant_id=str(current_user.tenant_id),
            session_id=session_id,
            plan_id=body.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return PlanningSessionOut.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Discard an OPEN session — marks it EXPIRED and all its plans SUPERSEDED."""
    try:
        svc.discard_session(
            db,
            tenant_id=str(current_user.tenant_id),
            session_id=session_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
