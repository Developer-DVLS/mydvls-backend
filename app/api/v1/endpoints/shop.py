from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.shop import PaginatedShopProductResponse, ShopProductDetailResponse
from app.core.database import get_db
from app.models.products import Product, ProductVariant
from app.utils.pagination import get_paginated_result


shop_router = APIRouter(prefix="/shop", tags=['shop'])

# @shop_router.get("/",response_model=ShopResponse)
# async def shop(
#     category_id: Optional[int] = None,
#     search: Optional[str] = None,
#     db:  AsyncSession = Depends(get_db)
# ):
#     products_data = []
#     categories = []

#     # ---------------------------------
#     # ONLY fetch products if needed
#     # ---------------------------------
#     products = []

#     if category_id or search:

#         product_query = (
#             select(Product)
#             .options(
#                 selectinload(Product.variants).selectinload(ProductVariant.images),
#                 selectinload(Product.category)
#             )
#             .where(Product.is_active == True)
#         )

#         if category_id:
#             product_query = product_query.where(
#                 Product.category_id == category_id
#             )

#         if search:
#             search_pattern = f"%{search}%"
#             product_query = product_query.where(
#                 or_(
#                     Product.name.ilike(search_pattern),
#                     Product.description.ilike(search_pattern)
#                 )
#             )

#         result = await db.execute(product_query)
#         products = result.scalars().all()

#         # build products response
#         for product in products:
#             first_variant = product.variants[0] if product.variants else None

#             products_data.append({
#                 "id": product.id,
#                 "name": product.name,
#                 "description": product.description,
#                 "price": first_variant.price if first_variant else None,
#                 "image_url": (
#                     first_variant.images[0].image_url
#                     if first_variant and first_variant.images
#                     else None
#                 )
#             })

#     # ---------------------------------
#     # categories ONLY if products exist OR no filters
#     # ---------------------------------
#     category_query = select(ProductCategory).where(
#         ProductCategory.is_active == True
#     )

#     if search:
#         # restrict categories to those having matching products
#         category_query = category_query.join(Product).where(
#             Product.is_active == True,
#             or_(
#                 Product.name.ilike(f"%{search}%"),
#                 Product.description.ilike(f"%{search}%")
#             )
#         ).distinct()

#     category_result = await db.execute(category_query)
#     categories = category_result.scalars().all()

#     return {
#         "categories": categories,
#         "products": products_data
#     }

@shop_router.get('/products', response_model=PaginatedShopProductResponse)
async def shop_products_list(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    is_featured: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.is_active == True).order_by(Product.created_at.desc())

    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if is_featured is not None:
        query = query.where(Product.is_featured == is_featured)

    return await get_paginated_result(db, query, skip, limit)
    

@shop_router.get("/product-detail/{product_id}/",response_model=ShopProductDetailResponse)
async def product_detail(
    product_id: int,
    db:  AsyncSession = Depends(get_db)
):
    query = await db.execute(
        select(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.images),
            selectinload(Product.variants).selectinload(ProductVariant.attributes),
            selectinload(Product.category)
        )
        .where(
            Product.id == product_id,
            Product.is_active == True,
            Product.variants.any(ProductVariant.is_active == True)
        )
    )
    
    result = query.scalars().first()
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return result