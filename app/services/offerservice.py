from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.offers import Offer, OfferBOGO, OfferTarget, OfferType, TargetType
from app.models.products import Product, ProductCategory


async def validate_offer_conflict(
    db: AsyncSession,
    *,
    code,
    offer_type,
    start_date,
    end_date,
    targets,
    exclude_offer_id=None,
):
    # validate code uniqueness
    result = await db.execute(
        select(Offer).where(Offer.code == code)
    )
    existing_offer = result.scalars().first()
    if existing_offer:
        raise HTTPException(
            status_code=400,
            detail="Offer with this code already exists."
        )
        
    # CASE 1: offers WITH targets
    if targets:
        for target in targets:
            query = (
                select(Offer)
                .join(OfferTarget)
                .where(
                    and_(
                        Offer.type == offer_type,
                        OfferTarget.target_type == target.target_type,
                        OfferTarget.target_id == target.target_id,
                        Offer.start_date <= end_date,
                        Offer.end_date >= start_date,
                        Offer.is_active == True
                    )
                )
            )

            if exclude_offer_id:
                query = query.where(Offer.id != exclude_offer_id)

            result = await db.execute(query)
            existing_offer = result.scalars().first()

            if existing_offer:
                raise HTTPException(
                    status_code=400,
                    detail=f"{offer_type.value} offer already exists for target_id={target.target_id}"
                )
        
        # check if the target_ids exists in db
        if offer_type in (OfferType.ITEM, OfferType.CATEGORY):
            for target in targets:
                await validate_target_exists(db, target)

    # CASE 2: offers WITHOUT targets (STORE / GLOBAL OFFERS)
    else:
        query = (
            select(Offer)
            .where(
                and_(
                    Offer.type == offer_type,
                    Offer.start_date <= end_date,
                    Offer.end_date >= start_date,
                    Offer.is_active == True
                )
            )
        )

        if exclude_offer_id:
            query = query.where(Offer.id != exclude_offer_id)

        result = await db.execute(query)
        existing_offer = result.scalars().first()

        if existing_offer:
            raise HTTPException(
                status_code=400,
                detail=f"{offer_type.value} offer already exists for this date range"
            )

