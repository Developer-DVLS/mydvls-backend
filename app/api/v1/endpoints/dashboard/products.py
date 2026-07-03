
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.api.v1.schemas.products import CreateNestedProductWithVariantOption, CreateVariantOption, CreateVariantOptionValue, NestedProductResponse, PaginatedProductResponse, ProductCreateRequest, ProductDropdown, ProductRequest, ProductResponse, ProductUpdate, VariantOptionDropdownResponse, VariantOptionResponse, VariantOptionUpdate, VariantOptionValueResponse, VariantOptionValueUpdate
from app.core.database import get_db
from app.models.products import Product, ProductCategory, ProductVariant, VariantOption, VariantOptionValue
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


@admin_product_router.delete('/{product_id}/')
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

    product.is_active = False
    await db.commit()

    return {
        "status": True,
        "message": "Product inactivated."
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


@admin_product_router.post('/product_with_variant_options')
async def create_product_with_variant_options(
    data: CreateNestedProductWithVariantOption,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    try:
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
        await db.flush()

        #create variant-options
        if data.variant_options:
            for variant_option in data.variant_options:
                new_variant_option = VariantOption(
                    product_id = new_product.id,
                    name = variant_option.name,
                    is_active = variant_option.is_active,
                    description = variant_option.description or None if "description" in variant_option else None
                )
                db.add(new_variant_option)
                await db.flush()
                
                # create variant-option values 
                for value in variant_option.values:
                    variant_option_value = VariantOptionValue(
                        option_id = new_variant_option.id,
                        value = value.value,
                        is_active = value.is_active,
                        description = value.description or None if "description" in value else None
                    )
                    db.add(variant_option_value)
                    await db.flush()

        await db.commit()
        await db.refresh(new_product)
    except IntegrityError as e:
        await db.rollback()
        error = str(e.orig)
        
        if "uq_product_option" in error:
            raise HTTPException(
                status_code=400,
                detail="Option already exists for this product."
            )

        if "uq_option_value" in error:
            raise HTTPException(
                status_code=400,
                detail="Option value already exists."
            )
        
        raise HTTPException(
            status_code=400,
            detail="Database integrity error."
        )
    
    return {
        "status": True,
        "message": "Product created successfully."
    }

# -----------------------------
# VARIANT OPTION  CRUD 
# -----------------------------
    
@product_router.get('/variant-option/', response_model=List[VariantOptionResponse])
async def list_variant_options(
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(VariantOption).order_by(VariantOption.created_at.desc())
        
    if product_id:
        query = query.where(
            VariantOption.product_id == product_id
        )
        
    result = await db.execute(query)
    options = result.scalars().all()
    return options

@product_router.get('/variant-option/dropdown/', response_model=List[VariantOptionDropdownResponse])
async def variant_options_dropdown(
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(VariantOption).order_by(VariantOption.created_at.desc())
        
    if product_id:
        query = query.where(
            VariantOption.product_id == product_id
        )
        
    result = await db.execute(query)
    options = result.scalars().all()
    return options

@product_router.get('/variant-option/{variant_option_id}/', response_model=VariantOptionResponse)
async def get_variant_option(
    variant_option_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VariantOption)
        .where(VariantOption.id == variant_option_id)
    )
    option = result.scalars().first()
    
    if not option:
        raise HTTPException(
            status_code=404, 
            detail="Variant Option not found"
        )
    return option

@admin_product_router.post('/variant-option/')
async def create_variant_option(
    data: CreateVariantOption,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    # -----------------------------
    # DUPLICATE VALIDATION
    # -----------------------------
    if data.name:
        existing_option = await db.execute(
            select(VariantOption).where(
                VariantOption.product_id == data.product_id,
                VariantOption.name == data.name
            )
        )

        duplicate = existing_option.scalars().first()

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Option '{data.name}' already exists for this product."
            )
    
    #create variant option
    new_variant_option = VariantOption(
        product_id = data.product_id,
        name = data.name,
        is_active = data.is_active,
        description = data.description or None if "description" in data else None
    )
    db.add(new_variant_option)
    await db.commit()
    
    return {
        "status": True,
        "message": "Variant option created successfully."
    }

@admin_product_router.patch('/variant-option/{variant_option_id}/')
async def update_variant_option(
    variant_option_id: int,
    data: VariantOptionUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VariantOption)
        .where(VariantOption.id == variant_option_id)
    )
    option = result.scalars().first()
    
    if not option:
        raise HTTPException(
            status_code=404, 
            detail="Variant Option not found"
        )
    
    # -----------------------------
    # DUPLICATE VALIDATION
    # -----------------------------
    if data.name:
        existing_option = await db.execute(
            select(VariantOption).where(
                VariantOption.product_id == option.product_id,
                VariantOption.name == data.name,
                VariantOption.id != variant_option_id
            )
        )

        duplicate = existing_option.scalars().first()

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Option '{data.name}' already exists for this product."
            )
    
    # -----------------------------
    # APPLY UPDATES
    # -----------------------------
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(option, field, value)

    await db.commit()
    await db.refresh(option)
    
    return {
        "status": True,
        "message": "Variant option updated successfully."
    }
    
@admin_product_router.delete('/variant-option/{variant_option_id}/')
async def delete_variant_option(
    variant_option_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VariantOption)
        .where(VariantOption.id == variant_option_id)
    )
    option = result.scalars().first()
    
    if not option:
        raise HTTPException(
            status_code=404, 
            detail="Variant Option not found"
        )
    
    await db.delete(option)
    await db.commit()
    
    return {
        "status": True,
        "message": "Variant option deleted successfully."
    }

