from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.offers import  OfferBOGOResponse, OfferBOGOUpdate, OfferCreate, OfferResponse, OfferTargetResponse, OfferTargetUpdate, OfferUpdate, PaginatedOfferResponse
from app.core.database import get_db
from app.models.offers import Offer, OfferBOGO, OfferTarget, OfferType, TargetType
from app.services.offerservice import check_active_offer, validate_dates, validate_discount, validate_offer, validate_offer_conflict, validate_target_exists
from app.utils.cache import delete_cache
from app.utils.pagination import get_paginated_result


offer_router = APIRouter(prefix="/dashboard/offer", tags=['Offer CRUD'])

PRODUCT_CACHE_KEY = "products:list"

@offer_router.post("/", response_model=OfferResponse)
async def create_offer(
    data: OfferCreate,
    db: AsyncSession = Depends(get_db),
):
    # validate offer fields
    validate_offer(data)
    
    # validate conflict
    await validate_offer_conflict(
        db=db,
        code=data.code,
        offer_type=data.type,
        start_date=data.start_date,
        end_date=data.end_date,
        targets=data.targets,
    )
    try: 
        offer = Offer(
            name=data.name,
            code=data.code,
            image_url=data.image_url,
            type=data.type,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            start_date=data.start_date,
            end_date=data.end_date,
            is_active=data.is_active,
            usage_limit_per_user=data.usage_limit_per_user,
            usage_limit_total=data.usage_limit_total,
            min_spent_amount=data.min_spent_amount,
            max_discount_amount=data.max_discount_amount,
        )

        db.add(offer)
        await db.flush()

        # create targets
        if data.type in (OfferType.ITEM, OfferType.CATEGORY) and data.targets:
            for target in data.targets:
                db.add(
                    OfferTarget(
                        offer_id=offer.id,
                        target_type=target.target_type,
                        target_id=target.target_id,
                    )
                )

        # create bogo meta
        if data.type == OfferType.BOGO and data.bogo_meta:
            for meta in data.bogo_meta:
                db.add(
                    OfferBOGO(
                        offer_id=offer.id,
                        buy_quantity=meta.buy_quantity,
                        get_quantity=meta.get_quantity,
                        apply_to_same_item=meta.apply_to_same_item,
                        get_item_id=meta.get_item_id,
                    )
                )
        await db.commit() 
    except Exception:
        await db.rollback()
        raise
    
    result = await db.execute(
        select(Offer)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(Offer.id == offer.id)
    )

    return result.scalars().first()

@offer_router.get("/", response_model=PaginatedOfferResponse)
async def list_offer(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    code: Optional[str] = None,
    type: Optional[OfferType] = None,
    is_active: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Offer).options(
        selectinload(Offer.targets),
        selectinload(Offer.bogo_meta)
    ).order_by(Offer.created_at.desc())
    
    #filters
    if code:
        query = query.where(Offer.code == code)
    if type:
        query = query.where(Offer.type == type)
    if is_active is not None:
        query = query.where(Offer.is_active == is_active)
    if start_date:
        query = query.where(func.date(Offer.start_date) == start_date.date())
    if end_date:
        query = query.where(func.date(Offer.end_date) == end_date.date())
        
    return await get_paginated_result(db, query, skip, limit)

@offer_router.get("/{offer_id:int}", response_model=OfferResponse)
async def get_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    query = select(Offer).options(
        selectinload(Offer.targets),
        selectinload(Offer.bogo_meta)
    ).where(Offer.id == offer_id)
    result = await db.execute(query)
    return result.scalars().first

@offer_router.patch("/{offer_id:int}", response_model=OfferResponse)
async def update_offer(
    offer_id: int,
    data: OfferUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Offer)
        .options(selectinload(Offer.targets))
        .where(Offer.id == offer_id)
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(
            status_code=404,
            detail="Offer not found"
        )
    
    # validate offer fields
    if data.start_date or data.end_date:
        validate_dates(data.start_date or offer.start_date, data.end_date or offer.end_date)
    if data.discount_type or data.discount_value:
        validate_discount(data.discount_type or offer.discount_type, data.discount_value or offer.discount_value)
    
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offer, field, value)

    await db.commit()
    await db.refresh(offer)
    
    result = await db.execute(
        select(Offer)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(Offer.id == offer.id)
    )
    offer = result.scalars().first()
    
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer):
        await delete_cache(PRODUCT_CACHE_KEY)

    return offer

