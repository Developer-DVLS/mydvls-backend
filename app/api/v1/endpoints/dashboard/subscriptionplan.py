import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import re
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.subscriptionplan import CreateSubscriptionPlanAddonPrice, PaginatedServiceResponse, PaginatedSubscriptionPlanResponse, ServiceCreate, ServiceOptionResponse, ServiceResponse, ServiceUpdate, SubscriptionPlanAddonCreate, SubscriptionPlanAddonOptionResponse, SubscriptionPlanAddonPriceResponse, SubscriptionPlanAddonResponse, SubscriptionPlanAddonUpdate, SubscriptionPlanCreate, SubscriptionPlanOptionResponse, SubscriptionPlanPriceCreate, SubscriptionPlanPriceResponse, SubscriptionPlanPriceUpdate, SubscriptionPlanResponse, SubscriptionPlanUpdate, UpdateSubscriptionPlanAddonPrice
from app.core.database import get_db
from app.models.subscriptionplan import Service, SubscriptionPlan, SubscriptionPlanAddon, SubscriptionPlanAddonPrice, SubscriptionPlanPrice
from app.models.user import User
from app.auth.permissions import staff_only
from app.services.security import get_current_user
from app.utils.pagination import get_paginated_result

admin_subscription_plan = APIRouter(prefix="/dashboard/subscription-plan", tags=['Admin SubscriptionPlan CRUD'])
subscription_plan = APIRouter(prefix="/subscription-plan", tags=['SubscriptionPlan'])

SUBSCRIPTION_ADDON_SELECTION_COOKIE_KEY = "subscription_selection"

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
        global_type=data.global_type.lower(),
        badge=data.badge,
        title=data.title,
        sub_title=data.sub_title,
        bottom_card=data.bottom_card
    )

    db.add(service)
    await db.flush()

    for plan_data in data.plans:
        
        # check if key already exists
        existing_plan_result = await db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.key == plan_data.key)
        ) 
        existing_plan = existing_plan_result.scalars().first()
        if existing_plan:
            raise HTTPException(
                status_code=400,
                detail=f"Subscriptionplan with key '{plan_data.key}' already exists."
            )

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
            created_by=current_user.id,
            is_normal=plan_data.is_normal if 'is_normal' in plan_data else None
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
                subscription_plan_addon = SubscriptionPlanAddon(
                        subscription_plan_id=plan.id,
                        title=addon_data.title,
                        description=addon_data.description
                    )
                db.add(subscription_plan_addon)
                await db.flush()

                for addon_price in addon_data.prices:
                    db.add(
                        SubscriptionPlanAddonPrice(
                            subscription_plan_addon_id = subscription_plan_addon.id,
                            billing_period = addon_price.billing_period,
                            price = addon_price.price
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
    global_type: Optional[str] = None,
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
            .selectinload(SubscriptionPlanAddon.prices)
        ).order_by(Service.created_at.desc())
    
    if global_type:
        query = query.where(Service.global_type == global_type.lower())

    return await get_paginated_result(db, query, skip, limit)

# @subscription_plan.get(
#     "/nested/{service_id}",
#     response_model=ServiceResponse
# )
# async def get_service(
#     service_id: int,
#     db: AsyncSession = Depends(get_db)
# ):
#     result = await db.execute(
#         select(Service)
#         .options(
#             selectinload(Service.plans)
#             .selectinload(SubscriptionPlan.prices),

#             selectinload(Service.plans)
#             .selectinload(SubscriptionPlan.addons)
#         )
#         .where(Service.id == service_id)
#     )

#     service = result.scalar_one_or_none()

#     if not service:
#         raise HTTPException(
#             status_code=404,
#             detail="Service not found"
#         )

#     return service

@subscription_plan.get(
    "/{global_type}",
    response_model=ServiceResponse,
    summary="Get subscription plans to show in user side by service global type",
)
async def get_service_plans(
    global_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    ## check if any addons are selected
    cookie = request.cookies.get(
        SUBSCRIPTION_ADDON_SELECTION_COOKIE_KEY
    )
    selection = None
    if cookie:
        try:
            selection = json.loads(cookie)
        except json.JSONDecodeError:
            pass
    
    ## get serviceplans
    result = await db.execute(
        select(Service)
        .options(
            selectinload(Service.plans)
            .selectinload(SubscriptionPlan.prices),

            selectinload(Service.plans)
            .selectinload(SubscriptionPlan.addons)
            .selectinload(SubscriptionPlanAddon.prices)
        )
        .where(Service.global_type == global_type)
    )

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )
        
    service_data = ServiceResponse.model_validate(
        service,
        from_attributes=True
    )
    
    if selection:
        selected_service_id = selection.get("service_id")
        selected_plan_id = selection.get("plan_id")
        selected_addon_ids = selection.get("addon_ids", [])

        service_data.selected = (
            service_data.id == selected_service_id
        )

        for plan in service_data.plans:
            plan.selected = (
                plan.id == selected_plan_id
            )

            for addon in plan.addons:
                addon.selected = (
                    addon.id in selected_addon_ids
                )
    
    return service_data
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
    # service_id validation
    service_result = await db.execute(
        select(Service)
        .where(Service.id == data.service_id)
    )
    service = service_result.scalars().first()
    if not service:
        raise HTTPException(
            status_code= 404,
            detail="Invalid service-id."
        )
        
    # check if key already exists
    existing_plan_result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.key == data.key)
    ) 
    existing_plan = existing_plan_result.scalars().first()
    if existing_plan:
        raise HTTPException(
            status_code=400,
            detail=f"SubscriptionPlan with key '{data.key}' already exists."
        )
        
    plan = SubscriptionPlan(
        service_id = data.service_id,
        name = data.name, 
        slug = create_slug(data.name),
        key = data.key,
        description = data.description or None if "description" in data else None, 
        features = data.features,
        trial_days = data.trial_days, 
        is_popular = data.is_popular,
        is_active = data.is_active,
        max_users = data.max_users,
        max_locations = data.max_locations,
        max_products = data.max_products,
        sort_order = data.sort_order,
        created_by = current_user.id,
        is_normal = data.is_normal if "is_normal" in data else None
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
    
# =========================
## SUBSCRIPTION PLAN ADDON PRICE CRUD
# =========================
@admin_subscription_plan.post(
    "/plans/addons/{addon_id}/price",
    response_model=SubscriptionPlanAddonPriceResponse
)
async def create_addon_price(
    addon_id: int,
    data: CreateSubscriptionPlanAddonPrice,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanAddon)
        .where(
            SubscriptionPlanAddon.id == addon_id,
            )
    )
    plan_addon = result.scalars().first()
    if not plan_addon:
        raise HTTPException(
            status_code=404,
            detail="Plan Addon not found"
        )

    addon_price = SubscriptionPlanAddonPrice(
        subscription_plan_addon_id=addon_id,
        **data.model_dump()
    )

    db.add(addon_price)

    await db.commit()
    await db.refresh(addon_price)

    return addon_price

