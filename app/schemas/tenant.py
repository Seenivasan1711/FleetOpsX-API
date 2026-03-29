"""Tenant-level config schemas — P2-E2."""
from typing import Optional
from pydantic import BaseModel, field_validator


class LLMConfigUpdate(BaseModel):
    """PATCH body for /tenants/config/llm"""
    provider: Optional[str] = None   # gemini | openai | anthropic
    api_key: Optional[str] = None    # stored encrypted-at-rest in future; plain for now
    model: Optional[str] = None      # override default model for the provider

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        if v is not None and v.lower() not in ("gemini", "openai", "anthropic"):
            raise ValueError("provider must be one of: gemini, openai, anthropic")
        return v.lower() if v else v


class LLMConfigOut(BaseModel):
    """Response for GET /tenants/config/llm"""
    provider: str
    model: str
    api_key_set: bool   # True if a key is stored; never echo the key back
