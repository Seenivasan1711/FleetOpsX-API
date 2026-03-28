import logging
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
def health():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}
