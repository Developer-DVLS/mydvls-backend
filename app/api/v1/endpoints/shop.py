from datetime import datetime
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.offers import ComboOfferDetailResponse, ComboOfferResponse, PaginatedComboOfferResponse
from app.api.v1.schemas.shop import PaginatedShopProductResponse, ShopProductDetailResponse
from app.core.database import get_db
from app.models.offers import ComboOffer, ComboOfferItem, OfferType
from app.models.products import Product, ProductVariant, VariantOption, VariantOptionValue
from app.services.offerservice import build_offer_indexes, get_all_active_offers, resolve_offer, valid_combo_offers
from app.services.shopservice import ShopService
from app.utils.cache import get_cache, set_cache
from app.utils.pagination import get_paginated_result


shop_router = APIRouter(prefix="/shop", tags=['shop'])

PRODUCT_CACHE_KEY = "products:list"

shop_service = ShopService()

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
    
    # ---------------------------------------------------------
    # 1. Get complete product data from cache
    # ---------------------------------------------------------
    cached_data = await get_cache(PRODUCT_CACHE_KEY)

    if cached_data:
        products_data = json.loads(cached_data)

    else:
        # -----------------------------------------------------
        # 2. Cache miss -> get ALL active products
        #    IMPORTANT: Do NOT apply search/category/featured
        #    filters here.
        # -----------------------------------------------------
        query = (
            select(Product)
            .options(
                selectinload(Product.variants)
                .selectinload(ProductVariant.images)
            )
            .where(
                Product.deleted_at.is_(None),
                Product.is_active.is_(True),
                Product.variants.any(
                    ProductVariant.is_active.is_(True)
                )
            )
            .order_by(Product.created_at.desc())
        )

        result = await db.execute(query)

        products = result.scalars().unique().all()

        # -----------------------------------------------------
        # 3. Get active offers
        # -----------------------------------------------------
        offers = await get_all_active_offers(db)

        bogo_map, item_map, category_map, store_offer = (
            build_offer_indexes(offers)
        )

        # -----------------------------------------------------
        # 4. Build complete product response
        # -----------------------------------------------------
        products_data = []

        for product in products:

            # Only active variants
            active_variants = [
                variant
                for variant in product.variants
                if variant.is_active
            ]

            if not active_variants:
                continue

            # -------------------------------------------------
            # Best applicable offer
            # -------------------------------------------------
            applicable_offers = shop_service.collect_applicable_offers(
                product,
                item_map,
                category_map,
                store_offer
            )

            best_offer = shop_service.pick_best_offer(
                applicable_offers
            )

            best_offer_data = None

            if best_offer:
                best_offer_data = {
                    "id": best_offer.id,
                    "name": best_offer.name,
                    "code": best_offer.code,
                    "type": best_offer.type,
                    "discount_type": best_offer.discount_type,
                    "discount_value": best_offer.discount_value,
                }

            # -------------------------------------------------
            # Get price from active variants
            # -------------------------------------------------
            price = min(
                variant.price
                for variant in active_variants
            )

            # -------------------------------------------------
            # Get image from active variants
            # -------------------------------------------------
            image_url = None

            for variant in active_variants:
                if variant.images:
                    image_url = variant.images[0].image_url
                    break

            products_data.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "is_featured": product.is_featured,
                "price": str(price),
                "image_url": image_url,
                "category_id": product.category_id,
                "best_offer": best_offer_data,
            })

        # -----------------------------------------------------
        # 5. Cache the COMPLETE unfiltered product list
        # -----------------------------------------------------
        await set_cache(
            PRODUCT_CACHE_KEY,
            json.dumps(products_data),
            expire=900  # 15 minutes
        )

    # ---------------------------------------------------------
    # 6. Apply filters AFTER getting complete cached data
    # ---------------------------------------------------------
    filtered = products_data

    # Search
    if search:
        search_value = search.strip().lower()

        filtered = [
            product
            for product in filtered
            if search_value in product["name"].lower()
        ]

    # Category
    if category_id is not None:
        filtered = [
            product
            for product in filtered
            if product["category_id"] == category_id
        ]

    # Featured
    if is_featured is not None:
        filtered = [
            product
            for product in filtered
            if product["is_featured"] == is_featured
        ]

    # ---------------------------------------------------------
    # 7. Pagination AFTER filtering
    # ---------------------------------------------------------
    total = len(filtered)

    paginated = filtered[
        skip: skip + limit
    ]

    # ---------------------------------------------------------
    # 8. Return response
    # ---------------------------------------------------------
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": paginated,
    }


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
            selectinload(Product.category),
            selectinload(Product.variants)
            .selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option),
            selectinload(Product.variant_options)
            .selectinload(VariantOption.values)
        )
        .where(
            Product.id == product_id,
            Product.is_active == True,
            Product.variants.any(ProductVariant.is_active == True),
            Product.deleted_at.is_(None),
        )
    )
    
    result = query.scalars().first()
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # first get all active offers
    offers = await get_all_active_offers(db)
    
    if offers:
        # Build indexes
        bogo_map, item_map, category_map, store_offer = build_offer_indexes(offers)
        
        for variant in result.variants:
            
            best_offer = resolve_offer(
                variant,
                item_map,
                category_map,
                store_offer,
                bogo_map
            )
            
            best_offer_data = None
            if best_offer:
                if best_offer.type in (OfferType.ITEM, OfferType.CATEGORY, OfferType.STORE):
                    best_offer_data = {
                        "id": best_offer.id,
                        "name": best_offer.name,
                        "code": best_offer.code,
                        "type": best_offer.type,
                        "discount_type": best_offer.discount_type,
                        "discount_value":best_offer.discount_value
                    } 
                elif best_offer.type == OfferType.BOGO:
                    get_item_result = await db.execute(
                        select(ProductVariant)
                        .options(selectinload(ProductVariant.product))
                        .where(
                            ProductVariant.id == best_offer.bogo_meta.get_item_id,
                            ProductVariant.deleted_at.is_(None)
                            )
                    )
                    get_item = get_item_result.scalars().first()
                    
                    best_offer_data = {
                        "id": best_offer.id,
                        "name": best_offer.name,
                        "code": best_offer.code,
                        "type": best_offer.type,
                        "bogo_meta": {
                            "id": best_offer.bogo_meta.id,
                            "apply_to_same_item": best_offer.bogo_meta.apply_to_same_item,
                            "buy_quantity": best_offer.bogo_meta.buy_quantity,
                            "buy_item_id": best_offer.bogo_meta.buy_item_id,
                            "get_quantity": best_offer.bogo_meta.get_quantity,
                            "get_item_id": best_offer.bogo_meta.get_item_id,
                            "get_item": {
                                "id": get_item.id,
                                "sku": get_item.sku,
                                "price": get_item.price,
                                "product": {
                                    "id": get_item.product.id,
                                    "name": get_item.product.name,
                                    "description": get_item.product.description
                                }
                            }
                        }
                    }
            variant.best_offer = best_offer_data
    
    return result


