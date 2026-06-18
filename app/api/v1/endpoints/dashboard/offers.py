from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.offers import  ComboOfferCreate, ComboOfferItemCreate, ComboOfferItemResponse, ComboOfferResponse, ComboOfferUpdate, OfferBOGOResponse, OfferBOGOUpdate, OfferCreate, OfferResponse, OfferTargetResponse, OfferTargetUpdate, OfferUpdate, PaginatedComboOfferResponse, PaginatedOfferResponse
from app.core.database import get_db
from app.models.offers import ComboDiscountType, ComboOffer, ComboOfferItem, Offer, OfferBOGO, OfferTarget, OfferType, TargetType
from app.models.products import ProductVariant
from app.models.user import User
from app.services.offerservice import check_active_offer, validate_dates, validate_discount, validate_offer, validate_offer_conflict, validate_target_exists
from app.utils.cache import delete_cache
from app.utils.pagination import get_paginated_result
from app.auth.permissions import staff_only


offer_router = APIRouter(prefix="/dashboard/offer", tags=['Offer CRUD'])

PRODUCT_CACHE_KEY = "products:list"

@offer_router.post("/", response_model=OfferResponse)
async def create_offer(
    data: OfferCreate,
    current_user: User = Depends(staff_only),
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
            db.add(
                OfferBOGO(
                    offer_id=offer.id,
                    buy_item_id=data.bogo_meta.buy_item_id,
                    buy_quantity=data.bogo_meta.buy_quantity,
                    get_quantity=data.bogo_meta.get_quantity,
                    apply_to_same_item=data.bogo_meta.apply_to_same_item,
                    get_item_id=data.bogo_meta.get_item_id,
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
    ).where(
        Offer.deleted_at.is_(None)
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
    ).where(
        Offer.id == offer_id,
        Offer.deleted_at.is_(None)
        )
    result = await db.execute(query)
    return result.scalars().first

@offer_router.patch("/{offer_id:int}", response_model=OfferResponse)
async def update_offer(
    offer_id: int,
    data: OfferUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Offer)
        .options(selectinload(Offer.targets))
        .where(
            Offer.id == offer_id,
            Offer.deleted_at.is_(None)
            )
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
async def soft_delete_offer(
    offer_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Offer)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta)
        )
        .where(
            Offer.id == offer_id,
            Offer.deleted_at.is_(None)
            )
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
    
    # soft delete
    if offer.targets:
        for target in offer.targets:
            target.deleted_at = datetime.utcnow()
    if offer.bogo_meta:
        for bogo_meta in offer.bogo_meta:
            bogo_meta.deleted_at = datetime.utcnow()
    
    offer.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Offer deleted successfully"
    }

@offer_router.patch("/target-type/{target_type_id}", response_model=OfferTargetResponse)
async def update_target_type(
    target_type_id: int,
    data: OfferTargetUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferTarget)
        .options(OfferTarget.offer)
        .where(
            OfferTarget.id == target_type_id,
            OfferTarget.deleted_at.is_(None)
            )
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
async def soft_delete_target_type(
    target_type_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferTarget)
        .options(selectinload(OfferTarget.offer))
        .where(
            OfferTarget.id == target_type_id,
            OfferTarget.deleted_at.is_(None)
            )
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

    #soft delete
    offer_target.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Offer target deleted successfully"
    }

@offer_router.patch("/offer-bogo/{offer_bogo_id}", response_model=OfferBOGOResponse)
async def update_offer_bogo(
    offer_bogo_id: int,
    data: OfferBOGOUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferBOGO)
        .options(selectinload(OfferBOGO.offer))
        .where(
            OfferBOGO.id == offer_bogo_id,
            OfferBOGO.deleted_at.is_(None)
            )
    )
    offer_bogo = result.scalars().first()
    if not offer_bogo:
        raise HTTPException(
            status_code=404,
            detail="OfferBOGO not found"
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offer_bogo, field, value)

    await db.commit()
    await db.refresh(offer_bogo)
    
    result = await db.execute(
        select(OfferBOGO)
        .where(OfferBOGO.id == offer_bogo.id)
    )
    offer_bogo = result.scalars().first()
    
    # check if offer is active , if active then delete product list cache
    if  await check_active_offer(db, offer_bogo.offer):
        await delete_cache(PRODUCT_CACHE_KEY)

    return offer_bogo

@offer_router.delete("/offer-bogo/{offer_bogo_id}")
async def soft_delete_offer_bogo(
    offer_bogo_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfferBOGO)
        .options(selectinload(OfferBOGO.offer))
        .where(
            OfferBOGO.id == offer_bogo_id,
            OfferBOGO.deleted_at.is_(None)
            )
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
    
    #soft delete
    offer_bogo.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Offer bogo deleted successfully"
    }
    
