from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.productvariants import PaginatedProductVariantResponse, ProductVariantRequest, ProductVariantResponse, ProductVariantUpdate
from app.core.database import get_db
from app.models.products import Product, ProductVariant
from app.models.user import User
from app.auth.permissions import staff_only
from app.utils.pagination import get_paginated_result

admin_variant_router = APIRouter(prefix="/dashboard/product-variant", tags=['Product variant CRUD'])


@admin_variant_router.get('/', response_model=PaginatedProductVariantResponse)
async def list_variants(
    search: Optional[str] = None,
    product_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductVariant).options(
        selectinload(ProductVariant.product),
        selectinload(ProductVariant.attributes),
        selectinload(ProductVariant.images),
    ).order_by(ProductVariant.created_at.desc())
    
    # search by SKU or product name
    if search:
        query = query.join(Product).where(
            or_(
                ProductVariant.sku.ilike(f"%{search}%"),
                Product.name.ilike(f"%{search}%")
            )
        )

    # filter by product
    if product_id is not None:
        query = query.where(ProductVariant.product_id == product_id)

    # boolean filters (IMPORTANT: use is not None)
    if is_active is not None:
        query = query.where(ProductVariant.is_active == is_active)

    if is_featured is not None:
        query = query.where(ProductVariant.is_featured == is_featured)

    return await get_paginated_result(db, query, skip, limit)

@admin_variant_router.get('/{variant_id}', response_model=ProductVariantResponse)
async def get_variant(
    variant_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.product),
            selectinload(ProductVariant.attributes),
            selectinload(ProductVariant.images),
        )
        .where(ProductVariant.id == variant_id)
    )

    variant = result.scalars().first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    return variant

@admin_variant_router.post('/', response_model=ProductVariantResponse)
async def create_variant(
    data: ProductVariantRequest,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # check product exists
    result = await db.execute(
        select(Product).where(Product.id == data.product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_variant = ProductVariant(
        product_id=data.product_id,
        sku=data.sku,
        price=data.price,
        cost_price=data.cost_price,
        margin=data.margin,
        stock_quantity=data.stock_quantity,
        is_active=data.is_active,
        is_featured=data.is_featured,
    )

    db.add(new_variant)
    await db.commit()

    # IMPORTANT: reload with relationships
    result = await db.execute(
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.product),
            selectinload(ProductVariant.attributes),
            selectinload(ProductVariant.images),
        )
        .where(ProductVariant.id == new_variant.id)
    )

    variant = result.scalars().first()

    return variant



@admin_variant_router.put('/{variant_id}', response_model=ProductVariantResponse)
async def update_variant(
    variant_id: int,
    data: ProductVariantUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductVariant).where(ProductVariant.id == variant_id)
    )
    variant = result.scalars().first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # validate product if updating
    if data.product_id is not None:
        product = await db.execute(
            select(Product).where(Product.id == data.product_id)
        )
        if not product.scalars().first():
            raise HTTPException(status_code=404, detail="Product not found")

    # update only provided fields
    if data.product_id is not None:
        variant.product_id = data.product_id
    if data.sku is not None:
        variant.sku = data.sku
    if data.price is not None:
        variant.price = data.price
    if data.cost_price is not None:
        variant.cost_price = data.cost_price
    if data.margin is not None:
        variant.margin = data.margin
    if data.stock_quantity is not None:
        variant.stock_quantity = data.stock_quantity
    if data.is_active is not None:
        variant.is_active = data.is_active
    if data.is_featured is not None:
        variant.is_featured = data.is_featured

    await db.commit()

    # 🔥 reload with relationships (IMPORTANT)
    result = await db.execute(
        select(ProductVariant)
        .options(selectinload(ProductVariant.product),
                selectinload(ProductVariant.attributes),
                selectinload(ProductVariant.images))
        .where(ProductVariant.id == variant.id)
    )

    return result.scalars().first()

@admin_variant_router.delete('/{variant_id}')
async def delete_variant(
    variant_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductVariant).where(ProductVariant.id == variant_id)
    )
    variant = result.scalars().first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    await db.delete(variant)
    await db.commit()

    return {
        "status": True,
        "message": "Variant deleted successfully"
    }