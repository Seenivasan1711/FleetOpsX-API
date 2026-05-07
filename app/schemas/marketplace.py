from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import date, datetime


class CapacityOfferIn(BaseModel):
    offer_date:    date
    driver_count:  int
    zone:          str
    vehicle_type:  Optional[str] = None
    rate_per_stop: Optional[float] = None


class CapacityOfferOut(BaseModel):
    id:            UUID4
    tenant_id:     UUID4
    offer_date:    date
    driver_count:  int
    vehicle_type:  Optional[str]
    zone:          str
    rate_per_stop: Optional[float]
    status:        str
    expires_at:    datetime
    created_at:    Optional[datetime] = None

    model_config = {"from_attributes": True}


class CapacityRequestIn(BaseModel):
    request_date: date
    order_count:  int
    zone:         str
    priority:     str = "NORMAL"


class CapacityRequestOut(BaseModel):
    id:           UUID4
    tenant_id:    UUID4
    request_date: date
    order_count:  int
    zone:         str
    priority:     str
    status:       str
    expires_at:   datetime
    created_at:   Optional[datetime] = None

    model_config = {"from_attributes": True}


class CapacityMatchOut(BaseModel):
    id:                   UUID4
    offer_id:             UUID4
    request_id:           UUID4
    offering_tenant_id:   UUID4
    requesting_tenant_id: UUID4
    matched_orders:       int
    status:               str
    settled_at:           Optional[datetime] = None
    created_at:           Optional[datetime] = None

    model_config = {"from_attributes": True}


class MatchRespondIn(BaseModel):
    status: str   # ACCEPTED | REJECTED
