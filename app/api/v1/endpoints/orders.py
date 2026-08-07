import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.orders import OrderCreate, OrderDetailResponse
from app.api.v1.schemas.payment import ChargeRequest
from app.core.database import get_db
from app.models.carts import Cart, CartProduct, CartStatus
from app.models.offers import ComboOffer, ComboOfferItem, Offer
from app.models.orders import AppliedCombo, Order, OrderItem
from app.models.products import Product, ProductVariant, VariantOption, VariantOptionValue
from app.models.user import User
from app.services.cartservice import CartService
from app.services.orderservice import OrderService
from app.services.paymentservice import PaymentService
from app.services.security import get_current_user_optional
from app.utils.cache import delete_cache, get_cache

order_router = APIRouter(prefix="/order", tags=['order'])

SESSION_COOKIE_KEY = "guest_cart"

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
            "amount": order.total,
            "order_number": order.order_number,
            "receiver_email": order.receiver_email
        }
        result = await payment_service.charge_card(payment=payment_payload)
        
        #3. Update order payment status
        order.payment_intent_id = result["transactionId"]
        order.payment_status = "paid"
        order.payment_method = "authorizenet"
                
        #4. update cart status
        # if cart exists in order, it means it is registered user's order else guest user
        # so delete redis cart
        if order.cart_id:
            order.cart.status = CartStatus.ORDERED
        else:
            # get redis cache key from cookie
            redis_cache_key = request.cookies.get(SESSION_COOKIE_KEY)
            if redis_cache_key:
                # delete cart from redis cache
                await delete_cache(redis_cache_key)
                # delete cart cookie
                response.delete_cookie(key=SESSION_COOKIE_KEY)

        #5. update inventory
        for ordered_item in order.items:
            product_variant = ordered_item.product_variant
            #update
            product_variant.stock_quantity -= ordered_item.quantity
        
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
    order_number: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items)
        )
        .where(Order.order_number == order_number)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    return order

