from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_ENV: str = "local"
    DATABASE_URL: str
    REDIS_URL: str
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
