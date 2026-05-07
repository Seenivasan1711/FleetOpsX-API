import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.context import set_current_tenant_id

logger = logging.getLogger(__name__)

EXCLUDED_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            set_current_tenant_id(tenant_id)
            logger.debug(f"Tenant context set: {tenant_id}")
        else:
            logger.debug("No X-Tenant-ID header present")

        return await call_next(request)
