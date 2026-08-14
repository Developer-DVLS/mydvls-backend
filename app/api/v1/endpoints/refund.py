from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.v1.schemas.refund import PaginatedRefundResponse, RefundCreate, RefundResponse
from app.core.database import get_db
from app.models.orders import Order
from app.models.refunds import Refund, RefundStatus, RefundType
from app.models.user import User
from app.services.refundservice import RefundService
from app.auth.permissions import customer_only
from app.utils.pagination import get_paginated_result


user_refund_router = APIRouter(
    prefix="/user/refunds",
    tags=[" User Refunds"],
)


@user_refund_router.post(
    "/orders/{order_id}/",
    response_model=RefundResponse,
)
async def create_refund_request(
    order_id: int,
    data: RefundCreate,
    current_user: User = Depends(customer_only),
    db: AsyncSession = Depends(get_db),
):
    refund_service = RefundService(db)
    
    # ---------------------------------------------------------
    # Get user's order
    # ---------------------------------------------------------

    result = await db.execute(
        select(Order)
        .where(
            Order.id == order_id,
            Order.user_id == current_user.id,
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
    await refund_service.existing_pending_check(order.id, current_user)

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

    return refund


@user_refund_router.get(
    "/orders/{order_id}/",
    response_model=PaginatedRefundResponse,
)
async def get_user_order_refunds(
    order_id: int,
    current_user: User = Depends(customer_only),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    # Verify order belongs to user
    order_result = await db.execute(
        select(Order)
        .where(
            Order.id == order_id,
            Order.user_id == current_user.id,
        )
    )

    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    query = select(Refund) .where(
            Refund.order_id == order_id,
            Refund.user_id == current_user.id,
        ).order_by(
            Refund.created_at.desc()
        )

    return await get_paginated_result(db, query, skip, limit)

@user_refund_router.get(
    "/{refund_id}/",
    response_model=RefundResponse,
)
async def get_user_refund(
    refund_id: int,
    current_user: User = Depends(customer_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Refund)
        .where(
            Refund.id == refund_id,
            Refund.user_id == current_user.id,
        )
    )

    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=404,
            detail="Refund not found.",
        )

    return refund

@user_refund_router.delete(
    "/{refund_id}",
)
async def cancel_refund_request(
    refund_id: int,
    current_user: User = Depends(customer_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Refund)
        .where(
            Refund.id == refund_id,
            Refund.user_id == current_user.id,
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
                "Only pending refund requests can be cancelled."
            ),
        )

    refund.status = RefundStatus.REJECTED.value
    refund.reason = (
        f"{refund.reason or ''}\n"
        "Cancelled by customer."
    ).strip()

    await db.commit()

    return {
        "message": "Refund request cancelled successfully."
    }