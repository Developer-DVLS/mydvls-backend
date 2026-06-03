from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.delivery import DeliveryConfigResponse, DeliveryConfigCreate, DeliveryConfigUpdate, PaginatedDeliveryConfigResponse
from app.models.delivery import DeliveryConfig
from app.models.user import User
from app.auth.permissions import staff_only
from app.core.database import get_db
from app.utils.pagination import get_paginated_result

delivery_router = APIRouter(prefix="/dashboard/delivery-config", tags=['Delivery CRUD'])


@delivery_router.post("/", response_model=DeliveryConfigResponse)
async def create_delivery_config(
    data: DeliveryConfigCreate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    delivery_config = DeliveryConfig(
        min_distance = data.min_distance,
        max_distance = data.max_distance,
        delivery_fee = data.delivery_fee,
        is_active = data.is_active
    )
    db.add(delivery_config)
    await db.commit()
    await db.refresh(delivery_config)
    
    return delivery_config

@delivery_router.get("/", response_model=PaginatedDeliveryConfigResponse)
async def list_delivery_config(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(DeliveryConfig)
    
    if is_active is not None:
        query = query.where(DeliveryConfig.is_active == is_active)
        
    return await get_paginated_result(db, query, skip, limit)


@delivery_router.get("/{delivery_id:int}", response_model=DeliveryConfigResponse)
async def get_delivery_config(
    delivery_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeliveryConfig)
        .where(DeliveryConfig.id == delivery_id)
        ) 
    
    delivery_config = result.scalars().first()
    if not delivery_config:
        raise HTTPException(
            status_code=404,
            detail="Delivery config not found"
        )
        
    return delivery_config

@delivery_router.patch("/{delivery_id:int}", response_model=DeliveryConfigResponse)
async def update_delivery_config(
    delivery_id: int,
    data: DeliveryConfigUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeliveryConfig)
        .where(DeliveryConfig.id == delivery_id)
        ) 
    
    delivery_config = result.scalars().first()
    if not delivery_config:
        raise HTTPException(
            status_code=404,
            detail="Delivery config not found"
        )
        
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(delivery_config, field, value)

    await db.commit()
    await db.refresh(delivery_config)
    
    return delivery_config
    
@delivery_router.delete("/{delivery_id:int}")
async def get_delivery_config(
    delivery_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeliveryConfig)
        .where(DeliveryConfig.id == delivery_id)
        ) 
    
    delivery_config = result.scalars().first()
    if not delivery_config:
        raise HTTPException(
            status_code=404,
            detail="Delivery config not found"
        )
    await db.delete(delivery_config)
    await db.commit()

    return {
        "status": True,
        "message": "Offer deleted successfully"
    }
        