from fastapi import APIRouter
from app.api import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
# Domain routers added here in P1-E3:
# api_router.include_router(depots.router, prefix="/api/v1")
# api_router.include_router(drivers.router, prefix="/api/v1")
# api_router.include_router(vehicles.router, prefix="/api/v1")
# api_router.include_router(orders.router, prefix="/api/v1")
# api_router.include_router(customers.router, prefix="/api/v1")
