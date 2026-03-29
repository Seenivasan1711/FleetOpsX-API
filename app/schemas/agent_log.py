"""Agent log schemas — P2-E3."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AgentLogOut(BaseModel):
    id: UUID
    plan_id: Optional[UUID]
    step: str
    role: str
    content: str
    llm_provider: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
