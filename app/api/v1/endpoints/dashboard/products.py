
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.products import NestedProductResponse, PaginatedProductResponse, ProductCreateRequest, ProductDropdown, ProductRequest, ProductResponse, ProductUpdate
from app.core.database import get_db
from app.models.products import Product, ProductCategory, ProductVariant
from app.models.user import User
from app.auth.permissions import staff_only
from app.utils.pagination import get_paginated_result


admin_product_router = APIRouter(prefix="/dashboard/product", tags=['Product CRUD'])
product_router = APIRouter(prefix="/product", tags=['Product api'])

@product_router.get('/', response_model=PaginatedProductResponse)
async def list_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).order_by(Product.created_at.desc())

    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if is_active is not None:
        query = query.where(Product.is_active == is_active)

    if is_featured is not None:
        query = query.where(Product.is_featured == is_featured)

    result = await db.execute(query.options(
            selectinload(Product.category)
        )
    )

    return await get_paginated_result(db, query, skip, limit)

# lightweight api for dropdown options 
# it returns id and name field only
@product_router.get('/options', response_model=List[ProductDropdown])
async def list_product_options(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).order_by(Product.created_at.desc())

    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if is_active is not None:
        query = query.where(Product.is_active == is_active)

    if is_featured is not None:
        query = query.where(Product.is_featured == is_featured)

    result = await db.execute(query.options(
            selectinload(Product.category)
        )
    )

    return result.scalars().all()


@admin_product_router.get('/{product_id}', response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@admin_product_router.post('/', response_model=ProductResponse)
async def create_product(
    data: ProductRequest,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # optional: check category exists
    category_result = await db.execute(
        select(ProductCategory).where(ProductCategory.id == data.category_id)
    )
    category = category_result.scalars().first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    new_product = Product(
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        is_active=data.is_active,
        is_featured=data.is_featured,
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    
    # reload with relationship
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == new_product.id)
    )
    product = result.scalars().first()

    return product

@admin_product_router.patch('/{product_id}', response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = data.model_dump(exclude_unset=True)

    # validate category only if provided
    if "category_id" in update_data:
        cat = await db.execute(
            select(ProductCategory).where(
                ProductCategory.id == update_data["category_id"]
            )
        )
        if not cat.scalars().first():
            raise HTTPException(status_code=404, detail="Category not found")

    # apply only provided fields
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    # reload with relationship
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product.id)
    )
    product = result.scalars().first()

    return product


@admin_product_router.delete('/{product_id}')
async def delete_product(
    product_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()

    return {
        "status": True,
        "message": "Product deleted successfully"
    }
    
# nested api tp create product and its variant as once
@admin_product_router.post('/product-with-variants', response_model=NestedProductResponse)
async def create_product_with_variants(
    data: ProductCreateRequest,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # 1. validate category
    category = await db.execute(
        select(ProductCategory).where(ProductCategory.id == data.category_id)
    )
    if not category.scalars().first():
        raise HTTPException(status_code=404, detail="Category not found")

    # 2. create product
    product = Product(
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        is_active=data.is_active,
        is_featured=data.is_featured,
    )

    db.add(product)
    await db.flush()  # 🔥 get product.id before commit

    # 3. create variants
    variant_objects = []

    for v in data.variants:
        variant = ProductVariant(
            product_id=product.id,
            sku=v.sku,
            price=v.price,
            cost_price=v.cost_price,
            margin=v.margin,
            stock_quantity=v.stock_quantity,
            is_active=v.is_active,
            is_featured=v.is_featured,
        )
        db.add(variant)
        variant_objects.append(variant)

    # 4. commit all at once
    await db.commit()

    # 5. reload with relationships (VERY IMPORTANT)
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == product.id)
    )

    return result.scalars().first()