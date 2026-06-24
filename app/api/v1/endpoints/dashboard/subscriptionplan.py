from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import re
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.subscriptionplan import PaginatedServiceResponse, PaginatedSubscriptionPlanResponse, ServiceCreate, ServiceResponse, ServiceUpdate, SubscriptionPlanAddonCreate, SubscriptionPlanAddonResponse, SubscriptionPlanAddonUpdate, SubscriptionPlanCreate, SubscriptionPlanPriceCreate, SubscriptionPlanPriceResponse, SubscriptionPlanPriceUpdate, SubscriptionPlanResponse, SubscriptionPlanUpdate
from app.core.database import get_db
from app.models.subscriptionplan import Service, SubscriptionPlan, SubscriptionPlanAddon, SubscriptionPlanPrice
from app.models.user import User
from app.auth.permissions import staff_only
from app.services.security import get_current_user
from app.utils.pagination import get_paginated_result

admin_subscription_plan = APIRouter(prefix="/dashboard/subscription-plan", tags=['Admin SubscriptionPlan CRUD'])
subscription_plan = APIRouter(prefix="/subscription-plan", tags=['SubscriptionPlan'])

def create_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

# =========================
## NESTED CRUD
# =========================
@admin_subscription_plan.post("/nested/")
async def create_service_nested(
    data: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):

    service = Service(
        global_type=data.global_type,
        badge=data.badge,
        title=data.title,
        sub_title=data.sub_title,
        bottom_card=data.bottom_card
    )

    db.add(service)
    await db.flush()

    for plan_data in data.plans:

        plan = SubscriptionPlan(
            service_id=service.id,
            name=plan_data.name,
            slug=create_slug(plan_data.name),
            key=plan_data.key,
            description=plan_data.description,
            features=plan_data.features,
            trial_days=plan_data.trial_days,
            is_popular=plan_data.is_popular,
            is_active=plan_data.is_active,
            max_users=plan_data.max_users,
            max_locations=plan_data.max_locations,
            max_products=plan_data.max_products,
            sort_order=plan_data.sort_order,
            created_by=current_user.id
        )

        db.add(plan)
        await db.flush()

        for price_data in plan_data.prices:
            db.add(
                SubscriptionPlanPrice(
                    subscription_plan_id=plan.id,
                    billing_period=price_data.billing_period,
                    price=price_data.price
                )
            )

        if plan_data.addons:
            for addon_data in plan_data.addons:
                db.add(
                    SubscriptionPlanAddon(
                        subscription_plan_id=plan.id,
                        title=addon_data.title,
                        description=addon_data.description,
                        price=addon_data.price
                    )
                )

    await db.commit()
    await db.refresh(service)

    return {
        "message": "Service created successfully",
        "service_id": service.id
    }
    
@subscription_plan.get(
    "/nested/",
    response_model=PaginatedServiceResponse
)
async def list_services_nested(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    
    query =   select(
        Service).options(
            selectinload(Service.plans)
            .selectinload(SubscriptionPlan.prices),

            selectinload(Service.plans)
            .selectinload(SubscriptionPlan.addons)
        ).order_by(Service.created_at.desc())

    return await get_paginated_result(db, query, skip, limit)

@subscription_plan.get(
    "/nested/{service_id}",
    response_model=ServiceResponse
)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Service)
        .options(
            selectinload(Service.plans)
            .selectinload(SubscriptionPlan.prices),

            selectinload(Service.plans)
            .selectinload(SubscriptionPlan.addons)
        )
        .where(Service.id == service_id)
    )

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    return service
# =========================
## END OF NESTED CRUD
# =========================

# =========================
## SERVICES CRUD
# =========================
@admin_subscription_plan.patch("/services/{service_id}")
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(Service)
        .where(Service.id == service_id)
        ) 
    service = result.scalars().first()
    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)

    return {
        "status": True,
        "message": "Service updated successfully."
    }

@admin_subscription_plan.delete("/services/{service_id}")
async def delete_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(Service)
        .where(Service.id == service_id)
        ) 
    service = result.scalars().first()
    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )
        
    await db.delete(service)
    await db.commit()

    return {
        "status": True,
        "message": "Service deleted successfully."
    }
# =========================
## END OF SERVICES CRUD
# =========================

# =========================
## SUBSCRIPTION CRUD
# =========================
@admin_subscription_plan.post("/")
async def create_plan(
    data: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    plan = SubscriptionPlan(
        name = data.name, 
        slug = create_slug(data.name),
        key = data.key,
        description = data.description or None if "description" in data else None, 
        price = data.price,
        billing_period = data.billing_period.lower() or None,
        trial_days = data.trial_days, 
        is_popular = data.is_popular,
        is_active = data.is_active,
        sort_order = data.sort_order,
        created_by = current_user.id
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    
    return {
        "status": True,
        "message": "Subscription plan created successfully."
    }

@subscription_plan.get("/", response_model=PaginatedSubscriptionPlanResponse)
async def list_plan(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    query = select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order)
    
    return await get_paginated_result(db, query, skip, limit)

@subscription_plan.get("/{plan_id:int}/", response_model=SubscriptionPlanResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code= 404,
            detail="Plan not found."
        )
    
    return plan

@subscription_plan.get("/slug/{plan_slug: str}/", response_model=SubscriptionPlanResponse)
async def get_plan_by_slug(
    plan_slug: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.slug == plan_slug)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code= 404,
            detail="Plan not found."
        )
    
    return plan

@admin_subscription_plan.patch("/{plan_id}/")
async def update_plan(
    plan_id: int,
    data: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code= 404,
            detail="Plan not found."
        )
        
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    
    await db.commit()
    await db.refresh(plan)
    
    return {
        "status": True,
        "message": "Plan updated successfully."
    }

@admin_subscription_plan.delete("/{plan_id}/")
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code= 404,
            detail="Plan not found."
        )
        
    await db.delete(plan)
    await db.commit()

    return {
        "status": True,
        "message": "Plan deleted successfully"
    }
