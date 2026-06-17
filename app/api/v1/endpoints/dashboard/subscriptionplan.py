from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.api.v1.schemas.subscriptionplan import PaginatedSubscriptionPlanResponse, SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate
from app.core.database import get_db
from app.models.subscriptionplan import SubscriptionPlan
from app.models.user import User
from app.auth.permissions import staff_only
from app.utils.pagination import get_paginated_result

admin_subscription_plan = APIRouter(prefix="/dashboard/subscription-plan", tags=['Admin SubscriptionPlan CRUD'])
subscription_plan = APIRouter(prefix="/subscription-plan", tags=['SubscriptionPlan'])

def create_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

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
        
    await db.delete(plan)
    await db.commit()

    return {
        "status": True,
        "message": "Plan deleted successfully"
    }
