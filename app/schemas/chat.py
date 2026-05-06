from pydantic import BaseModel
from uuid import UUID
from typing import List
from datetime import datetime


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str
    used_llm: bool


class ChatHistoryItem(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatHistoryItem]
