from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscriptionplan import Service, SubscriptionPlan, SubscriptionPlanAddon, SubscriptionPlanAddonPrice, SubscriptionPlanPrice

class BusinessService:

    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_service_plan(
        self,
        service_id,
        plan_id
    ):
        service_result = await self.db.execute(
            select(Service)
            .where(Service.id == service_id)
            )
        service = service_result.scalars().first()
        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"Service {service_id} not found."
            )

        plan_result = await self.db.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.id == plan_id,
                SubscriptionPlan.service_id == service_id
                )
        )
        plan = plan_result.scalars().first()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail=f"Plan {plan_id} not found."
            )
        
        return service, plan
    
    async def get_plan_price(
        self, 
        plan_id,
        billing_period
    ):
        plan_result = await self.db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.id == plan_id)
        )
        plan = plan_result.scalars().first()
        if not plan:
            raise HTTPException(
                status_code=404,
                detail=f"Plan {plan_id} not found."
            )
        
        price_result = await self.db.execute(
            select(SubscriptionPlanPrice)
            .where(
                SubscriptionPlanPrice.subscription_plan_id == plan_id,
                SubscriptionPlanPrice.billing_period == billing_period
                )
        )
        price = price_result.scalars().first()
        if not price:
            raise HTTPException(
                status_code=404,
                detail=f"No price found for billing period '{billing_period}'."
            )
        
        return price
    
    async def validate_plan_addon(
        self,
        addon_id,
        billing_period
    ):
        plan_addon_result = await self.db.execute(
            select(SubscriptionPlanAddon)
            .where(SubscriptionPlanAddon.id == addon_id)
        )
        plan_addon = plan_addon_result.scalars().first()
        if not plan_addon:
            raise HTTPException(
                status_code=404,
                detail=f"PlanAddon {addon_id} not found."
            )
        
        addon_price_result = await self.db.execute(
            select(SubscriptionPlanAddonPrice)
            .where(
                SubscriptionPlanAddonPrice.subscription_plan_addon_id == addon_id,
                SubscriptionPlanAddonPrice.billing_period == billing_period
                )
        )
        addon_price = addon_price_result.scalars().first()
        if not plan_addon:
            raise HTTPException(
                status_code=404,
                detail=f"AddonPrice not found of billing period {billing_period}."
            )
        
        return plan_addon, addon_price
        
        