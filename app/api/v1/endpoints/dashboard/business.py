from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.business import (
    Business,
    BusinessSubscription,
    BusinessSubscriptionAddon,
    SubscriptionStatus,
)
from app.api.v1.schemas.business import AdminCreateBusiness, AdminCreateBusinessSubscription, AdminCreateBusinessSubscriptionAddon, BusinessResponse, BusinessSubscriptionAddonResponse, BusinessSubscriptionResponse, PaginatedBusinessResponse, PaginatedBusinessSubscriptionAddonResponse, PaginatedBusinessSubscriptionResponse, UpdateBusiness, UpdateBusinessSubscription, UpdateBusinessSubscriptionAddon
from app.core.database import get_db
from app.services.businessservice import BusinessService
from app.utils.pagination import get_paginated_result
from app.auth.permissions import staff_only

admin_business_router = APIRouter(prefix="/dashboard/businesses", tags=["Admnin Businesses CRUD"])


#--------------------------
# Business CRUD
#--------------------------
@admin_business_router.post("/business/", response_model=BusinessResponse)
async def create_business(
    data: AdminCreateBusiness,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    data.email = data.email.lower()
    
    # Prevent duplicate business email
    existing = await db.scalar(
        select(Business).where(Business.email == data.email)
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Business with this email already exists."
        )
        
    business = Business(
        **data.model_dump(exclude_unset=True)
    )
    
    db.add(business)
    await db.commit()
    await db.refresh(business)

    return business
    
@admin_business_router.get("/business/", response_model=PaginatedBusinessResponse)
async def list_business(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    query = select(Business).order_by(Business.created_at.desc())
    return await get_paginated_result(db, query, skip, limit)

    
@admin_business_router.get("/business/{business_id}/", response_model=BusinessResponse)
async def get_business(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(Business)
        .where(Business.id == business_id)
        .order_by(Business.created_at.desc())
    )
    business = result.scalars().first()
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found."
        )
    
    return business

@admin_business_router.patch("/business/{business_id}/", response_model=BusinessResponse)
async def update_business( 
    business_id: UUID,
    data: UpdateBusiness,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(Business)
        .where(Business.id == business_id)
        .order_by(Business.created_at.desc())
    )
    business = result.scalars().first()
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found."
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(business, field, value)

    await db.commit()
    await db.refresh(business)
    
    return business

@admin_business_router.delete("/business/{business_id}/")
async def delete_business( 
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(Business)
        .where(Business.id == business_id)
        .order_by(Business.created_at.desc())
    )
    business = result.scalars().first()
    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found."
        )

    await db.delete(business)
    await db.commit()
    
    return {
        "status": True,
        "message": "Deleted successfully"
    }

