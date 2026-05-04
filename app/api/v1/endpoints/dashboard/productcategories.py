
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.productcategories import CategoryRequest, CategoryResponse, CategoryUpdateRequest, PaginatedCategoryResponse
from app.core.database import get_db
from app.models.products import ProductCategory
from app.models.user import User
from app.auth.permissions import staff_only
from app.utils.pagination import get_paginated_result
from app.api.v1.endpoints.shop import shop_router

admin_product_category_router = APIRouter(prefix="/dashboard/product_category", tags=['Product category CRUD'])
product_category_router = APIRouter(prefix="/product-category", tags=['Product api'])

@product_category_router.get('/', response_model=PaginatedCategoryResponse)
async def list_category(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductCategory).order_by(ProductCategory.ordering.asc())
    
    if search:
        query = query.where(
            ProductCategory.name.ilike(f"%{search}%"),
        )
    
    if is_active is not None:
        query = query.where(ProductCategory.is_active == is_active)
    if is_featured is not None:
        query = query.where(ProductCategory.is_featured == is_featured)
        
    
    return await get_paginated_result(db, query, skip, limit)

@admin_product_category_router.get('/{category_id}/', response_model=CategoryResponse)
async def get_category(
    category_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):        
    result = await db.execute(select(ProductCategory))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Product category not found")
    
    return category

@admin_product_category_router.post('/', response_model=CategoryResponse)
async def create_category(
    data: CategoryRequest,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # check if category already exists (optional but recommended)
    result = await db.execute(
        select(ProductCategory).where(func.lower(ProductCategory.name) == data.name.lower())
    )
    existing_category = result.scalars().first()

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )

    # create new category
    new_category = ProductCategory(
        name=data.name,
        description=data.description,
        image_url=data.image_url,
        is_active=data.is_active,
        is_featured=data.is_featured,
        ordering=data.ordering
    )

    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    return new_category
    

@admin_product_category_router.patch('/{category_id}', response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdateRequest,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # fetch category
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.id == category_id)
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    # check duplicate name only if name is being updated
    if "name" in update_data and update_data["name"] != category.name:
        existing = await db.execute(
            select(ProductCategory).where(
                ProductCategory.name == update_data["name"]
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )

    # apply only provided fields
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    return category

@admin_product_category_router.delete('/{category_id}')
async def delete_category(
    category_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # fetch category
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.id == category_id)
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # delete category
    await db.delete(category)
    await db.commit()

    return {
        "status": True,
        "message": "Category deleted successfully"
    }