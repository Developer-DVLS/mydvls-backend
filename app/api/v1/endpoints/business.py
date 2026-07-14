from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.business import (
    Business,
    BusinessSubscription,
    BusinessSubscriptionAddon,
    SubscriptionStatus,
)
from app.models.subscriptionplan import (
    Service,
    SubscriptionPlan,
    SubscriptionPlanAddon,
)
from app.api.v1.schemas.business import  AddBusinessSubscription, BusinessResponse, CreateBusiness, PaginatedBusinessResponse, UpdateUserBusiness
from app.core.database import get_db
from app.services.businessservice import BusinessService
from app.services.recaptchaservice import RecaptchaService
from app.services.security import get_current_user
from app.utils.pagination import get_paginated_result
from app.utils.teams_alert import team_alert


business_router = APIRouter(prefix="/businesses", tags=["Businesses"])



@business_router.post("/register/")
async def register_business(
    request: Request,
    payload: CreateBusiness,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # reCptcha
    await RecaptchaService.verify(
        token=payload.recaptcha_token,
        action="register_business"
    )
    
    business_service = BusinessService(db=db)
    
    # Prevent duplicate business email
    existing = await db.scalar(
        select(Business).where(Business.email == payload.email.lower())
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Business with this email already exists."
        )

    business = Business(
        user_id=current_user.id,
        
        legal_business_name=payload.legal_business_name,
        dba_name=payload.dba_name,
        owner_name=payload.owner_name,

        business_type=payload.business_type or None,
        industry=payload.industry or None,

        email=payload.email.lower(),
        phone=payload.phone,
        logo=payload.logo or None,

        website_url=payload.website_url or None,
        business_description=payload.business_description or None,

        timezone=payload.timezone or None,
        currency=payload.currency or "USD" if "currency" in payload else None,
        language=payload.language or "en" if "language" in payload else None,

        opening_time=payload.opening_time or None if "opening_time" in payload else None,
        closing_time=payload.closing_time or None if "closing_time" in payload else None,

        team_size=payload.team_size or None if "team_size" in payload else None,
        product_categories=payload.product_categories or None if "product_categories" in payload else None,

        template=payload.template or None if "template" in payload else None,

        address_line1=payload.address_line1,
        address_line2=payload.address_line2 or None,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,

        tax_number=payload.tax_number or None if "tax_number" in payload else None,
        employer_identification_number=payload.employer_identification_number or None 
                                            if "employer_identification_number" in payload else None,
        business_license_number=payload.business_license_number or None if "business_license_number" in payload else None,
        insurance_policy_number=payload.insurance_policy_number or None if "insurance_policy_number" in payload else None,
        vat_number=payload.vat_number or None if "vat_number" in payload else None,

        is_verified=False,
        is_active=False,
    )

    db.add(business)

    await db.flush()

    # Create subscriptions
    if  payload.subscriptions:
        subscription_data = payload.subscriptions
        
        # validate service and plan
        await business_service.validate_service_plan(
            subscription_data.service_id, 
            subscription_data.plan_id
            )
        #get price of a plan with selected billing_period
        plan_price = await business_service.get_plan_price(
            subscription_data.plan_id,
            subscription_data.billing_period
        )

        subscription = BusinessSubscription(
            business_id=business.id,
            service_id=subscription_data.service_id,
            plan_id=subscription_data.plan_id,

            billing_period=subscription_data.billing_period,

            # calculate after payment is done
            # starts_at=subscription_data.starts_at,
            # expires_at=subscription_data.expires_at,

            amount=plan_price.price,

            auto_renew=subscription_data.auto_renew,
            is_active=False,

            status=SubscriptionStatus.PENDING,
        )

        db.add(subscription)

        await db.flush()

        if subscription_data.addons:

            for addon in subscription_data.addons:

                for addon_id in addon.addon_id:

                    plan_addon, addon_price = await business_service.validate_plan_addon(addon_id, subscription.billing_period)

                    db.add(
                        BusinessSubscriptionAddon(
                            business_subscription_id=subscription.id,
                            addon_id=addon_id,
                            amount=addon_price.price,
                            # calculate after payment is done
                            # starts_at=addon.starts_at,
                            # expires_at=addon.expires_at,
                            is_active=False,
                        )
                    )

    await db.commit()

    await db.refresh(business)
    
    #send team alert
    # await team_alert(
    #     title="NEW BUSINESS REGISTERED -MYDVLS",
    #     monitor="New business have registered and subscribed for a plan. Review it ASAP and response to it.",
    #     monitor_url="https://mydvls.chowchownow.com/"
    # )

    return {
        "message": "Business registered successfully.",
        "business_id": business.id,
    }


@business_router.post("/add-subscription-plan/")
async def add_business_subscription_plan(
    payload: AddBusinessSubscription,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription_data = payload

    business_service = BusinessService(db=db)
    # validate service and plan
    await business_service.validate_service_plan(
        subscription_data.service_id, 
        subscription_data.plan_id
        )
    #get price of a plan with selected billing_period
    plan_price = await business_service.get_plan_price(
        subscription_data.plan_id,
        subscription_data.billing_period
    )

    subscription = BusinessSubscription(
        business_id=subscription_data.business_id,
        service_id=subscription_data.service_id,
        plan_id=subscription_data.plan_id,

        billing_period=subscription_data.billing_period,
        amount=plan_price.price,
        auto_renew=subscription_data.auto_renew,
        
        is_active=False,
        status=SubscriptionStatus.PENDING,
    )

    db.add(subscription)

    await db.flush()

    if subscription_data.addons:
        for addon in subscription_data.addons:
            for addon_id in addon.addon_id:
                plan_addon = await business_service.validate_plan_addon(addon_id)
                db.add(
                    BusinessSubscriptionAddon(
                        business_subscription_id=subscription.id,
                        addon_id=addon_id,
                        amount=plan_addon.price,
                        is_active=False,
                    )
                )

    await db.commit()
    
    await db.refresh(subscription)
    
    #send team alert
    # await team_alert(
    #     title="EXISTING BUSINESS SUBSCRIBED FOR NEW PLAN -MYDVLS",
    #     monitor="Existing business have subscribed for a plan. Review it ASAP and response to it.",
    #     monitor_url="https://mydvls.chowchownow.com/"
    # )

    return {
        "message": "subscription Plan registered successfully.",
        "business_id": subscription.id,
    }
    
@business_router.get("/user-business/", response_model=PaginatedBusinessResponse)
async def list_user_business(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    
):
    query = select(Business).where(
        Business.user == current_user
        ).order_by(Business.created_at.desc())
    return await get_paginated_result(db, query, skip, limit)

@business_router.patch("/business/{business_id}/", response_model=BusinessResponse)
async def update_user_business( 
    business_id: UUID,
    data: UpdateUserBusiness,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Business)
        .where(
            Business.id == business_id,
            Business.user == current_user
            )
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