async def validate_target_exists(db, target, target_id=None):
    actual_target_id = target_id or target.target_id

    if target.target_type == TargetType.ITEM:
        result = await db.execute(
            select(Product.id).where(Product.id == actual_target_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Product with id {actual_target_id} does not exist"
            )

    elif target.target_type == TargetType.CATEGORY:
        result = await db.execute(
            select(ProductCategory.id).where(ProductCategory.id == actual_target_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Category with id {actual_target_id} does not exist"
            )
                

# overall validations 
def validate_offer(payload):
    validate_type_rule(payload.type, payload.bogo_meta, payload.targets)
    validate_dates(payload.start_date, payload.end_date)
    validate_discount(payload.discount_type, payload.discount_value)
    validate_target_type_with_offer_type(payload.type, payload.targets)
    
# offer type validation 
def validate_type_rule(type_, bogo_meta, targets):
    if type_ == "bogo":
        if bogo_meta is None:
            raise HTTPException(
                status_code=400,
                detail="bogo_meta is required when type is BOGO"
            )
    
    if type_ in("item", "category"):
        if not targets:
            raise HTTPException(
                status_code=400,
                detail=f"targets is required when type is {type_}"
            )

# offer dates validation 
# start_date should be before end_date
def validate_dates(start_date, end_date):
    if end_date <= start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be greater than start_date"
        )

# offer values validation
def validate_discount(discount_type, discount_value):
    if discount_value < 0:
        raise HTTPException(
            status_code=400,
            detail="discount_value cannot be negative"
        )

    if discount_type == "percentage" and discount_value > 100:
        raise HTTPException(
            status_code=400,
            detail="percentage discount cannot exceed 100"
        )

def validate_target_type_with_offer_type(type, targets):
     # validate target consistency BEFORE DB
    if type == OfferType.ITEM:
        for t in targets or []:
            if t.target_type != TargetType.ITEM:
                raise HTTPException(400, "target must be item for item offer")

    if type == OfferType.CATEGORY:
        for t in targets or []:
            if t.target_type != TargetType.CATEGORY:
                raise HTTPException(400, "target must be category for category offer")


# get all active offers 
async def get_all_active_offers(db):
    """
    Get all currently active offers.

    Conditions:
    - is_active = True
    - current time >= start_date
    - current time <= end_date
    """
    
    now = datetime.utcnow()
    
    query = (
        select(Offer)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(
            and_(
                Offer.is_active == True,
                Offer.start_date <= now,
                Offer.end_date >= now,
            )
        )
        .order_by(Offer.created_at.desc())
    )

    result = await db.execute(query)

    return result.scalars().unique().all()

# pre-group offers by type.
def build_offer_indexes(offers):
    item_map = {}       # item_id → offer
    category_map = {}   # category_id → offer
    store_offer = None
    bogo_map = {}       # item_id → offer

    for offer in offers:
        # STORE (single global priority bucket)
        if offer.type == OfferType.STORE:
            if not store_offer:
                store_offer = offer
            continue

        # ITEM + CATEGORY via targets
        if offer.type in (OfferType.ITEM, OfferType.CATEGORY):
            for t in offer.targets:
                if offer.type == OfferType.ITEM:
                    item_map[t.target_id] = offer
                elif offer.type == OfferType.CATEGORY:
                    category_map[t.target_id] = offer

        # BOGO
        if offer.type == OfferType.BOGO and offer.bogo_meta:
            bogo_map[offer.bogo_meta.buy_item_id] = offer

    return item_map, category_map, store_offer, bogo_map

# Resolve BEST OFFER per product (priority rules)
def resolve_offer(
    product,
    item_map,
    category_map,
    store_offer,
    bogo_map
):
    # 1. ITEM (highest priority)
    if product.id in item_map:
        return item_map[product.id]

    # 2. CATEGORY
    if product.category_id in category_map:
        return category_map[product.category_id]

    # 3. STORE
    if store_offer:
        return store_offer

    # 4. BOGO (lowest)
    return bogo_map.get(product.id)

# get active offer based on item 
# the priorirty of offers based on types: 
# 1 = Item offer
# 2 = Category offer
# 3 = Store offer
# 4 = bogo offer
#  1 being the highest priority
async def get_active_offer_by_item(db, item_id: int):
    """
    Offer priority:

    1. ITEM offer
    2. CATEGORY offer
    3. STORE offer
    4. BOGO offer

    Returns first matching active offer based on priority.
    """
    
    # 1. get item 
    item_result = await db.execute(
        select(Product).where(Product.id == item_id)
    )

    item = item_result.scalars().first()

    if not item:
        return []
    
    now = datetime.utcnow()
    
    # 2. ITEM OFFER (highest priority)
    item_offer_query = (
        select(Offer)
        .join(OfferTarget)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(
            and_(
                Offer.is_active == True,
                Offer.start_date <= now,
                Offer.end_date >= now,

                Offer.type == OfferType.ITEM,

                OfferTarget.target_type == TargetType.ITEM,
                OfferTarget.target_id == item_id,
            )
        )
        .order_by(Offer.created_at.desc())
    )

    item_offer = (
        await db.execute(item_offer_query)
    ).scalars().first()

    if item_offer:
        return item_offer

    # 3. CATEGORY OFFER
    category_offer_query = (
        select(Offer)
        .join(OfferTarget)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(
            and_(
                Offer.is_active == True,
                Offer.start_date <= now,
                Offer.end_date >= now,

                Offer.type == OfferType.CATEGORY,

                OfferTarget.target_type == TargetType.CATEGORY,
                OfferTarget.target_id == item.category_id,
            )
        )
        .order_by(Offer.created_at.desc())
    )

    category_offer = (
        await db.execute(category_offer_query)
    ).scalars().first()

    if category_offer:
        return category_offer

    # 4. STORE OFFER
    store_offer_query = (
        select(Offer)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(
            and_(
                Offer.is_active == True,
                Offer.start_date <= now,
                Offer.end_date >= now,

                Offer.type == OfferType.STORE,
            )
        )
        .order_by(Offer.created_at.desc())
    )

    store_offer = (
        await db.execute(store_offer_query)
    ).scalars().first()

    if store_offer:
        return store_offer

    # 5. BOGO OFFER
    bogo_offer_query = (
        select(Offer)
        .join(OfferBOGO)
        .options(
            selectinload(Offer.targets),
            selectinload(Offer.bogo_meta),
        )
        .where(
            and_(
                Offer.is_active == True,
                Offer.start_date <= now,
                Offer.end_date >= now,

                Offer.type == OfferType.BOGO,

                OfferBOGO.buy_item_id == item_id,
            )
        )
        .order_by(Offer.created_at.desc())
    )

    bogo_offer = (
        await db.execute(bogo_offer_query)
    ).scalars().first()

    if bogo_offer:
        return bogo_offer

    # No offer found
    return None

# check if offer is active 
async def check_active_offer(db, offer):
    query = (
        select(Offer)
        .where(
            and_(
                Offer.id ==offer.id,
                Offer.start_date <= offer.end_date,
                Offer.end_date >= offer.start_date,
                Offer.is_active == True
            )
        )
    )
    result = await db.execute(query)
    offer = result.scalars().first()
    if offer:
        return True
    return False