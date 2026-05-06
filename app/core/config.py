from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_ENV: str = "local"
    DATABASE_URL: str
    REDIS_URL: str
    SENTRY_DSN: Optional[str] = None
    MAPS_API_KEY: Optional[str] = None

    # Auth (used in P1-E3-S6)
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Planner (used in P1-E4)
    PLANNER_TYPE: str = "rule_based"

    # Multi-tenant DB routing (P4-E1)
    TENANT_MODE: str = "multi"              # "multi" | "single" (on-prem/single-tenant)
    DB_ROUTE_REFRESH_INTERVAL: int = 60     # seconds between route cache refreshes

    # LLM — system-wide defaults (tenants can override via TenantConfig KV store)
    LLM_PROVIDER: str = "gemini"          # gemini | openai | anthropic
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
