from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.admincart import CartDetailResponse, CartProductResponse, CartProductUpdate, PaginatedCartResponse
from app.models.carts import Cart, CartProduct, CartStatus
from app.models.user import User
from app.utils.pagination import get_paginated_result
from app.auth.permissions import staff_only
from app.core.database import get_db

admin_cart_router = APIRouter(prefix="/dashboard/cart", tags=['Admin Cart'])

@admin_cart_router.get("/", response_model=PaginatedCartResponse)
async def list_carts(
    user_id: Optional[UUID] = None,
    status: Optional[CartStatus] = None,
    created_at: Optional[datetime] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    query = select(
        Cart
        ).where(
            Cart.deleted_at.is_(None)
            ).order_by(
                Cart.created_at.desc()
                )
    
    if user_id:
        query = query.where(Cart.user_id == user_id)
    if status:
        query = query.where(Cart.status == status)
    if created_at:
        query = query.where(func.date(Cart.created_at) == created_at.date())
    
    return await get_paginated_result(db, query, skip, limit)

@admin_cart_router.get("/{cart_id:int}/", response_model=CartDetailResponse)
async def get_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(Cart)
        .options(
            selectinload(Cart.cart_products)
        )
        .where(
            Cart.id == cart_id,
            Cart.deleted_at.is_(None)
            )
    )
    cart = result.scalars().first()
    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Cart not found."
        )
    
    return cart

@admin_cart_router.delete("/{cart_id:int}/")
async def soft_delete_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(Cart)
        .options(
            selectinload(Cart.cart_products)
        )
        .where(Cart.id == cart_id)
    )
    cart = result.scalars().first()
    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Cart not found."
        )
        
    # soft delete 
    if cart.cart_products:
        for product in cart.cart_products:
            product.deleted_at = datetime.utcnow()
    cart.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Cart deleted successfully"
    }

@admin_cart_router.patch("/cart-product/{cart_product_id:int}/", response_model=CartProductResponse)
async def update_cart_product(
    cart_product_id: int,
    data: CartProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(CartProduct)
        .where(CartProduct.id == cart_product_id)
    )
    cart_product = result.scalars().first()
    if not cart_product:
        raise HTTPException(
            status_code=404,
            detail="Cart product not found."
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cart_product, field, value)

    return cart_product

@admin_cart_router.delete("/cart-product/{cart_product_id:int}/")
async def soft_delete_cart_product(
    cart_product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(CartProduct)
        .where(CartProduct.id == cart_product_id)
    )
    cart_product = result.scalars().first()
    if not cart_product:
        raise HTTPException(
            status_code=404,
            detail="Cart product not found."
        )
    
    #soft delete
    cart_product.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Cart product deleted successfully"
    }