@order_router.get("/invoice/{order_number}/")
async def get_invoice(
    request: Request,
    response: Response,
    order_number: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            
            selectinload(Order.items)
            .selectinload(OrderItem.product_variant)
            .selectinload(ProductVariant.product),
            
            selectinload(Order.items)
            .selectinload(OrderItem.product_variant)
            .selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option),
        
            selectinload(Order.applied_combos)
            .selectinload(AppliedCombo.combo_offer)
            .selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.product),
            
            selectinload(Order.applied_combos)
            .selectinload(AppliedCombo.combo_offer)
            .selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option)
        
        )
        .where(Order.order_number == order_number)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )
    
    # ----------------------------
    # STEP 1: index items
    # ----------------------------

    breakdown = [
        {
            "order_item_id": item.id,
            "product_variant_id": item.product_variant_id,
            "quantity": item.quantity,
            "combo_quantity": 0,
            "normal_quantity": item.quantity,
            "product_variant": {
                "id": item.product_variant.id,
                "sku": item.product_variant.sku,
                "price": item.product_variant.price,
                "variant_options": [{
                    "id": variant_option_value.id,
                    "value": variant_option_value.value,
                    "variant_option": {
                        "id": variant_option_value.variant_option.id,
                        "name": variant_option_value.variant_option.name,
                        }
                }
                    for variant_option_value in item.product_variant.variant_options
                ],
                "product": {
                    "id": item.product_variant.product.id,
                    "name": item.product_variant.product.name
                }
            }
        }
        for item in order.items
    ]
    
    breakdown_map = {
        row["product_variant_id"]: row
        for row in breakdown
    }

    # ----------------------------
    # STEP 2: process combos
    # ----------------------------
    for combo in order.applied_combos:
        combo_offer = combo.combo_offer
        combo_qty = combo.quantity_used

        for c_item in combo_offer.items:
            product_variant_id = c_item.product_variant_id
            required_qty = c_item.quantity

            if product_variant_id not in breakdown_map:
                continue

            order_item = breakdown_map[product_variant_id]

            # find or create row
            row = next(
                (r for r in breakdown if r["order_item_id"] == order_item.id),
                None
            )

            if not row:
                row = {
                    "order_item_id": order_item.id,
                    "product_variant_id": product_variant_id,
                    "quantity": order_item.quantity,
                    "combo_quantity": 0,
                    "normal_quantity": order_item.quantity,
                    "unit_price": order_item.unit_price,
                    "total_price": order_item.total_price,
                    "product_variant": {
                        "id": c_item.product_variant.id,
                        "sku": c_item.product_variant.sku,
                        "price": c_item.product_variant.price,
                        "variant_options": [{
                            "id": variant_option_value.id,
                            "value": variant_option_value.value,
                            "variant_option": {
                                "id": variant_option_value.variant_option.id,
                                "name": variant_option_value.variant_option.name,
                                }
                        }
                            for variant_option_value in c_item.product_variant.variant_options
                        ],
                        "product":{
                            "id":c_item.product_variant.product.id,
                            "name":c_item.product_variant.product.name
                            }
                    }
                }
                breakdown.append(row)

            # allocate combo qty
            row["combo_quantity"] += combo_qty * required_qty

    # ----------------------------
    # STEP 3: finalize
    # ----------------------------
    for row in breakdown:
        row["normal_quantity"] = max(
            0,
            row["quantity"] - row["combo_quantity"]
        )

    # ----------------------------
    # STEP 4: build final invoice
    # ----------------------------
    invoice = {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": str(order.user_id),

        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "discount_amount": float(order.discount_amount),
        "delivery_charge": float(order.delivery_charge),
        "total": float(order.total),

        "status": order.status,
        "currency": order.currency,
        "notes": order.notes,
        
        "receiver_first_name": order.receiver_first_name,
        "receiver_last_name": order.receiver_last_name,
        "receiver_email": order.receiver_email,
        "receiver_phone": order.receiver_phone,
        
        "address_line1": order.address_line1,
        "address_line2": order.address_line2,
        "city": order.city,
        "state": order.state,
        "postal_code": order.postal_code,
        "country": order.country,
        "latitude": order.latitude,
        "longitude": order.longitude,
        
        "delivery_distance": order.delivery_distance,
        "delivery_status": order.delivery_status,
        "payment_intent_id": order.payment_intent_id,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        
        "items": breakdown,
        "applied_combos": [
            {
                "combo_offer_id": c.combo_offer_id,
                "quantity_used": c.quantity_used,
                "discount_amount": float(c.discount_amount),
                "combo_offer": {
                    "name": c.combo_offer.name,
                    "discount_type": c.combo_offer.discount_type,
                    "discount_value": c.combo_offer.discount_value,
                    "items": [{
                        "product_variant_id": item.product_variant_id,
                        "quantity": item.quantity,
                        "product_variant": {
                            "id": item.product_variant.id,
                            "sku": item.product_variant.sku,
                            "price": item.product_variant.price,
                            "product":{
                                "id":item.product_variant.product.id,
                                "name":item.product_variant.product.name
                                }
                        }
                    }
                        for item in c.combo_offer.items
                    ]
                }
            }
            for c in order.applied_combos
        ],
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "confirmed_at": order.confirmed_at,
        "completed_at": order.completed_at,
        "cancelled_at": order.cancelled_at,
    }

    return invoice

# from app.core.config import settings
# @order_router.get("get_token")
# async def get_test_nonce():
#     payload = {
#         "securePaymentContainerRequest": {
#             "merchantAuthentication": {
#                 "name": settings.API_LOGIN_ID,
#                 "transactionKey": settings.TRANSACTION_KEY,
#             },
#             "data": {
#                 "type": "TOKEN",
#                 "id": "test-request-1",
#                 "token": {
#                     "cardNumber": "4111111111111111",
#                     "expirationDate": "1226",
#                     "cardCode": "123",
#                 }
#             }
#         }
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.post(settings.ENDPOINT_URL, json=payload)
    
#     data = response.json()
#     opaque = data["opaqueData"]
#     print(opaque["dataDescriptor"])  # use this as opaqueDataDescriptor
#     print(opaque["dataValue"]) 
    
# @order_router.post("/api/charge")
# async def charge_card(payload: ChargeRequest):
#     payment_service = PaymentService()
#     response = await payment_service.charge_card(payment=payload)
#     return response