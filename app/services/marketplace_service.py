"""
Marketplace service — P4-E3.

Match engine: greedy zone-match (same zone, same date, sufficient drivers).
Auto-archives expired offers/requests.
"""
import logging
from math import ceil
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.marketplace import CapacityOffer, CapacityRequest, CapacityMatch
from app.schemas.marketplace import CapacityOfferIn, CapacityRequestIn

logger = logging.getLogger(__name__)

_DEFAULT_EXPIRY_HOURS = 24   # offers/requests expire after 24h if not set explicitly
_ORDERS_PER_DRIVER    = 12   # assumed throughput for driver-capacity estimation


def create_offer(db: Session, tenant_id: str, data: CapacityOfferIn) -> CapacityOffer:
    offer = CapacityOffer(
        tenant_id    = tenant_id,
        offer_date   = data.offer_date,
        driver_count = data.driver_count,
        vehicle_type = data.vehicle_type,
        zone         = data.zone,
        rate_per_stop= data.rate_per_stop,
        status       = "OPEN",
        expires_at   = datetime.utcnow() + timedelta(hours=_DEFAULT_EXPIRY_HOURS),
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def list_open_offers(db: Session, zone: str | None = None) -> list[CapacityOffer]:
    """Returns all OPEN, non-expired offers (platform-wide, visible to all tenants)."""
    q = select(CapacityOffer).where(
        CapacityOffer.status == "OPEN",
        CapacityOffer.expires_at > datetime.utcnow(),
    )
    if zone:
        q = q.where(CapacityOffer.zone == zone)
    return db.execute(q.order_by(CapacityOffer.created_at.desc())).scalars().all()


def cancel_offer(db: Session, offer_id: str, tenant_id: str) -> CapacityOffer | None:
    offer = db.execute(
        select(CapacityOffer).where(
            CapacityOffer.id == offer_id,
            CapacityOffer.tenant_id == tenant_id,
            CapacityOffer.status == "OPEN",
        )
    ).scalar_one_or_none()
    if offer:
        offer.status = "CANCELLED"
        db.commit()
    return offer


def create_request(db: Session, tenant_id: str, data: CapacityRequestIn) -> CapacityRequest:
    req = CapacityRequest(
        tenant_id    = tenant_id,
        request_date = data.request_date,
        order_count  = data.order_count,
        zone         = data.zone,
        priority     = data.priority.upper(),
        status       = "OPEN",
        expires_at   = datetime.utcnow() + timedelta(hours=_DEFAULT_EXPIRY_HOURS),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def list_my_requests(db: Session, tenant_id: str) -> list[CapacityRequest]:
    return db.execute(
        select(CapacityRequest)
        .where(CapacityRequest.tenant_id == tenant_id)
        .order_by(CapacityRequest.created_at.desc())
    ).scalars().all()


def list_matches(db: Session, tenant_id: str, status: str | None = None) -> list[CapacityMatch]:
    q = select(CapacityMatch).where(
        (CapacityMatch.requesting_tenant_id == tenant_id) |
        (CapacityMatch.offering_tenant_id   == tenant_id)
    )
    if status:
        q = q.where(CapacityMatch.status == status)
    return db.execute(q.order_by(CapacityMatch.created_at.desc())).scalars().all()


def respond_to_match(
    db: Session, match_id: str, tenant_id: str, new_status: str
) -> CapacityMatch | None:
    """Requesting tenant accepts or rejects a match."""
    match = db.execute(
        select(CapacityMatch).where(
            CapacityMatch.id == match_id,
            CapacityMatch.requesting_tenant_id == tenant_id,
            CapacityMatch.status == "PENDING_ACCEPTANCE",
        )
    ).scalar_one_or_none()

    if not match:
        return None

    match.status = new_status
    if new_status == "ACCEPTED":
        match.settled_at = datetime.utcnow()

    db.commit()
    db.refresh(match)
    return match


# ─── Match engine ─────────────────────────────────────────────────────────────

def run_match_engine(db: Session) -> int:
    """Greedy zone-match: runs every 5 min via APScheduler.

    For each OPEN request (HIGH priority first), find an OPEN offer in the same
    zone, same date, with enough drivers. Creates a CapacityMatch and marks both
    offer and request as MATCHED.

    Also auto-archives expired offers/requests.
    Returns number of matches created.
    """
    _archive_expired(db)

    open_requests = db.execute(
        select(CapacityRequest)
        .where(
            CapacityRequest.status == "OPEN",
            CapacityRequest.expires_at > datetime.utcnow(),
        )
        .order_by(
            (CapacityRequest.priority == "HIGH").desc(),
            CapacityRequest.created_at,
        )
    ).scalars().all()

    matched = 0
    for req in open_requests:
        drivers_needed = ceil(req.order_count / _ORDERS_PER_DRIVER)
        offer = db.execute(
            select(CapacityOffer).where(
                and_(
                    CapacityOffer.zone        == req.zone,
                    CapacityOffer.offer_date  == req.request_date,
                    CapacityOffer.status      == "OPEN",
                    CapacityOffer.driver_count >= drivers_needed,
                    CapacityOffer.expires_at  > datetime.utcnow(),
                    CapacityOffer.tenant_id   != req.tenant_id,  # no self-matching
                )
            ).limit(1)
        ).scalar_one_or_none()

        if offer:
            match = CapacityMatch(
                offer_id             = offer.id,
                request_id           = req.id,
                offering_tenant_id   = offer.tenant_id,
                requesting_tenant_id = req.tenant_id,
                matched_orders       = req.order_count,
                status               = "PENDING_ACCEPTANCE",
            )
            db.add(match)
            offer.status = "MATCHED"
            req.status   = "MATCHED"
            db.commit()
            matched += 1
            logger.info(
                "marketplace match: offer=%s → request=%s zone=%s orders=%d",
                offer.id, req.id, req.zone, req.order_count,
            )

    return matched


def _archive_expired(db: Session) -> None:
    now = datetime.utcnow()
    for Model in (CapacityOffer, CapacityRequest):
        expired = db.execute(
            select(Model).where(
                Model.status == "OPEN",
                Model.expires_at <= now,
            )
        ).scalars().all()
        for row in expired:
            row.status = "EXPIRED"
    if expired:
        db.commit()
