from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

class SubscriptionPlanCreate(BaseModel):
    name: str
    key: str

    description: Optional[str] = None
    features: Optional[List[str]] = None

    trial_days: int = 0

    is_popular: bool = False
    is_active: bool = True

    max_users: Optional[int] = None
    max_locations: Optional[int] = None
    max_products: Optional[int] = None

    sort_order: int = 0

class SubscriptionPlanResponse(BaseModel):
    id: int

    name: str
    slug: str
    key: str

    description: Optional[str] = None
    features: Optional[list] = None

    trial_days: int

    is_popular: bool
    is_active: bool

    max_users: Optional[int]
    max_locations: Optional[int]
    max_products: Optional[int]

    sort_order: int

    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
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
    

class SubscriptionPlanPriceCreate(BaseModel):
    billing_period: str
    price: Decimal

class SubscriptionPlanAddonCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: Decimal
    
class NestedSubscriptionPlanCreate(BaseModel):
    name: str
    key: str

    description: Optional[str] = None
    features: Optional[List[str]] = None

    trial_days: int = 0

    is_popular: bool = False
    is_active: bool = True

    max_users: Optional[int] = None
    max_locations: Optional[int] = None
    max_products: Optional[int] = None

    sort_order: int = 0

    prices: List[SubscriptionPlanPriceCreate]
    addons: Optional[List[SubscriptionPlanAddonCreate]] = None
    
class ServiceCreate(BaseModel):
    global_type: str
    badge: Optional[str] = None

    title: str
    sub_title: Optional[str] = None

    bottom_card: Optional[Dict[str, Any]] = None

    plans: List[NestedSubscriptionPlanCreate]
    

#nested response schemas
class SubscriptionPlanPriceResponse(BaseModel):
    id: int
    subscription_plan_id: int
    billing_period: str
    price: Decimal

    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionPlanAddonResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: Decimal

    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NestedSubscriptionPlanResponse(BaseModel):
    id: int

    name: str
    slug: str
    key: str

    description: Optional[str] = None
    features: Optional[list] = None

    trial_days: int

    is_popular: bool
    is_active: bool

    max_users: Optional[int]
    max_locations: Optional[int]
    max_products: Optional[int]

    sort_order: int

    prices: List[SubscriptionPlanPriceResponse]
    addons: List[SubscriptionPlanAddonResponse]

    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ServiceResponse(BaseModel):

    id: int

    global_type: str
    badge: Optional[str] = None

    title: str
    sub_title: Optional[str] = None

    bottom_card: Optional[Any] = None

    plans: List[NestedSubscriptionPlanResponse]

    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    
class PaginatedServiceResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ServiceResponse]] = None

    class Config:
        from_attributes = True
        
# Service schemas
class ServiceUpdate(BaseModel):
    global_type: Optional[str] = None
    badge: Optional[str]= None
    title: Optional[str]= None
    sub_title: Optional[str]= None
    bottom_card: Optional[Dict[str, Any]] = None
    
# Subscription plan price schema
class SubscriptionPlanPriceUpdate(BaseModel):
    billing_period: Optional[str] = None
    price: Optional[Decimal] = None
    
# Subscription plan addon schema
class SubscriptionPlanAddonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None