import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.orders import OrderCreate
from app.core.database import get_db
from app.models.user import User
from app.services.orderservice import OrderService
from app.services.security import get_current_user_optional

order_router = APIRouter(prefix="/order", tags=['order'])

@order_router.post("/")
async def create_order(
    data: OrderCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Create an order from the customer's current cart.

    - Validates cart has items
    - Creates order with order number
    - Converts cart items to order items
    - Clears cart after order creation
    """
    try:
        order_service = OrderService(db)
        order = await order_service.create_order(
            request=request,
            response=response,
            data=data,
            user=current_user
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    return {
        "message": "Order created successfully",
        "order_id": order.id,
    }
    