# =========================
## END OF SUBSCRIPTION PLAN CRUD
# =========================

# =========================
## SUBSCRIPTION PLAN PRICE CRUD
# =========================
@admin_subscription_plan.post(
    "/plans/{plan_id}/prices",
    response_model=SubscriptionPlanPriceResponse
)
async def create_price(
    plan_id: int,
    data: SubscriptionPlanPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )
        
    price = SubscriptionPlanPrice(
        subscription_plan_id=plan_id,
        **data.model_dump()
    )

    db.add(price)

    await db.commit()
    await db.refresh(price)

    return price

@subscription_plan.get(
    "/{plan_id}/prices",
    response_model=list[SubscriptionPlanPriceResponse]
)
async def list_prices_by_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanPrice)
        .where(
            SubscriptionPlanPrice.subscription_plan_id
            == plan_id
        )
    )

    return result.scalars().all()

@subscription_plan.get(
    "/prices/{price_id}",
    response_model=SubscriptionPlanPriceResponse
)
async def get_price(
    price_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanPrice)
        .where(SubscriptionPlanPrice.id == price_id)
    )
    price = result.scalars().first()

    if not price:
        raise HTTPException(
            status_code= 404,
            detail="Price not found."
        )

    return price

@admin_subscription_plan.patch(
    "/prices/{price_id}",
    response_model=SubscriptionPlanPriceResponse
)
async def update_price(
    price_id: int,
    data: SubscriptionPlanPriceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanPrice)
        .where(SubscriptionPlanPrice.id == price_id)
    )
    price = result.scalars().first()

    if not price:
        raise HTTPException(
            status_code= 404,
            detail="Price not found."
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(price, field, value)

    await db.commit()
    await db.refresh(price)

    return price

@admin_subscription_plan.delete("/prices/{price_id}")
async def delete_price(
    price_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanPrice)
        .where(SubscriptionPlanPrice.id == price_id)
    )
    price = result.scalars().first()

    if not price:
        raise HTTPException(
            status_code= 404,
            detail="Price not found."
        )

    await db.delete(price)
    await db.commit()

    return {
        "status": True,
        "message": "Price deleted successfully."
    }
# =========================
## END OF SUBSCRIPTION PLAN PRICE CRUD
# =========================


# =========================
## SUBSCRIPTION PLAN ADDON CRUD
# =========================
@admin_subscription_plan.post(
    "/plans/{plan_id}/addons",
    response_model=SubscriptionPlanAddonResponse
)
async def create_addon(
    plan_id: int,
    data: SubscriptionPlanAddonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    addon = SubscriptionPlanAddon(
        subscription_plan_id=plan_id,
        **data.model_dump()
    )

    db.add(addon)

    await db.commit()
    await db.refresh(addon)

    return addon

@subscription_plan.get(
    "/plans/{plan_id}/addons",
    response_model=list[SubscriptionPlanAddonResponse]
)
async def list_addons_by_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanAddon)
        .where(
            SubscriptionPlanAddon.subscription_plan_id
            == plan_id
        )
        .order_by(
            SubscriptionPlanAddon.created_at.asc()
        )
    )

    return result.scalars().all()

@subscription_plan.get(
    "/addons/{addon_id}",
    response_model=SubscriptionPlanAddonResponse
)
async def get_addon(
    addon_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanAddon)
        .where(SubscriptionPlanAddon.id == addon_id)
    )
    addon = result.scalars().first()

    if not addon:
        raise HTTPException(
            status_code=404,
            detail="Addon not found"
        )

    return addon

@admin_subscription_plan.patch(
    "/addons/{addon_id}",
    response_model=SubscriptionPlanAddonResponse
)
async def update_addon(
    addon_id: int,
    data: SubscriptionPlanAddonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanAddon)
        .where(SubscriptionPlanAddon.id == addon_id)
    )
    addon = result.scalars().first()
    if not addon:
        raise HTTPException(
            status_code=404,
            detail="Addon not found"
        )

    for field, value in data.model_dump(
        exclude_unset=True
    ).items():
        setattr(addon, field, value)

    await db.commit()
    await db.refresh(addon)

    return addon

@admin_subscription_plan.delete("/addons/{addon_id}")
async def delete_addon(
    addon_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanAddon)
        .where(SubscriptionPlanAddon.id == addon_id)
    )
    addon = result.scalars().first()
    if not addon:
        raise HTTPException(
            status_code=404,
            detail="Addon not found"
        )

    await db.delete(addon)
    await db.commit()

    return {
        "status": True,
        "message": "Addon deleted successfully."
    }