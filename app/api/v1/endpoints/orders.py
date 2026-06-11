import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.orders import OrderCreate, OrderDetailResponse
from app.api.v1.schemas.payment import ChargeRequest
from app.core.database import get_db
from app.models.carts import CartStatus
from app.models.orders import Order
from app.models.user import User
from app.services.orderservice import OrderService
from app.services.paymentservice import PaymentService
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
        # 1. Create order in DB with status "pending"
        order_service = OrderService(db)
        order = await order_service.create_order(
            request=request,
            response=response,
            data=data,
            user=current_user
        )
        
        #2. Attempt charge
        payment_service = PaymentService()
        payment_payload = {
            "opaqueDataDescriptor": data.opaqueDataDescriptor,
            "opaqueDataValue": data.opaqueDataValue,
            "amount": order.total
        }
        result = await payment_service.charge_card(payment=payment_payload)
        
        #3. Update order payment status
        order.payment_intent_id = result["transactionId"]
        order.payment_status = "paid"
        order.payment_method = "authorizenet"
        
        #4. update cart status
        order.cart.status = CartStatus.ORDERED
        
        await db.commit()
        await db.refresh(order) 
        
        return {
            "order_id": order.id, 
            "order_number": order.order_number,
            "status": "paid",
            "transaction_id": result["transactionId"],
            "auth_code": result["authCode"],
            }
        
    except ValueError as e:
        raise HTTPException(
            status_code=402,
            detail=str(e)
        )
    except Exception as e:
        
        raise HTTPException(
            status_code=402, 
            detail=str(e)
            )

@order_router.get("/order/{order_number}/", response_model=OrderDetailResponse)
async def get_order_by_order_number(
    order_number: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .where(Order.order_number == order_number)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    return order

from app.core.config import settings
@order_router.get("get_token")
async def get_test_nonce():
    payload = {
        "securePaymentContainerRequest": {
            "merchantAuthentication": {
                "name": settings.API_LOGIN_ID,
                "transactionKey": settings.TRANSACTION_KEY,
            },
            "data": {
                "type": "TOKEN",
                "id": "test-request-1",
                "token": {
                    "cardNumber": "4111111111111111",
                    "expirationDate": "1226",
                    "cardCode": "123",
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(settings.ENDPOINT_URL, json=payload)
    
    data = response.json()
    opaque = data["opaqueData"]
    print(opaque["dataDescriptor"])  # use this as opaqueDataDescriptor
    print(opaque["dataValue"]) 
    
@order_router.post("/api/charge")
async def charge_card(payload: ChargeRequest):
    payment_service = PaymentService()
    response = await payment_service.charge_card(payment=payload)
    return response