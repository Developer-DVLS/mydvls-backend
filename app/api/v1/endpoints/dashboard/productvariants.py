from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.productvariants import CreateProductVariantImage, PaginatedProductVariantResponse, ProductAttributeCreate, ProductAttributeMini, ProductAttributeRequest, ProductAttributeResponse, ProductAttributeUpdate, ProductVariantDropdown, ProductVariantImageBase, ProductVariantImageResponse, ProductVariantRequest, ProductVariantResponse, ProductVariantUpdate
from app.core.database import get_db
from app.models.products import Product, ProductAttribute, ProductVariant, ProductVariantImage, VariantOptionValue
from app.models.user import User
from app.auth.permissions import staff_only
from app.utils.pagination import get_paginated_result

admin_variant_router = APIRouter(prefix="/dashboard/product-variant", tags=['Product variant CRUD'])
product_variant_router = APIRouter(prefix="/product-variant", tags=['Product api'])


@product_variant_router.get('/', response_model=PaginatedProductVariantResponse)
async def list_variants(
    search: Optional[str] = None,
    product_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductVariant).join(Product).options(
        selectinload(ProductVariant.product),
        selectinload(ProductVariant.attributes),
        selectinload(ProductVariant.images),
        selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option)
    ).where(
        ProductVariant.deleted_at.is_(None),
        Product.deleted_at.is_(None),
        ProductVariant.deleted_at.is_(None),
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

@product_variant_router.get('/options', response_model=List[ProductVariantDropdown])
async def list_variants_options(
    search: Optional[str] = None,
    product_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ProductVariant).join(Product).options(
        selectinload(ProductVariant.product)
    ).where(
        ProductVariant.deleted_at.is_(None),
        Product.deleted_at.is_(None),
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

    result = await db.execute(query)
    return result.scalars().all()

@product_variant_router.get('/{variant_id}', response_model=ProductVariantResponse)
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
            selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option)
        )
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.deleted_at.is_(None)
            )
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
        select(Product).where(
            Product.id == data.product_id,
            Product.deleted_at.is_(None))
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # check if sku already exists
    sku_exists_result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.sku == data.sku.lower(),
            ProductVariant.deleted_at.is_(None)
            )
    )
    sku_exists = sku_exists_result.scalars().first()
    
    if sku_exists:
        raise HTTPException(status_code=409, detail="Product variant with same SKU already exists")
    
    ## check if there is any variant options 
    variant_options = []
    if data.variant_option_value_ids:
        ids = data.variant_option_value_ids or []

        result = await db.execute(
            select(VariantOptionValue).where(
                VariantOptionValue.deleted_at.is_(None),
                VariantOptionValue.id.in_(ids)
            )
        )
        variant_options = result.scalars().all()
        if not variant_options:
            raise HTTPException(status_code=409, detail="Invalid variant option value.")

    new_variant = ProductVariant(
        product_id=data.product_id,
        sku=data.sku.lower(), #already save lowercase
        price=data.price,
        cost_price=data.cost_price,
        margin=data.margin,
        stock_quantity=data.stock_quantity,
        is_active=data.is_active,
        is_featured=data.is_featured,
        description=data.description or None if "description" in data else None,
        features=data.features or None if "features" in data else None
    )
    
    ##assign variant-option
    new_variant.variant_options = variant_options

    db.add(new_variant)
    await db.commit()

    # create images
    if data.variant_images:
        for image in data.variant_images:
            db.add(
                ProductVariantImage(
                    variant_id=new_variant.id,
                    image_url=image.image_url
                )
            )

    await db.commit()
    
    # create attributes
    if data.attributes:
        for attribute in data.attributes:
            db.add(
                ProductAttribute(
                    variant_id=new_variant.id,
                    key=attribute.key,
                    value=attribute.value
                )
            )

    await db.commit()
    
    # reload with relationships
    result = await db.execute(
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.product),
            selectinload(ProductVariant.attributes),
            selectinload(ProductVariant.images),
            selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option)
        )
        .where(ProductVariant.id == new_variant.id)
    )

    variant = result.scalars().first()

    return variant