#--------------------------
# Business Subscription CRUD
#--------------------------
@admin_business_router.post("/business-subscription/", response_model=BusinessSubscriptionResponse)
async def create_business_subscription(
    data: AdminCreateBusinessSubscription,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    business_service = BusinessService(db=db)
    # validate service and plan
    await business_service.validate_service_plan(
        data.service_id, 
        data.plan_id
        )
    #get price of a plan with selected billing_period
    plan_price = await business_service.get_plan_price(
        data.plan_id,
        data.billing_period
    )
    
    ## assign price
    subscription_data = data.model_dump()
    subscription_data["amount"] = plan_price.price
        
    business_subscription = BusinessSubscription(
        **subscription_data.model_dump(exclude_unset=True)
    )
    
    db.add(business_subscription)
    await db.commit()
    await db.refresh(business_subscription)

    return business_subscription

@admin_business_router.get("/business-subscription/", response_model=PaginatedBusinessSubscriptionResponse)
async def list_business_subscription(
    business_id: Optional[UUID] = None,
    status: Optional[SubscriptionStatus] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    query = select(BusinessSubscription).order_by(BusinessSubscription.created_at.desc())
    
    if business_id:
        query = query.where(
            BusinessSubscription.business_id == business_id
        )
    if status:
        query = query.where(
            BusinessSubscription.status == status
        )
    if is_active is not None:
        query = query.where(
            BusinessSubscription.is_active == is_active
        )
        
    return await get_paginated_result(db, query, skip, limit)

@admin_business_router.get("/business-subscription/{business_subscription_id}/", response_model=BusinessSubscriptionResponse)
async def get_business_subscription(
    business_subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(BusinessSubscription)
        .where(BusinessSubscription.id == business_subscription_id)
        .order_by(BusinessSubscription.created_at.desc())
    )
    business_subscription = result.scalars().first()
    if not business_subscription:
        raise HTTPException(
            status_code=404,
            detail="BusinessSubscription not found."
        )
    
    return business_subscription

@admin_business_router.patch("/business-subscription/{business_subscription_id}/", response_model=BusinessSubscriptionResponse)
async def update_business_subscription(
    business_subscription_id: UUID,
    data: UpdateBusinessSubscription,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(BusinessSubscription)
        .where(BusinessSubscription.id == business_subscription_id)
        .order_by(BusinessSubscription.created_at.desc())
    )
    business_subscription = result.scalars().first()
    if not business_subscription:
        raise HTTPException(
            status_code=404,
            detail="BusinessSubscription not found."
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(business_subscription, field, value)

    await db.commit()
    await db.refresh(business_subscription)
    
    return business_subscription

@admin_business_router.delete("/business-subscription/{business_subscription_id}/")
async def delete_business_subscription(
    business_subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(BusinessSubscription)
        .where(BusinessSubscription.id == business_subscription_id)
        .order_by(BusinessSubscription.created_at.desc())
    )
    business_subscription = result.scalars().first()
    if not business_subscription:
        raise HTTPException(
            status_code=404,
            detail="BusinessSubscription not found."
        )

    await db.delete(business_subscription)
    await db.commit()
    
    return {
        "status": True,
        "message": "Deleted successfully"
    }


#--------------------------
# Business Subscription Addon CRUD
#--------------------------
@admin_business_router.post("/business-subscription-addon/", response_model=BusinessSubscriptionAddonResponse)
async def create_business_subscription_addon(
    data: AdminCreateBusinessSubscriptionAddon,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    # validate plan addon
    business_service = BusinessService(db=db)
    plan_addon = await business_service.validate_plan_addon(data.addon_id)
    
    #assign price
    addon_data = data.model_dump(exclude_unset=True)
    addon_data["amount"] = plan_addon.price
    
    business_subscription_addon = BusinessSubscriptionAddon(
        **addon_data
    )
    
    db.add(business_subscription_addon)
    await db.commit()
    await db.refresh(business_subscription_addon)

    return business_subscription_addon

@admin_business_router.get("/business-subscription-addon/", response_model=PaginatedBusinessSubscriptionAddonResponse)
async def list_business_subscription_addon(
    business_subscription_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    query = select(BusinessSubscriptionAddon).order_by(BusinessSubscriptionAddon.created_at.desc())
    
    if business_subscription_id:
        query = query.where(
            BusinessSubscriptionAddon.business_subscription_id == business_subscription_id
        )
    if is_active is not None:
        query = query.where(
            BusinessSubscriptionAddon.is_active == is_active
        )
        
    return await get_paginated_result(db, query, skip, limit)

@admin_business_router.get("/business-subscription-addon/{business_subscription_addon_id}/", 
                           response_model=BusinessSubscriptionAddonResponse)
async def get_business_subscription_addon(
    business_subscription_addon_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(BusinessSubscriptionAddon)
        .where(BusinessSubscriptionAddon.id == business_subscription_addon_id)
        .order_by(BusinessSubscriptionAddon.created_at.desc())
    )
    business_subscription_addon = result.scalars().first()
    if not business_subscription_addon:
        raise HTTPException(
            status_code=404,
            detail="BusinessSubscriptionAddon not found."
        )
    
    return business_subscription_addon

@admin_business_router.patch("/business-subscription-addon/{business_subscription_addon_id}/", 
                           response_model=BusinessSubscriptionAddonResponse)
async def update_business_subscription_addon(
    business_subscription_addon_id: UUID,
    data: UpdateBusinessSubscriptionAddon,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(BusinessSubscriptionAddon)
        .where(BusinessSubscriptionAddon.id == business_subscription_addon_id)
        .order_by(BusinessSubscriptionAddon.created_at.desc())
    )
    business_subscription_addon = result.scalars().first()
    if not business_subscription_addon:
        raise HTTPException(
            status_code=404,
            detail="BusinessSubscriptionAddon not found."
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(business_subscription_addon, field, value)

    await db.commit()
    await db.refresh(business_subscription_addon)
    
    return business_subscription_addon

@admin_business_router.delete("/business-subscription-addon/{business_subscription_addon_id}/")
async def delete_business_subscription_addon(
    business_subscription_addon_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only),
):
    result = await db.execute(
        select(BusinessSubscriptionAddon)
        .where(BusinessSubscriptionAddon.id == business_subscription_addon_id)
        .order_by(BusinessSubscriptionAddon.created_at.desc())
    )
    business_subscription_addon = result.scalars().first()
    if not business_subscription_addon:
        raise HTTPException(
            status_code=404,
            detail="BusinessSubscriptionAddon not found."
        )
    
    await db.delete(business_subscription_addon)
    await db.commit()
    
    return {
        "status": True,
        "message": "Deleted successfully"
    }
