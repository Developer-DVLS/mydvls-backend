from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.taxes import PaginatedTaxConfigResponse, TaxConfigCreate, TaxConfigResponse, TaxConfigUpdate
from app.models.tax import TaxConfig, TaxScope
from app.models.user import User
from app.auth.permissions import staff_only
from app.core.database import get_db
from app.services.taxservice import TaxService
from app.utils.pagination import get_paginated_result


tax_router = APIRouter(prefix="/dashboard/tax-config", tags=['Tax CRUD'])

@tax_router.post("/", response_model=TaxConfigResponse)
async def create_delivery_config(
    data: TaxConfigCreate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    tax_service = TaxService(db)
    if await tax_service.tax_code_exists(data.code):
        raise HTTPException(
            status_code=400,
            detail="Tax code already exists"
        )

    tax_config = TaxConfig(
        name = data.name,
        code = data.code,
        tax_scope = data.tax_scope,
        tax_percentage = data.tax_percentage,
        description = data.description,
        is_active = data.is_active
    )
    db.add(tax_config)
    await db.commit()
    await db.refresh(tax_config)
    
    return tax_config

@tax_router.get("/", response_model=PaginatedTaxConfigResponse)
async def list_tax_config(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    is_active: Optional[bool] = None,
    code: Optional[str] = None,
    tax_scope: Optional[TaxScope] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(TaxConfig)
    
    if is_active is not None:
        query = query.where(TaxConfig.is_active == is_active)
    if code:
        query = query.where(TaxConfig.code == code) 
    if tax_scope:
        query = query.where(TaxConfig.tax_scope == tax_scope)
        
    return await get_paginated_result(db, query, skip, limit)

@tax_router.get("/{tax_id:int}", response_model=TaxConfigResponse)
async def get_tax_config(
    tax_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaxConfig)
        .where(TaxConfig.id == tax_id)
        ) 
    
    tax_config = result.scalars().first()
    if not tax_config:
        raise HTTPException(
            status_code=404,
            detail="Tax config not found"
        )
        
    return tax_config

@tax_router.patch("/{tax_id:int}", response_model=TaxConfigResponse)
async def update_tax_config(
    tax_id: int,
    data: TaxConfigUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaxConfig)
        .where(TaxConfig.id == tax_id)
        ) 
    
    tax_config = result.scalars().first()
    if not tax_config:
        raise HTTPException(
            status_code=404,
            detail="Tax config not found"
        )
    
    # code uniqueness
    tax_service = TaxService(db)
    if await tax_service.tax_code_exists(data.code, exclude_id=tax_id):
        raise HTTPException(
            status_code=400,
            detail="Tax code already exists"
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tax_config, field, value)

    await db.commit()
    await db.refresh(tax_config)
        
    return tax_config


@tax_router.delete("/{tax_id:int}")
async def delete_tax_config(
    tax_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaxConfig)
        .where(TaxConfig.id == tax_id)
        ) 
    
    tax_config = result.scalars().first()
    if not tax_config:
        raise HTTPException(
            status_code=404,
            detail="Tax config not found"
        )
    
    await db.delete(tax_config)
    await db.commit()
        
    return {
        "status": True,
        "message": "Tax config deleted successfully"
    }