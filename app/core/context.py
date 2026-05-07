from contextvars import ContextVar
from typing import Optional

tenant_context: ContextVar[Optional[str]] = ContextVar(
    "tenant_context", default=None
)

def get_current_tenant_id() -> Optional[str]:
    return tenant_context.get()

def set_current_tenant_id(tenant_id: str) -> None:
    tenant_context.set(tenant_id)
