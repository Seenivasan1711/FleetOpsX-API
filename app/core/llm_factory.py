"""
LLM Factory — P2-E2

Builds a LangChain BaseChatModel for a given tenant.

Resolution order:
  1. TenantConfig KV rows  (llm_provider, llm_api_key, llm_model)
  2. System-wide env vars   (LLM_PROVIDER, <PROVIDER>_API_KEY)

Supported providers: gemini | openai | anthropic
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tenant import TenantConfig

# Default models per provider (used when tenant hasn't set a specific model)
_DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
}


def _load_tenant_llm_config(db: Session, tenant_id: UUID) -> dict:
    """Return a dict with keys that exist in TenantConfig for this tenant."""
    rows = db.execute(
        select(TenantConfig).where(
            TenantConfig.tenant_id == tenant_id,
            TenantConfig.config_key.in_(["llm_provider", "llm_api_key", "llm_model"]),
        )
    ).scalars().all()
    return {row.config_key: row.config_value for row in rows}


def get_llm_for_tenant(db: Session, tenant_id: str):
    """
    Return a LangChain BaseChatModel configured for the given tenant.

    Raises ValueError if the resolved API key is missing.
    """
    tid = UUID(tenant_id)
    kv = _load_tenant_llm_config(db, tid)

    provider = (kv.get("llm_provider") or settings.LLM_PROVIDER).lower()
    model = kv.get("llm_model") or _DEFAULT_MODELS.get(provider)

    # Tenant-supplied key takes priority; fall back to env
    api_key: Optional[str] = kv.get("llm_api_key")

    if provider == "gemini":
        if not api_key:
            api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("Gemini API key not configured (set GEMINI_API_KEY or tenant llm_api_key)")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key)

    if provider == "openai":
        if not api_key:
            api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not configured (set OPENAI_API_KEY or tenant llm_api_key)")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, openai_api_key=api_key)

    if provider == "anthropic":
        if not api_key:
            api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("Anthropic API key not configured (set ANTHROPIC_API_KEY or tenant llm_api_key)")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, anthropic_api_key=api_key)

    raise ValueError(f"Unknown LLM provider: {provider!r}. Use gemini | openai | anthropic")
