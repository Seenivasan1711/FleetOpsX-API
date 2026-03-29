"""
AgentSuggestion schemas — P3-E2
"""
from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel


class AgentSuggestionOut(BaseModel):
    id: UUID
    tenant_id: UUID
    plan_date: date
    suggestion_type: str
    status: str
    priority: str
    title: str
    detail: str | None
    context: dict[str, Any] | None
    expires_at: datetime | None
    acted_by: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


class AgentSuggestionUpdate(BaseModel):
    status: str   # "ACCEPTED" | "DISMISSED"
