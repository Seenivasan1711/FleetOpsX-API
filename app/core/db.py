import base64
import hashlib
import logging
import threading
import redis as redis_lib
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from cryptography.fernet import Fernet

from .config import settings

logger = logging.getLogger(__name__)

# ─── Redis ────────────────────────────────────────────────────────────────────

_redis_client = None


def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# ─── Shared DB ────────────────────────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Connection-string encryption (Fernet, keyed from JWT secret) ─────────────

def _fernet() -> Fernet:
    raw = settings.JWT_SECRET_KEY.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_connection_string(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_connection_string(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


def mask_connection_string(encrypted: str) -> str:
    """Return a safe display string — strips credentials from the decrypted URL."""
    try:
        plain = decrypt_connection_string(encrypted)
        # hide password: postgresql://user:PASSWORD@host/db → postgresql://user:***@host/db
        if "@" in plain and "://" in plain:
            scheme_user, rest = plain.split("@", 1)
            if ":" in scheme_user.split("://", 1)[-1]:
                prefix, _ = scheme_user.rsplit(":", 1)
                return f"{prefix}:***@{rest}"
        return plain
    except Exception:
        return "***"


# ─── Per-tenant DB routing (P4-E1) ───────────────────────────────────────────

_route_cache: dict[str, sessionmaker] = {}  # tenant_id (str) → session factory
_route_lock = threading.Lock()


def refresh_route_cache(db: Session) -> int:
    """Load active TenantDbRoute rows and rebuild the in-memory session factory map.

    Returns the number of routes loaded.
    """
    from app.models.tenant_db_route import TenantDbRoute  # local import avoids circular

    try:
        routes = db.query(TenantDbRoute).filter_by(is_active=True).all()
    except Exception as exc:
        logger.warning("route cache refresh skipped — DB not ready: %s", exc)
        return 0

    new_cache: dict[str, sessionmaker] = {}
    for route in routes:
        try:
            conn_str = decrypt_connection_string(route.connection_string)
            eng = create_engine(
                conn_str,
                pool_pre_ping=True,
                pool_size=route.max_pool_size,
                future=True,
            )
            new_cache[str(route.tenant_id)] = sessionmaker(
                autocommit=False, autoflush=False, bind=eng, future=True
            )
        except Exception as exc:
            logger.error("Failed to create engine for tenant %s: %s", route.tenant_id, exc)

    with _route_lock:
        _route_cache.clear()
        _route_cache.update(new_cache)

    logger.info("DB route cache refreshed — %d dedicated tenants", len(new_cache))
    return len(new_cache)


def get_db_for_tenant(tenant_id: str) -> Session:
    """Return a DB session for the given tenant.

    - TENANT_MODE=single → always shared DB (on-prem / single-tenant deployments)
    - Dedicated route found → use tenant's own DB
    - No route → fall back to shared DB
    """
    if settings.TENANT_MODE == "single":
        return SessionLocal()

    with _route_lock:
        factory = _route_cache.get(tenant_id)

    if factory:
        return factory()
    return SessionLocal()
