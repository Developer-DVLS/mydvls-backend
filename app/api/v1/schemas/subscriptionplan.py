from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class SubscriptionPlanCreate(BaseModel):
    name: str
    key: str
    description: Optional[str] = None
    price: float
    billing_period: str
    trial_days: int
    is_popular: bool
    is_active: bool
    sort_order: int

class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    slug: str
    key: str
    description: Optional[str] = None
    price: float
    billing_period: str
    trial_days: int
    is_popular: bool
    is_active: bool
    sort_order: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class PaginatedSubscriptionPlanResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[SubscriptionPlanResponse]] = None

    class Config:
        from_attributes = True

class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    billing_period: Optional[str] = None
    trial_days: Optional[int] = None
    is_popular: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None