@admin_variant_router.patch('/{variant_id}', response_model=ProductVariantResponse)
async def update_variant(
    variant_id: int,
    data: ProductVariantUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.variant_options)
        )
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.deleted_at.is_(None)
            )
    )
    variant = result.scalars().first()

    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    update_data = data.model_dump(exclude_unset=True)

    # validate product only if provided
    if "product_id" in update_data:
        product_result = await db.execute(
            select(Product).where(
                Product.id == update_data["product_id"],
                Product.deleted_at.is_(None)
                )
        )
        if not product_result.scalars().first():
            raise HTTPException(status_code=404, detail="Product not found")
    
    #sku must be unique
    if "sku" in update_data:
        existing = await db.execute(
            select(ProductVariant).where(
                ProductVariant.sku == update_data["sku"],
                ProductVariant.id != variant_id,
                ProductVariant.deleted_at.is_(None)
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="SKU already exists"
            )

    # apply only provided fields
    for field, value in update_data.items():
        setattr(variant, field, value)
        
    if "variant_option_value_ids" in update_data:
        ids = update_data["variant_option_value_ids"] or []

        result = await db.execute(
            select(VariantOptionValue).where(
                VariantOptionValue.deleted_at.is_(None),
                VariantOptionValue.id.in_(ids)
            )
        )

        variant_values = result.scalars().all()

        if len(variant_values) != len(ids):
            raise HTTPException(400, "Invalid variant option values")

        # clear old relations
        variant.variant_options.clear()

        # assign new ones
        variant.variant_options = variant_values

    await db.commit()

    # reload with relationships
    result = await db.execute(
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.product),
            selectinload(ProductVariant.attributes),
            selectinload(ProductVariant.images),
            selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option),
            selectinload(ProductVariant.variant_options)
            .selectinload(VariantOptionValue.variant_option)
        )
        .where(ProductVariant.id == variant.id)
    )

    return result.scalars().first()

@admin_variant_router.delete('/{variant_id}/')
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

    # Variant attributes
    if variant.attributes:
        for attribute in variant.attributes:
            attribute.deleted_at = datetime.utcnow()
            await db.commit()
                            
    variant.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Variant deleted."
    }

# add product variant image
@admin_variant_router.post('/image/', response_model=ProductVariantImageResponse)
async def create_image(
    data: CreateProductVariantImage,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    
    image = ProductVariantImage(
        variant_id = data.variant_id,
        image_url = data.image_url
    )

    db.add(image)
    await db.commit()

    return image
    

# delete variant image 
@admin_variant_router.delete('/image/{image_id}/')
async def delete_image(
    image_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductVariantImage).where(ProductVariantImage.id == image_id)
    )
    image = result.scalars().first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    await db.delete(image)
    await db.commit()

    return {
        "status": True,
        "message": "Image deleted successfully"
    }
    
    
# product attribute 
@admin_variant_router.post('/attribute/', response_model=ProductAttributeResponse)
async def create_attribute(
    data: ProductAttributeCreate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    attribute = ProductAttribute(
        variant_id = data.variant_id,
        key = data.key,
        value = data.value
    )

    db.add(attribute)
    await db.commit()

    return attribute

@admin_variant_router.patch('/attribute/{attribute_id}/', response_model=ProductAttributeMini)
async def update_attribute(
    attribute_id: int,
    data: ProductAttributeUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductAttribute).where(ProductAttribute.id == attribute_id)
    )
    attribute = result.scalars().first()

    if not attribute:
        raise HTTPException(status_code=404, detail="Product attribute not found")

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(attribute, field, value)

    await db.commit()
    await db.refresh(attribute)

    return attribute
    
@admin_variant_router.delete('/attribute/{attribute_id}/')
async def delete_attribute(
    attribute_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductAttribute).where(ProductAttribute.id == attribute_id)
    )
    attribute = result.scalars().first()

    if not attribute:
        raise HTTPException(status_code=404, detail="Product attribute not found")

    attribute.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Product attribute deleted successfully"
    }