## combo offer
@offer_router.post("/combo-offer/", response_model=ComboOfferResponse)
async def create_combo_offer(
    data: ComboOfferCreate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    # validate offer fields
    validate_dates(data.start_date, data.end_date)
    validate_discount(data.discount_type, data.discount_value)

    try: 
        combo_offer = ComboOffer(
            name = data.name,
            description = data.description, 
            is_active = data.is_active,
            start_date = data.start_date,
            end_date = data.end_date,
            discount_type = data.discount_type,
            discount_value = data.discount_value,
            priority = data.priority,
            stackable = data.stackable,
            image_url = data.image_url
        )

        db.add(combo_offer)
        await db.flush()

        # create targets
        if data.items:
            for item in data.items:
                db.add(
                    ComboOfferItem(
                        combo_offer_id = combo_offer.id,
                        product_variant_id = item.product_variant_id if item.product_variant_id else None,
                        product_id = item.product_id if item.product_id else None,
                        quantity = item.quantity
                    )
                )
                
        await db.commit() 
    except Exception:
        await db.rollback()
        raise
    
    result = await db.execute(
        select(ComboOffer)
        .options(
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.product)
        )
        .where(ComboOffer.id == combo_offer.id)
    )

    return result.scalars().first()

@offer_router.get("/combo-offer/", response_model=PaginatedComboOfferResponse)
async def list_combo_offer(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    discount_type: Optional[ComboDiscountType] = None,
    is_active: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ComboOffer).where(
        ComboOffer.deleted_at.is_(None)
        ).options(
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.product)
    ).order_by(ComboOffer.created_at.desc())
    
    #filters
    if discount_type:
        query = query.where(ComboOffer.discount_type == discount_type)
    if is_active is not None:
        query = query.where(ComboOffer.is_active == is_active)
    if start_date:
        query = query.where(func.date(ComboOffer.start_date) == start_date.date())
    if end_date:
        query = query.where(func.date(ComboOffer.end_date) == end_date.date())
        
    return await get_paginated_result(db, query, skip, limit)

@offer_router.get("/combo-offer/{offer_id:int}/", response_model=ComboOfferResponse)
async def get_combo_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    query = select(ComboOffer).options(
        selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.product)
    ).where(
        ComboOffer.id == offer_id,
        ComboOffer.deleted_at.is_(None)
        )
    result = await db.execute(query)
    return result.scalars().first()

@offer_router.patch("/combo-offer/{offer_id:int}/", response_model=ComboOfferResponse)
async def update_combo_offer(
    offer_id: int,
    data: ComboOfferUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ComboOffer)
        .options(selectinload(ComboOffer.items))
        .where(
            ComboOffer.id == offer_id,
            ComboOffer.deleted_at.is_(None)
            )
    )
    combo_offer = result.scalars().first()
    if not combo_offer:
        raise HTTPException(
            status_code=404,
            detail="Offer not found"
        )
    
    # validate offer fields
    if data.start_date or data.end_date:
        validate_dates(data.start_date or combo_offer.start_date, data.end_date or combo_offer.end_date)
    if  data.discount_type or data.discount_value:
        validate_discount(data.discount_type or combo_offer.discount_type, data.discount_value or combo_offer.discount_value)
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(combo_offer, field, value)

    await db.commit()
    await db.refresh(combo_offer)
    
    result = await db.execute(
        select(ComboOffer)
        .options(
            selectinload(ComboOffer.items)
            .selectinload(ComboOfferItem.product_variant)
            .selectinload(ProductVariant.product)
        )
        .where(ComboOffer.id == combo_offer.id)
    )
    combo_offer = result.scalars().first()
    return combo_offer


@offer_router.delete("/combo-offer/{offer_id:int}/")
async def soft_delete_combo_offer(
    offer_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ComboOffer)
        .options(
            selectinload(ComboOffer.items)
        )
        .where(ComboOffer.id == offer_id)
    )
    combo_offer = result.scalars().first()
    if not combo_offer:
        raise HTTPException(
            status_code=404,
            detail="Offer not found"
        )
    
    #soft delete
    if combo_offer.items:
        for item in combo_offer.items:
            item.deleted_at = datetime.utcnow()
        
    combo_offer.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Offer deleted successfully"
    }
    
# @offer_router.post("/combo-offer-item/", response_model=ComboOfferItemResponse)
# async def add_combo_offer_item(
#     data: ComboOfferItemCreate,
#     current_user: User = Depends(staff_only),
#     db: AsyncSession = Depends(get_db),
# ):
#     offer_item = ComboOfferItem(
#         combo_offer_id = data.combo_offer_id,
#         product_variant_id = data.product_variant_id if data.product_variant_id else None,
#         product_id = data.product_id if data.product_id else None,
#         quantity = data.quantity
#     )
#     db.add(offer_item)
#     await db.commit() 
#     await db.refresh(offer_item)
#     return offer_item

@offer_router.delete("/combo-offer-item/{offer_item_id:int}/")
async def soft_delete_combo_offer_item(
    offer_item_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ComboOfferItem)
        .where(ComboOfferItem.id == offer_item_id)
    )
    combo_offer_item = result.scalars().first()
    if not combo_offer_item:
        raise HTTPException(
            status_code=404,
            detail="Offer item not found"
        )
    
    #soft delete
    combo_offer_item.deleted_at = datetime.utcnow()
    await db.commit()

    return {
        "status": True,
        "message": "Offer item deleted successfully"
    }
    