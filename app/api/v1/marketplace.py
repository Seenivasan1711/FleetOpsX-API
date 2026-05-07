"""
Capacity Marketplace endpoints — P4-E3.

POST   /marketplace/offers               → post excess capacity
GET    /marketplace/offers               → browse open offers (platform-wide)
DELETE /marketplace/offers/{id}          → cancel own offer
POST   /marketplace/requests             → request coverage
GET    /marketplace/requests             → list own requests
GET    /marketplace/matches              → list matches involving this tenant
PATCH  /marketplace/matches/{id}         → accept or reject a match
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.user import User
from app.schemas.marketplace import (
    CapacityOfferIn, CapacityOfferOut,
    CapacityRequestIn, CapacityRequestOut,
    CapacityMatchOut, MatchRespondIn,
)
from app.services.marketplace_service import (
    create_offer, list_open_offers, cancel_offer,
    create_request, list_my_requests,
    list_matches, respond_to_match,
)

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])

_VALID_RESPOND = {"ACCEPTED", "REJECTED"}


# ─── Offers ───────────────────────────────────────────────────────────────────

@router.post("/offers", response_model=CapacityOfferOut, status_code=201)
def post_offer(
    body: CapacityOfferIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Post excess capacity to the marketplace."""
    return create_offer(db=db, tenant_id=str(current_user.tenant_id), data=body)


@router.get("/offers", response_model=list[CapacityOfferOut])
def browse_offers(
    zone: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_dispatcher),
):
    """Browse all OPEN offers on the platform (platform-wide view)."""
    return list_open_offers(db=db, zone=zone)


@router.delete("/offers/{offer_id}", status_code=204)
def cancel_my_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    result = cancel_offer(db=db, offer_id=str(offer_id), tenant_id=str(current_user.tenant_id))
    if not result:
        raise HTTPException(status_code=404, detail="Offer not found or already matched/cancelled")


# ─── Requests ─────────────────────────────────────────────────────────────────

@router.post("/requests", response_model=CapacityRequestOut, status_code=201)
def post_request(
    body: CapacityRequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Request additional delivery capacity from the marketplace."""
    return create_request(db=db, tenant_id=str(current_user.tenant_id), data=body)


@router.get("/requests", response_model=list[CapacityRequestOut])
def my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """List this tenant's capacity requests."""
    return list_my_requests(db=db, tenant_id=str(current_user.tenant_id))


# ─── Matches ──────────────────────────────────────────────────────────────────

@router.get("/matches", response_model=list[CapacityMatchOut])
def my_matches(
    status: Optional[str] = Query(None, description="PENDING_ACCEPTANCE | ACCEPTED | REJECTED | COMPLETED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """List matches where this tenant is either offering or requesting capacity."""
    return list_matches(db=db, tenant_id=str(current_user.tenant_id), status=status)


@router.patch("/matches/{match_id}", response_model=CapacityMatchOut)
def respond_match(
    match_id: UUID,
    body: MatchRespondIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dispatcher),
):
    """Requesting tenant accepts or rejects an incoming match."""
    if body.status not in _VALID_RESPOND:
        raise HTTPException(status_code=400, detail=f"status must be one of {_VALID_RESPOND}")

    result = respond_to_match(
        db=db, match_id=str(match_id),
        tenant_id=str(current_user.tenant_id),
        new_status=body.status,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Match not found or already responded")
    return result


@router.post("/match-now", status_code=202)
def trigger_match_engine(
    db: Session = Depends(get_db),
    _user: User = Depends(require_dispatcher),
):
    """Manually trigger the match engine (normally runs every 5 min automatically)."""
    from app.services.marketplace_service import run_match_engine
    count = run_match_engine(db)
    return {"matches_created": count}