@subscription_plan.get(
    "/plans/addons/{addon_id}/price",
    response_model=list[SubscriptionPlanAddonPriceResponse]
)
async def list_prices_by_addons(
    addon_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanAddonPrice)
        .where(
            SubscriptionPlanAddonPrice.subscription_plan_addon_id== addon_id
        )
        .order_by(
            SubscriptionPlanAddonPrice.created_at.asc()
        )
    )

    return result.scalars().all()

@subscription_plan.get(
    "/addons/price/{addon_price_id}",
    response_model=SubscriptionPlanAddonPriceResponse
)
async def get_addon_price(
    addon_price_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanAddonPrice)
        .where(SubscriptionPlanAddonPrice.id == addon_price_id)
    )
    addon_price = result.scalars().first()

    if not addon_price:
        raise HTTPException(
            status_code=404,
            detail="Addon Price not found"
        )

    return addon_price

@admin_subscription_plan.patch(
    "/addons/price/{addon_price_id}",
    response_model=SubscriptionPlanAddonPriceResponse
)
async def update_addon_price(
    addon_price_id: int,
    data: UpdateSubscriptionPlanAddonPrice,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanAddonPrice)
        .where(SubscriptionPlanAddonPrice.id == addon_price_id)
    )
    addon_price = result.scalars().first()
    if not addon_price:
        raise HTTPException(
            status_code=404,
            detail="Addon Price not found"
        )

    for field, value in data.model_dump(
        exclude_unset=True
    ).items():
        setattr(addon_price, field, value)

    await db.commit()
    await db.refresh(addon_price)

    return addon_price

@admin_subscription_plan.delete("/addons/price/{addon_price_id}")
async def delete_addon(
    addon_price_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(SubscriptionPlanAddonPrice)
        .where(SubscriptionPlanAddonPrice.id == addon_price_id)
    )
    addon_price = result.scalars().first()
    if not addon_price:
        raise HTTPException(
            status_code=404,
            detail="Addon Price not found"
        )

    await db.delete(addon_price)
    await db.commit()

    return {
        "status": True,
        "message": "Addon Price deleted successfully."
    }
    
@subscription_plan.get("/service-options/", response_model=List[ServiceOptionResponse])
async def service_options(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Service)
        .order_by(Service.created_at.desc())
    )
    services = result.scalars().all()
    if not services:
        return []
    return services

@subscription_plan.get("/plan-options/", response_model=List[SubscriptionPlanOptionResponse])
async def subscription_plan_options(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlan)
        .order_by(SubscriptionPlan.created_at.desc())
    )
    subscription_plans = result.scalars().all()
    if not subscription_plans:
        return []
    return subscription_plans


@subscription_plan.get("/addon-options/", response_model=List[SubscriptionPlanAddonOptionResponse])
async def subscription_plan_addon_options(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlanAddon)
        .order_by(SubscriptionPlanAddon.created_at.desc())
    )
    subscription_plan_addons = result.scalars().all()
    if not subscription_plan_addons:
        return []
    return subscription_plan_addons