@shop_router.get("/combo-offers/", response_model=PaginatedComboOfferResponse)
async def list_combo_offer(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.utcnow()
    
    query = (
        select(ComboOffer)
        .options(
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant).selectinload(ProductVariant.product)
        )
        .where(
            ComboOffer.is_active == True,
            ComboOffer.start_date <= now,
            ComboOffer.end_date >= now,
            ComboOffer.deleted_at.is_(None),
        )
        .order_by(ComboOffer.priority)
    )
    
    return await get_paginated_result(db, query, skip, limit)

@shop_router.get("/combo-offers/{offer_id}/", response_model=ComboOfferDetailResponse)
async def list_combo_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db)
):
    now = datetime.utcnow()
    
    result = await db.execute(
        select(ComboOffer)
        .options(
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.product),
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.attributes),
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.images),
        )
        .where(
            ComboOffer.id == offer_id,
            ComboOffer.is_active == True,
            ComboOffer.start_date <= now,
            ComboOffer.end_date >= now,
            ComboOffer.deleted_at.is_(None),
        )
        .order_by(ComboOffer.priority)
    )
    combo_offer = result.scalars().first()
    if not combo_offer:
        raise HTTPException(
            status_code= 404,
            detail="Combo offer not found"
        )
    
    return combo_offer