@offer_router.delete("/{offer_id:int}")
async def delete_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Offer)
        .where(Offer.id == offer_id)
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(
            status_code=404,
            detail="Offer not found"
        )
    
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer):
        await delete_cache(PRODUCT_CACHE_KEY)
    
    await db.delete(offer)
    await db.commit()

    return {
        "status": True,
        "message": "Offer deleted successfully"
    }

@offer_router.patch("/target-type/{target_type_id}", response_model=OfferTargetResponse)
async def update_target_type(
    target_type_id: int,
    data: OfferTargetUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferTarget)
        .options(OfferTarget.offer)
        .where(OfferTarget.id == target_type_id)
    )
    offer_target = result.scalars().first()
    if not offer_target:
        raise HTTPException(
            status_code=404,
            detail="OfferTarget not found"
        )
    
    #validate if the target_id [item, category id] exists in db 
    await validate_target_exists(db, offer_target, data.target_id)
    
    # apply only provided fields
    if data.target_id:
        offer_target.target_id = data.target_id

    await db.commit()
    await db.refresh(offer_target)
    
    result = await db.execute(
        select(OfferTarget)
        .where(OfferTarget.id == offer_target.id)
    )
    offer_target = result.scalars().first()
    
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer_target.offer):
        await delete_cache(PRODUCT_CACHE_KEY)

    return offer_target

@offer_router.delete("/target-type/{target_type_id}")
async def delete_target_type(
    target_type_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferTarget)
        .options(selectinload(OfferTarget.offer))
        .where(OfferTarget.id == target_type_id)
    )
    offer_target = result.scalars().first()
    if not offer_target:
        raise HTTPException(
            status_code=404,
            detail="OfferTarget not found"
        )
    
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer_target.offer):
        await delete_cache(PRODUCT_CACHE_KEY)

    await db.delete(offer_target)
    await db.commit()

    return {
        "status": True,
        "message": "Offer target deleted successfully"
    }

@offer_router.patch("/offer-bogo/{offer_bogo_id}", response_model=OfferBOGOResponse)
async def update_offer_bogo(
    offer_bogo_id: int,
    data: OfferBOGOUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferBOGO)
        .options(selectinload(OfferBOGO.offer))
        .where(OfferBOGO.id == offer_bogo_id)
    )
    offer_bogo = result.scalars().first()
    if not offer_bogo:
        raise HTTPException(
            status_code=404,
            detail="OfferBOGO not found"
        )
    
    # apply only provided fields
    for field, value in data.items():
        setattr(offer_bogo, field, value)

    await db.commit()
    await db.refresh(offer_bogo)
    
    result = await db.execute(
        select(OfferBOGO)
        .where(Offer.id == offer_bogo.id)
    )
    offer_bogo = result.scalars().first()
    
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer_bogo.offer):
        await delete_cache(PRODUCT_CACHE_KEY)

    return offer_bogo

@offer_router.delete("/offer-bogo/{offer_bogo_id}")
async def delete_offer_bogo(
    offer_bogo_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferBOGO)
        .options(selectinload(OfferBOGO.offer))
        .where(OfferBOGO.id == offer_bogo_id)
    )
    offer_bogo = result.scalars().first()
    if not offer_bogo:
        raise HTTPException(
            status_code=404,
            detail="OfferBOGO not found"
        )
        
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer_bogo.offer):
        await delete_cache(PRODUCT_CACHE_KEY)
    
    await db.delete(offer_bogo)
    await db.commit()

    return {
        "status": True,
        "message": "Offer bogo deleted successfully"
    }