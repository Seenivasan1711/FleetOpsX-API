from fastapi import APIRouter
from app.api import health
from app.api.v1 import auth, depots, drivers, vehicles, customers, orders, planning

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(depots.router, prefix="/api/v1")
api_router.include_router(drivers.router, prefix="/api/v1")
api_router.include_router(vehicles.router, prefix="/api/v1")
api_router.include_router(customers.router, prefix="/api/v1")
api_router.include_router(orders.router, prefix="/api/v1")
api_router.include_router(planning.router, prefix="/api/v1")
# Driver view router added in P1-E6:
# api_router.include_router(driver.router, prefix="/api/v1")
