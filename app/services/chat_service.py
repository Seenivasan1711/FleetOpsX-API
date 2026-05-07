from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.chat_message import ChatMessage
from app.services.chat_context_service import build_fleet_context

_HISTORY_WINDOW = 10  # prior message pairs to include for context
_FALLBACK_REPLY = (
    "Chat AI is not configured. Please set an LLM API key in your tenant settings "
    "(llm_provider + llm_api_key via TenantConfig)."
)

_SYSTEM_PROMPT = """You are FleetOpsX Assistant, an AI helping fleet dispatchers manage deliveries.
Answer questions about today's orders, drivers, vehicles, and route plans using the fleet context below.
Be concise and factual. If you don't know something, say so.

--- FLEET CONTEXT ---
{context}
--- END CONTEXT ---"""


def _save_messages(db: Session, tenant_id: UUID, session_id: str, user_text: str, reply_text: str) -> None:
    db.add(ChatMessage(tenant_id=tenant_id, session_id=session_id, role="user", content=user_text))
    db.add(ChatMessage(tenant_id=tenant_id, session_id=session_id, role="assistant", content=reply_text))
    db.commit()


def _load_history(db: Session, tenant_id: UUID, session_id: str) -> list[ChatMessage]:
    return db.execute(
        select(ChatMessage)
        .where(ChatMessage.tenant_id == tenant_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(_HISTORY_WINDOW * 2)
    ).scalars().all()[::-1]  # chronological order


def send_message(db: Session, tenant_id: str, session_id: str, user_text: str) -> tuple[str, bool]:
    """Returns (reply_text, used_llm)."""
    tid = UUID(tenant_id)

    llm = None
    try:
        from app.core.llm_factory import get_llm_for_tenant
        llm = get_llm_for_tenant(db=db, tenant_id=tenant_id)
    except (ValueError, Exception):
        pass

    if llm is None:
        _save_messages(db, tid, session_id, user_text, _FALLBACK_REPLY)
        return _FALLBACK_REPLY, False

    context = build_fleet_context(db, tenant_id, date.today())
    system_content = _SYSTEM_PROMPT.format(context=context)

    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    history = _load_history(db, tid, session_id)
    lc_messages = [SystemMessage(content=system_content)]
    for msg in history:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    lc_messages.append(HumanMessage(content=user_text))

    try:
        response = llm.invoke(lc_messages)
        reply = response.content
    except Exception as exc:
        reply = f"Sorry, I encountered an error: {exc}"

    _save_messages(db, tid, session_id, user_text, reply)
    return reply, True


def get_history(db: Session, tenant_id: str, session_id: str) -> list[ChatMessage]:
    tid = UUID(tenant_id)
    return db.execute(
        select(ChatMessage)
        .where(ChatMessage.tenant_id == tid, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(50)
    ).scalars().all()
