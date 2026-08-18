
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


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
        .options(selectinload(Refund.order))
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
    # process refund in Authorize.Net
    # ---------------------------------------------------------

    refund_service = RefundService(db)
    refund = await refund_service.process_refund(refund)

    return refund


@admin_refund_router.post(
    "/orders/{order_id}/",
    response_model=RefundResponse,
)
async def create_process_refund_request(
    order_id: int,
    data: RefundCreate,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    refund_service = RefundService(db)
    
    # ---------------------------------------------------------
    # Get order
    # ---------------------------------------------------------

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.user))
        .where(
            Order.id == order_id
        )
    )

    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )
    
    # ---------------------------------------------------------
    # Check for existing pending refund
    # ---------------------------------------------------------
    await refund_service.existing_pending_check(order.id, order.user)

    # ---------------------------------------------------------
    # Validate order/payment
    # ---------------------------------------------------------

    if order.payment_status != "paid":
        raise HTTPException(
            status_code=400,
            detail="Only paid orders can be refunded.",
        )

    if not order.payment_intent_id:
        raise HTTPException(
            status_code=400,
            detail="Payment transaction not found.",
        )

    # ---------------------------------------------------------
    # Calculate previous successful refunds
    # ---------------------------------------------------------
    
    previous_refunded = (
        await refund_service.get_previous_refunded_amount(
            order.id
        )
    )

    original_amount = Decimal(
        str(order.total)
    )

    remaining_amount = (
        original_amount - previous_refunded
    )

    # ---------------------------------------------------------
    # Validate refund amount
    # ---------------------------------------------------------

    if data.amount > remaining_amount:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "refund_amount_exceeded",
                "message": (
                    f"Maximum refundable amount is "
                    f"{remaining_amount:.2f}."
                ),
            },
        )

    # ---------------------------------------------------------
    # Determine full / partial
    # ---------------------------------------------------------

    refund_type = (
        RefundType.FULL.value
        if data.amount == remaining_amount
        else RefundType.PARTIAL.value
    )
    
    # ---------------------------------------------------------
    # Get card number
    # ---------------------------------------------------------
    card_info = await refund_service.get_refund_card_info(
        order.payment_intent_id
    )

    card_last4 = card_info["card_last4"]

    # ---------------------------------------------------------
    # Create refund
    # ---------------------------------------------------------

    refund = Refund(
        order_id=order.id,

        user_id=current_user.id,

        refund_type=refund_type,

        status=RefundStatus.PENDING.value,

        amount=data.amount,

        original_amount=original_amount,

        previous_refunded_amount=previous_refunded,

        original_transaction_id=(
            order.payment_intent_id
        ),

        card_last4=card_last4,

        reason=data.reason,
    )

    db.add(refund)

    await db.commit()
    await db.refresh(refund)
    
    # ---------------------------------------------------------
    # Process refund
    # ---------------------------------------------------------
    
    refund_result = await db.execute(
        select(Refund)
        .options(
            selectinload(Refund.order)
            )
        .where(Refund.id == refund.id)
    )
    refund = refund_result.scalars().first()
    

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
    # process refund in Authorize.Net
    # ---------------------------------------------------------

    refund_service = RefundService(db)
    refund = await refund_service.process_refund(refund)

    return refund