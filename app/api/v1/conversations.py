"""
Conversations API — Phase 6 (MongoDB-backed chat history with Postgres fallback)

When MONGODB_URL is set + motor installed: full conversation persistence in MongoDB.
When not configured: endpoints return graceful empty/fallback responses.
  - GET  /chat/conversations           → []
  - POST /chat/conversations           → pseudo conversation (id = "session")
  - GET  /chat/conversations/{id}/messages → []
  - POST /chat/conversations/{id}/messages → uses existing Postgres chat_service
  - DELETE /chat/conversations/{id}    → 204 (no-op)

Frontend handles both modes: shows history when MongoDB active, falls back to
in-session (localStorage) chat when not.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.mongo import get_mongo_db, is_mongo_active

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


# ─── Status endpoint ──────────────────────────────────────────────────────────

@router.get("/status")
async def chat_storage_status():
    """Returns whether MongoDB-backed chat history is active."""
    return {"mongodb_active": is_mongo_active()}


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
        id=str(doc.get("_id", _uuid.uuid4())),
        role=doc["role"],
        content=doc["content"],
        created_at=doc.get("created_at", _now()),
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ConversationOut])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not is_mongo_active():
        return []
    mdb = get_mongo_db()
    cursor = mdb["chat_conversations"].find(
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
    now = _now()
    if not is_mongo_active():
        # Return a stable pseudo-conversation the FE can use as a session key
        return ConversationOut(
            id="session",
            title=body.title or "Chat Session",
            created_at=now,
            updated_at=now,
        )
    mdb = get_mongo_db()
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
    if not is_mongo_active() or conversation_id == "session":
        return []
    try:
        from bson import ObjectId
        mdb = get_mongo_db()
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
    except HTTPException:
        raise
    except Exception:
        return []


@router.post("/{conversation_id}/messages", response_model=list[MessageOut], status_code=201)
async def send_message(
    conversation_id: str,
    body: MessageSend,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    now = _now()
    user_msg = MessageOut(id=str(_uuid.uuid4()), role="user", content=body.content, created_at=now)

    if not is_mongo_active() or conversation_id == "session":
        # Fallback: use the existing Postgres-backed chat service
        ai_reply = await _postgres_chat(db, str(current_user.tenant_id), conversation_id, body.content)
        ai_msg   = MessageOut(id=str(_uuid.uuid4()), role="assistant", content=ai_reply, created_at=_now())
        return [user_msg, ai_msg]

    # MongoDB path
    try:
        from bson import ObjectId
        mdb = get_mongo_db()
        conv = await mdb["chat_conversations"].find_one({
            "_id": ObjectId(conversation_id),
            "tenant_id": str(current_user.tenant_id),
        })
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

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
        if conv.get("title") in ("New Conversation", None, ""):
            title = body.content[:60].strip()
            if len(body.content) > 60:
                title += "…"
            await mdb["chat_conversations"].update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"title": title, "updated_at": now}},
            )

        # Fetch history for multi-turn context
        history_cursor = mdb["chat_messages"].find(
            {"conversation_id": conversation_id},
            sort=[("created_at", -1)],
            limit=_HISTORY_WINDOW * 2,
        )
        history_docs = await history_cursor.to_list(length=_HISTORY_WINDOW * 2)
        history_docs = list(reversed(history_docs[:-1]))

        ai_reply = await _get_ai_reply(db, str(current_user.tenant_id), body.content, history_docs)

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

    except HTTPException:
        raise
    except Exception as exc:
        # Unexpected error — still return a response using Postgres fallback
        ai_reply = await _postgres_chat(db, str(current_user.tenant_id), conversation_id, body.content)
        ai_msg   = MessageOut(id=str(_uuid.uuid4()), role="assistant", content=ai_reply, created_at=_now())
        return [user_msg, ai_msg]


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not is_mongo_active() or conversation_id == "session":
        return  # graceful no-op
    try:
        from bson import ObjectId
        mdb = get_mongo_db()
        await mdb["chat_conversations"].delete_one({
            "_id": ObjectId(conversation_id),
            "tenant_id": str(current_user.tenant_id),
        })
        await mdb["chat_messages"].delete_many({"conversation_id": conversation_id})
    except Exception:
        pass  # ignore errors on delete


# ─── AI helpers ───────────────────────────────────────────────────────────────

async def _postgres_chat(db: Session, tenant_id: str, session_id: str, user_text: str) -> str:
    """Fallback to existing Postgres-backed chat_service (synchronous, run in threadpool)."""
    import asyncio
    from app.services.chat_service import send_message as _send
    try:
        loop = asyncio.get_event_loop()
        reply, _ = await loop.run_in_executor(None, _send, db, tenant_id, session_id, user_text)
        return reply
    except Exception as exc:
        return f"Sorry, I couldn't process that request: {exc}"


_SYSTEM_PROMPT = """You are FleetOpsX Assistant — an AI helping fleet dispatchers manage deliveries.
Answer questions about orders, drivers, vehicles, and route plans using the fleet context below.
Be concise and factual. Only answer questions about fleet operations.

--- FLEET CONTEXT ---
{context}
--- END CONTEXT ---"""

_FALLBACK = "Chat AI is not configured. Please set an LLM API key in your tenant settings."


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
        lc_messages.append(HumanMessage(content=msg["content"]) if msg["role"] == "user"
                           else AIMessage(content=msg["content"]))
    lc_messages.append(HumanMessage(content=user_text))

    try:
        response = llm.invoke(lc_messages)
        return response.content
    except Exception as exc:
        return f"Sorry, I encountered an error: {exc}"
