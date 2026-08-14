from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class RefundCreate(BaseModel):
    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
    )
    reason: str | None = None


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class RefundReject(BaseModel):
    reason: str = Field(
        ...,
        min_length=1,
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class RefundResponse(BaseModel):
    id: int

    order_id: int

    user_id: UUID | None
    processed_by_id: UUID | None

    refund_type: str
    status: str

    amount: Decimal
    original_amount: Decimal
    previous_refunded_amount: Decimal

    reason: str | None

    original_transaction_id: str | None
    refund_transaction_id: str | None

    card_last4: str | None

    gateway_response_code: str | None
    gateway_error: str | None

    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True
    )
    
class PaginatedRefundResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[RefundResponse]] = None

    class Config:
        from_attributes = True