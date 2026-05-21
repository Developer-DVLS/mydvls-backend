from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.carts import CartResponse
from app.core.database import get_db
from app.models.products import Product, ProductVariant
from app.services.cartservice import CartService
from app.services.offerservice import build_offer_indexes, get_all_active_offers, resolve_offer
from app.services.security import get_current_user_optional

cart_router = APIRouter(prefix="/cart", tags=["Cart"])

cart_service = CartService()

@cart_router.get("/", response_model=CartResponse | dict)
async def get_cart(
    request: Request,
    cart_count: Optional[bool] = False,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None
    
    ## to get cart count
    if cart_count:
        return {"cart_count" : await cart_service.cart_count(request=request, db=db, user_id=user_id)}
    
    cart = await cart_service.get_cart(
        request=request,
        db=db,
        user_id=user_id
    )
    
    # calculate totals    
    enriched_cart = await cart_service.enrich_cart(
        db=db,
        cart=cart
    )

    return enriched_cart
    

@cart_router.post("/add-to-cart/")
async def add_to_cart(
    request: Request,
    response: Response,
    product_variant_id: int,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.add(
        request=request,
        response=response,
        db=db,
        product_variant_id=product_variant_id,
        quantity=quantity,
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Item added successfully"
    }

@cart_router.patch("/update-cart-product/{cart_product_id}/")
async def update_cart_product(
    request: Request,
    cart_product_id: int,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.update(
        request=request,
        db=db,  
        quantity=quantity, 
        cart_product_id=cart_product_id, 
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Item updated successfully"
    }


@cart_router.delete("/delete-cart-product/{cart_product_id}/")
async def delete_cart_product(
    request: Request,
    cart_product_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    user_id = user.id if user else None

    await cart_service.remove(
        request=request,
        db=db,  
        cart_product_id=cart_product_id, 
        user_id=user_id
    )
    
    return {
        "status": True,
        "message": "Item deleted successfully"
    }
