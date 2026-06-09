from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.orders import OrderDetailResponse, OrderStatusUpdate, PaginatedOrderResponse
from app.core.database import get_db
from app.models.orders import Order, OrderStatus
from app.models.user import User
from app.utils.pagination import get_paginated_result
from app.auth.permissions import staff_only

admin_order_router = APIRouter(prefix="/dashboard/order", tags=['Admin Order'])
@admin_order_router.get("/", response_model=PaginatedOrderResponse)
async def list_orders(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    query = select(Order).order_by(Order.created_at)
    
    return await get_paginated_result(db, query, skip, limit)

@admin_order_router.get("/{order_id}/", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items)
        )
        .where(Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail='Order not found.'
        )
    
    return order

@admin_order_router.patch("/{order_id}/status/")
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    VALID_TRANSITIONS = {
        OrderStatus.PENDING: [
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.CONFIRMED: [
            OrderStatus.PREPARING,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.PREPARING: [
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED,
        ],
        OrderStatus.COMPLETED: [
            OrderStatus.REFUNDED,
        ],
        OrderStatus.CANCELLED: [],
        OrderStatus.REFUNDED: [],
    }

    
    current_status = order.status
    new_status = data.status
    
    # Same status check
    if current_status == new_status:
        return {
            "message": "Order already has this status",
            "order_id": order.id,
            "status": order.status,
        }
        
    # Transition validation
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change order status from "
                f"'{current_status.value}' to '{new_status.value}'"
            )
        )

    order.status = new_status
    
    await db.commit()
    await db.refresh(order)

    return {
        "message": "Order status updated successfully",
        "order_id": order.id,
        "status": order.status,
    }