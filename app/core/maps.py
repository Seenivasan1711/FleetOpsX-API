from typing import Optional
from app.core.config import settings


async def get_distance_km(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> Optional[float]:
    """
    Returns distance in km via Google Maps Distance Matrix API.
    Returns None if MAPS_API_KEY is not configured (Phase 1 — Haversine used instead).
    """
    if not settings.MAPS_API_KEY:
        return None
    # Phase 2: plug in real Maps API call here
    return None
