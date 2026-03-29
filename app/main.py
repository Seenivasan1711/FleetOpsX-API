import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.core.middleware import TenantMiddleware
from app.api.router import api_router
from app.workers.scheduler import start_scheduler, stop_scheduler

# Configure Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FleetOpsX API starting up...")
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("FleetOpsX API shut down")


app = FastAPI(title="FleetOpsX API", lifespan=lifespan)

# Configure Prometheus
Instrumentator().instrument(app).expose(app)

# Configure CORS (outermost middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant middleware (runs after CORS)
app.add_middleware(TenantMiddleware)

app.include_router(api_router)
