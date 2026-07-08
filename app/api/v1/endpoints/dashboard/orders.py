from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.orders import OrderDeliveryStatusUpdate, OrderDetailResponse, OrderStatusUpdate, PaginatedOrderResponse
from app.core.database import get_db
from app.models.orders import DeliveryStatus, Order, OrderStatus
from app.models.user import User
from app.utils.pagination import get_paginated_result
from app.auth.permissions import staff_only

admin_order_router = APIRouter(prefix="/dashboard/order", tags=['Admin Order'])
@admin_order_router.get("/", response_model=PaginatedOrderResponse)
async def list_orders(
    user_id: Optional[UUID] = None,
    created_at: Optional[datetime] = None,
    cart_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    delivery_status: Optional[DeliveryStatus] = None,
    search: Optional[str] = Query(
        None, 
        description="search by ordernumber, receiver-info, address-info, payment-method"
        ),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    query = select(Order).order_by(Order.created_at.desc())
    
    if user_id:
        query = query.where(Order.user_id == user_id)
    if created_at:
        query = query.where(func.date(Order.created_at) == created_at.date())
    if cart_id:
        query = query.where(Order.cart_id == cart_id)
    if status:
        query = query.where(Order.status == status)
    if delivery_status:
        query = query.where(Order.delivery_status == delivery_status)
    
    #search query
    if search:
        query = query.where(
            or_(
            Order.order_number == search,
            
            Order.receiver_first_name.ilike(f"%{search}%"),
            Order.receiver_last_name.ilike(f"%{search}%"),
            func.concat(
                Order.receiver_first_name,
                " ",
                Order.receiver_last_name
            ).ilike(f"%{search}%"),
            Order.receiver_email == search,
            Order.receiver_phone.ilike(f"%{search}%"),
            
            Order.address_line1.ilike(f"%{search}%"),
            Order.address_line2.ilike(f"%{search}%"),
            Order.city.ilike(f"%{search}%"),
            Order.state.ilike(f"%{search}%"),
            Order.postal_code.ilike(f"%{search}%"),
            Order.country.ilike(f"%{search}%"),
            
            Order.payment_method == search
            )
            
        )
    
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
    
@admin_order_router.delete("/{order_id:int}/")
async def delete_order(
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
    await db.delete(order)
    await db.commit()
    
    return {
        "status": True,
        "message": "Order deleted successfully"
    }
    
@admin_order_router.patch("/{order_id}/delivery-status/")
async def update_delivery_status(
    order_id: int,
    data: OrderDeliveryStatusUpdate,
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
        DeliveryStatus.PENDING_ASSIGNMENT: [
            DeliveryStatus.DRIVER_ASSIGNED,
            DeliveryStatus.FAILED,
        ],
        DeliveryStatus.DRIVER_ASSIGNED: [
            DeliveryStatus.PICKED_UP,
            DeliveryStatus.FAILED,
        ],
        DeliveryStatus.PICKED_UP: [
            DeliveryStatus.ON_THE_WAY,
            DeliveryStatus.RETURNED,
            DeliveryStatus.FAILED,
        ],
        DeliveryStatus.ON_THE_WAY: [
            DeliveryStatus.DELIVERED,
            DeliveryStatus.RETURNED,
            DeliveryStatus.FAILED,
        ],
        DeliveryStatus.DELIVERED: [],
        DeliveryStatus.FAILED: [
            DeliveryStatus.PENDING_ASSIGNMENT,  # Optional: retry delivery
        ],
        DeliveryStatus.RETURNED: [],
    }

    
    current_status = order.delivery_status
    new_status = data.delivery_status
    
    # Same status check
    if current_status == new_status:
        return {
            "message": "Order already has this status",
            "order_id": order.id,
            "delivery_status": order.delivery_status,
        }
        
    # Transition validation
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change order delivery status from "
                f"'{current_status.value}' to '{new_status.value}'"
            )
        )

    order.delivery_status = new_status
    
    await db.commit()
    await db.refresh(order)

    return {
        "message": "Order delivery status updated successfully",
        "order_id": order.id,
        "status": order.delivery_status,
    }