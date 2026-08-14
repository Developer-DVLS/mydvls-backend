
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.v1.schemas.refund import PaginatedRefundResponse, RefundCreate, RefundReject, RefundResponse
from app.core.database import get_db
from app.models.orders import Order
from app.models.refunds import Refund, RefundStatus, RefundType
from app.models.user import User
from app.services.paymentservice import PaymentService
from app.services.refundservice import RefundService
from app.auth.permissions import admin_only
from app.utils.pagination import get_paginated_result

admin_refund_router = APIRouter(
    prefix="/dashboard/refunds",
    tags=["Admin Refunds"],
)

@admin_refund_router.get(
    "/",
    response_model=PaginatedRefundResponse,
)
async def admin_get_refunds(
    status: str | None = None,
    order_id: int | None = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    query = (
        select(Refund)
        .order_by(
            Refund.created_at.desc()
        )
    )

    if status:
        query = query.where(
            Refund.status == status
        )

    if order_id:
        query = query.where(
            Refund.order_id == order_id
        )

    return await get_paginated_result(db, query, skip, limit)


@admin_refund_router.get(
    "/{refund_id}/",
    response_model=RefundResponse,
)
async def admin_get_refund(
    refund_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    result = await db.execute(
        select(Refund)
        .where(
            Refund.id == refund_id
        )
    )

    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=404,
            detail="Refund not found.",
        )

    return refund

@admin_refund_router.post(
    "/{refund_id}/reject/",
    response_model=RefundResponse,
)
async def admin_reject_refund(
    refund_id: int,
    data: RefundReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    result = await db.execute(
        select(Refund)
        .where(
            Refund.id == refund_id
        )
        .with_for_update()
    )

    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=404,
            detail="Refund not found.",
        )

    if refund.status != RefundStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only pending refunds can be rejected."
            ),
        )

    refund.status = RefundStatus.REJECTED.value

    refund.processed_by_id = current_user.id

    refund.reason = data.reason

    refund.processed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(refund)

    return refund


@admin_refund_router.post(
    "/{refund_id}/process",
    response_model=RefundResponse,
)
async def admin_process_refund(
    refund_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    # ---------------------------------------------------------
    # Lock refund row
    # ---------------------------------------------------------

    result = await db.execute(
        select(Refund)
        .where(
            Refund.id == refund_id
        )
        .with_for_update()
    )

    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=404,
            detail="Refund not found.",
        )

    # ---------------------------------------------------------
    # Prevent duplicate processing
    # ---------------------------------------------------------

    if refund.status != RefundStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Refund is already {refund.status}."
            ),
        )

    # ---------------------------------------------------------
    # Validate Authorize.Net information
    # ---------------------------------------------------------

    if not refund.original_transaction_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Original Authorize.Net "
                "transaction ID not found."
            ),
        )

    if not refund.card_last4:
        raise HTTPException(
            status_code=400,
            detail="Card last four digits not found.",
        )

    # ---------------------------------------------------------
    # Mark processing
    # ---------------------------------------------------------

    refund.status = RefundStatus.PROCESSING.value

    refund.processed_by_id = current_user.id

    refund.processed_at = datetime.utcnow()

    await db.commit()

    # ---------------------------------------------------------
    # Authorize.Net
    # ---------------------------------------------------------

    try:
        authorize_net = PaymentService()

        response = await authorize_net.refund(
            amount=refund.amount,
            original_transaction_id=(
                refund.original_transaction_id
            ),
            card_last4=refund.card_last4,
        )
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        # We genuinely don't know if Authorize.Net processed this.
        # Do NOT mark as FAILED — that invites a duplicate refund.
        refund.status = RefundStatus.PENDING_RECONCILIATION.value
        refund.gateway_error = f"No response from gateway: {exc}"
        await db.commit()
        raise HTTPException(
            status_code=502,
            detail="Refund status unknown, pending reconciliation.",
        )

    except Exception as exc:
        refund.status = RefundStatus.FAILED.value
        refund.gateway_error = str(exc)
        await db.commit()

        raise HTTPException(
            status_code=502,
            detail="Authorize.Net refund request failed.",
        )

    # ---------------------------------------------------------
    # Parse Authorize.Net response
    # ---------------------------------------------------------

    transaction_response = response.get("transactionResponse", {})
    response_code = transaction_response.get("responseCode")
    top_level_messages = response.get("messages", {})

    # ---------------------------------------------------------
    # Success / Failure
    # ---------------------------------------------------------

    if response_code == "1":
        refund.status = RefundStatus.SUCCEEDED.value
        refund.refund_transaction_id = (
            transaction_response.get("transId")
        )
        refund.gateway_response_code = (
            response_code
        )
        refund.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(refund)

        return refund
    elif response_code == "4":
        refund.status = RefundStatus.PENDING_REVIEW.value
        refund.gateway_response_code = response_code
        refund.gateway_error = str(
            transaction_response.get("errors")
            or transaction_response.get("messages")
            or "Held for review"
        )
    else:
        refund.status = RefundStatus.FAILED.value
        refund.gateway_response_code = response_code
        refund.gateway_error = str(
            transaction_response.get("errors")
            or transaction_response.get("messages")
            or top_level_messages.get("message")
            or "Unknown gateway error"
        )

    await db.commit()
    await db.refresh(refund)

    return refund