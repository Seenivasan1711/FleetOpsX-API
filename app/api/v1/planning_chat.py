"""
Planning Chat API — AI-1 E8.

POST /chat/planning            — send a message to the planning-aware chat agent
GET  /chat/planning/{session_id}/history — retrieve planning chat history

When an OPEN planning session exists for the requested date the request is
routed to PlanningChatAgent (tool-calling, plan-mutating).
If no OPEN session is found the endpoint returns 404.
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services import planning_chat_agent as agent_svc

router = APIRouter(prefix="/chat/planning", tags=["Planning Chat"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PlanningChatRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None  # planning_session UUID; auto-detected if omitted
    plan_date: Optional[date] = None   # defaults to today if session_id not given


class PlanningChatResponse(BaseModel):
    planning_session_id: str
    reply: str
    used_llm: bool
    has_active_session: bool  # True when an OPEN session is active


class PlanningChatHistoryItem(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class PlanningChatHistoryResponse(BaseModel):
    planning_session_id: str
    messages: List[PlanningChatHistoryItem]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=PlanningChatResponse)
def post_planning_message(
    body: PlanningChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Send a message to the planning-aware chat agent.

    If session_id is provided, use that OPEN session.
    Otherwise auto-detect the OPEN session for plan_date (defaults to today).
    Returns 404 if no OPEN session is found.
    """
    tenant_id = str(current_user.tenant_id)

    if body.session_id:
        # Resolve the provided session id
        from app.models.planning_session import PlanningSession
        from sqlalchemy import select
        from uuid import UUID

        session = db.execute(
            select(PlanningSession).where(
                PlanningSession.id == body.session_id,
                PlanningSession.tenant_id == current_user.tenant_id,
            )
        ).scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Planning session not found.")
        if session.status != "OPEN":
            raise HTTPException(
                status_code=400,
                detail=f"Session {session.id} is {session.status} — only OPEN sessions accept chat messages.",
            )
    else:
        target_date = body.plan_date or date.today()
        session = agent_svc.get_open_session(db, tenant_id, target_date)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"No OPEN planning session found for {target_date}. Start a session first.",
            )

    reply, used_llm = agent_svc.send_planning_message(
        db=db,
        tenant_id=tenant_id,
        planning_session_id=str(session.id),
        user_text=body.message,
    )

    return PlanningChatResponse(
        planning_session_id=str(session.id),
        reply=reply,
        used_llm=used_llm,
        has_active_session=True,
    )


@router.get("/{session_id}/history", response_model=PlanningChatHistoryResponse)
def get_planning_history(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Retrieve the full chat history for a planning session."""
    tenant_id = str(current_user.tenant_id)

    # Verify session belongs to tenant
    from app.models.planning_session import PlanningSession
    from sqlalchemy import select

    session = db.execute(
        select(PlanningSession).where(
            PlanningSession.id == session_id,
            PlanningSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Planning session not found.")

    messages = agent_svc.get_planning_history(db, tenant_id, str(session_id))

    return PlanningChatHistoryResponse(
        planning_session_id=str(session_id),
        messages=[
            PlanningChatHistoryItem(
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in messages
        ],
    )
