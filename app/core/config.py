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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