# -----------------------------
# VARIANT OPTION VALUE CRUD 
# -----------------------------
@product_router.get('/variant-option-value/', response_model=List[VariantOptionValueResponse])
async def list_variant_option_values(
    option_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query =  select(VariantOptionValue).order_by(VariantOptionValue.created_at.desc())
    
    if option_id:
        query = query.where(
            VariantOptionValue.option_id == option_id
        )
        
    result = await db.execute(query)
    option_values = result.scalars().all()
    return option_values

@product_router.get('/variant-option-value/{variant_option_value_id}/', response_model=VariantOptionValueResponse)
async def get_variant_option_value(
    variant_option_value_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VariantOptionValue)
        .where(VariantOptionValue.id == variant_option_value_id)
    )
    option_value = result.scalars().first()
    
    if not option_value:
        raise HTTPException(
            status_code=404, 
            detail="Variant Option not found"
        )
    return option_value 

@admin_product_router.post('/variant-option-value/')
async def create_variant_option_value(
    data: CreateVariantOptionValue,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    # -----------------------------
    # DUPLICATE VALIDATION
    # -----------------------------
    if data.value:
        existing_option_value = await db.execute(
            select(VariantOptionValue).where(
                VariantOptionValue.option_id == data.option_id,
                VariantOptionValue.value == data.value
            )
        )

        duplicate = existing_option_value.scalars().first()

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Option value '{data.value}' already exists for this product variant option."
            )
    
    #create variant option value
    new_variant_option_value = VariantOptionValue(
        option_id = data.option_id,
        value = data.value,
        is_active = data.is_active,
        description = data.description or None if "description" in data else None
    )
    db.add(new_variant_option_value)
    await db.commit()
    
    return {
        "status": True,
        "message": "Variant option value created successfully."
    }
    
@admin_product_router.patch('/variant-option-value/{variant_option_value_id}/')
async def update_variant_option_values(
    variant_option_value_id: int,
    data: VariantOptionValueUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VariantOptionValue)
        .where(VariantOptionValue.id == variant_option_value_id)
    )
    option_value = result.scalars().first()
    
    if not option_value:
        raise HTTPException(
            status_code=404, 
            detail="Variant Option not found"
        )
        
    # -----------------------------
    # DUPLICATE CHECK
    # -----------------------------
    if data.value:
        existing_value = await db.execute(
            select(VariantOptionValue).where(
                VariantOptionValue.option_id == option_value.option_id,
                VariantOptionValue.value == data.value,
                VariantOptionValue.id != variant_option_value_id
            )
        )

        duplicate = existing_value.scalars().first()

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Value '{data.value}' already exists for this option."
            )
        
    # -----------------------------
    # APPLY UPDATES
    # -----------------------------
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(option_value, field, value)

    await db.commit()
    await db.refresh(option_value)
    
    return {
        "status": True,
        "message": "Variant option value updated successfully."
    }
    
@admin_product_router.delete('/variant-option-value/{variant_option_value_id}/')
async def delete_variant_option_values(
    variant_option_value_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(VariantOptionValue)
        .where(VariantOptionValue.id == variant_option_value_id)
    )
    option_value = result.scalars().first()
    
    if not option_value:
        raise HTTPException(
            status_code=404, 
            detail="Variant Option not found"
        )
        
    await db.delete(option_value)
    await db.commit()
    
    return {
        "status": True,
        "message": "Variant option value deleted successfully."
    }