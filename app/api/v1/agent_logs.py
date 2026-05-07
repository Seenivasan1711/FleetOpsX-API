"""
Agent logs endpoint — P2-E3

GET /agent-logs   — list step-by-step reasoning from the LangGraph agent
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.agent_log import AgentLog
from app.schemas.agent_log import AgentLogOut

router = APIRouter(prefix="/agent-logs", tags=["Agent Logs"])


@router.get("", response_model=list[AgentLogOut])
def list_agent_logs(
    plan_id: Optional[UUID] = Query(None, description="Filter by route plan ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Return agent reasoning steps for the caller's tenant.
    Optionally scoped to a single plan via ?plan_id=<uuid>.
    """
    stmt = (
        select(AgentLog)
        .where(AgentLog.tenant_id == current_user.tenant_id)
        .order_by(AgentLog.created_at.desc())
        .limit(limit)
    )
    if plan_id is not None:
        stmt = stmt.where(AgentLog.plan_id == plan_id)

    return db.execute(stmt).scalars().all()
