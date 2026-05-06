from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse, ChatHistoryItem
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatMessageResponse)
def post_chat_message(
    data: ChatMessageRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    reply, used_llm = chat_service.send_message(db, tenant_id, data.session_id, data.message)
    return ChatMessageResponse(session_id=data.session_id, reply=reply, used_llm=used_llm)


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    messages = chat_service.get_history(db, tenant_id, session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatHistoryItem.model_validate(m) for m in messages],
    )
