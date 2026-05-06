from fastapi import APIRouter
from app.api import health
from app.api.v1 import (
    auth, depots, drivers, vehicles, customers, orders, planning, driver,
    tenants, agent_logs, tracking, sla, analytics, agent_suggestions,
    export, import_orders, fleet, chat, admin, integrations, marketplace,
    audit, governance, scenarios,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(depots.router, prefix="/api/v1")
api_router.include_router(drivers.router, prefix="/api/v1")
api_router.include_router(vehicles.router, prefix="/api/v1")
api_router.include_router(customers.router, prefix="/api/v1")
api_router.include_router(orders.router, prefix="/api/v1")
api_router.include_router(planning.router, prefix="/api/v1")
api_router.include_router(driver.router, prefix="/api/v1")
api_router.include_router(tenants.router, prefix="/api/v1")
api_router.include_router(agent_logs.router, prefix="/api/v1")
api_router.include_router(tracking.router, prefix="/api/v1")
api_router.include_router(sla.router, prefix="/api/v1")
api_router.include_router(analytics.router, prefix="/api/v1")
api_router.include_router(agent_suggestions.router, prefix="/api/v1")
api_router.include_router(export.router, prefix="/api/v1")
api_router.include_router(import_orders.router, prefix="/api/v1")
api_router.include_router(fleet.router, prefix="/api/v1")
api_router.include_router(chat.router, prefix="/api/v1")
api_router.include_router(admin.router, prefix="/api/v1")
api_router.include_router(integrations.router, prefix="/api/v1")
api_router.include_router(marketplace.router, prefix="/api/v1")
api_router.include_router(audit.router, prefix="/api/v1")
api_router.include_router(governance.router, prefix="/api/v1")
api_router.include_router(scenarios.router, prefix="/api/v1")
