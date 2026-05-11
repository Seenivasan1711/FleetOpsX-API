"""
Conversations API — Phase 6 (MongoDB-backed chat history)

GET    /chat/conversations              → list user's conversations
POST   /chat/conversations              → create new conversation
GET    /chat/conversations/{id}/messages → fetch messages
POST   /chat/conversations/{id}/messages → send message + get AI reply
DELETE /chat/conversations/{id}         → delete conversation
"""
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.mongo import get_mongo_db

router = APIRouter(prefix="/chat/conversations", tags=["Chat"])

_HISTORY_WINDOW = 10


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class MessageSend(BaseModel):
    content: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conv_out(doc: dict) -> ConversationOut:
    return ConversationOut(
        id=str(doc["_id"]),
        title=doc.get("title", "Conversation"),
        created_at=doc.get("created_at", ""),
        updated_at=doc.get("updated_at", ""),
    )


def _msg_out(doc: dict) -> MessageOut:
    return MessageOut(
        id=str(doc["_id"]),
        role=doc["role"],
        content=doc["content"],
        created_at=doc.get("created_at", ""),
    )


def _require_mongo() -> Any:
    db = get_mongo_db()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB not configured. Set MONGODB_URL in environment.",
        )
    return db


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ConversationOut])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mdb = _require_mongo()
    coll = mdb["chat_conversations"]
    cursor = coll.find(
        {"tenant_id": str(current_user.tenant_id), "user_id": str(current_user.id)},
        sort=[("updated_at", -1)],
        limit=50,
    )
    docs = await cursor.to_list(length=50)
    return [_conv_out(d) for d in docs]


@router.post("/", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mdb = _require_mongo()
    now = _now()
    doc = {
        "tenant_id": str(current_user.tenant_id),
        "user_id": str(current_user.id),
        "title": body.title or "New Conversation",
        "created_at": now,
        "updated_at": now,
    }
    result = await mdb["chat_conversations"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _conv_out(doc)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mdb = _require_mongo()
    conv = await mdb["chat_conversations"].find_one({
        "_id": ObjectId(conversation_id),
        "tenant_id": str(current_user.tenant_id),
    })
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    cursor = mdb["chat_messages"].find(
        {"conversation_id": conversation_id},
        sort=[("created_at", 1)],
    )
    docs = await cursor.to_list(length=200)
    return [_msg_out(d) for d in docs]


@router.post("/{conversation_id}/messages", response_model=list[MessageOut], status_code=201)
async def send_message(
    conversation_id: str,
    body: MessageSend,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mdb = _require_mongo()
    conv = await mdb["chat_conversations"].find_one({
        "_id": ObjectId(conversation_id),
        "tenant_id": str(current_user.tenant_id),
    })
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    now = _now()

    # Save user message
    user_doc = {
        "conversation_id": conversation_id,
        "tenant_id": str(current_user.tenant_id),
        "role": "user",
        "content": body.content,
        "created_at": now,
    }
    await mdb["chat_messages"].insert_one(user_doc)

    # Auto-title from first message
    if conv.get("title") in ("New Conversation", None):
        title = body.content[:60].strip()
        if len(body.content) > 60:
            title += "…"
        await mdb["chat_conversations"].update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"title": title, "updated_at": now}},
        )

    # Build conversation history for LLM context
    history_cursor = mdb["chat_messages"].find(
        {"conversation_id": conversation_id},
        sort=[("created_at", -1)],
        limit=_HISTORY_WINDOW * 2,
    )
    history_docs = await history_cursor.to_list(length=_HISTORY_WINDOW * 2)
    history_docs = list(reversed(history_docs[:-1]))  # chronological, exclude just-saved user msg

    # Call LLM
    ai_reply = await _get_ai_reply(db, str(current_user.tenant_id), body.content, history_docs)

    # Save AI message
    ai_doc = {
        "conversation_id": conversation_id,
        "tenant_id": str(current_user.tenant_id),
        "role": "assistant",
        "content": ai_reply,
        "created_at": _now(),
    }
    await mdb["chat_messages"].insert_one(ai_doc)
    await mdb["chat_conversations"].update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"updated_at": _now()}},
    )

    return [_msg_out(user_doc), _msg_out(ai_doc)]


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mdb = _require_mongo()
    result = await mdb["chat_conversations"].delete_one({
        "_id": ObjectId(conversation_id),
        "tenant_id": str(current_user.tenant_id),
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await mdb["chat_messages"].delete_many({"conversation_id": conversation_id})


# ─── LLM call (multi-turn) ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are FleetOpsX Assistant — an AI helping fleet dispatchers manage deliveries.
Answer questions about orders, drivers, vehicles, and route plans using the fleet context below.
Be concise and factual. Only answer questions about fleet operations.

--- FLEET CONTEXT ---
{context}
--- END CONTEXT ---"""

_FALLBACK = (
    "Chat AI is not configured. Please set an LLM API key in your tenant settings."
)


async def _get_ai_reply(db: Session, tenant_id: str, user_text: str, history: list[dict]) -> str:
    from datetime import date as _date
    from app.services.chat_context_service import build_fleet_context

    try:
        from app.core.llm_factory import get_llm_for_tenant
        llm = get_llm_for_tenant(db=db, tenant_id=tenant_id)
    except Exception:
        return _FALLBACK

    if llm is None:
        return _FALLBACK

    context = build_fleet_context(db, tenant_id, _date.today())
    system_content = _SYSTEM_PROMPT.format(context=context)

    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    lc_messages = [SystemMessage(content=system_content)]
    for msg in history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        else:
            lc_messages.append(AIMessage(content=msg["content"]))
    lc_messages.append(HumanMessage(content=user_text))

    try:
        response = llm.invoke(lc_messages)
        return response.content
    except Exception as exc:
        return f"Sorry, I encountered an error: {exc}"
