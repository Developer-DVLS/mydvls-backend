from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime, time

from app.models.business import SubscriptionStatus


class CreateBusinessSubscriptionAddons(BaseModel):
    addon_id: List[int]
    # quantity: int
    
class AddBusinessSubscription(BaseModel):
    business_id: UUID
    service_id: int
    plan_id: int
    billing_period: str
    auto_renew: bool
    
    addons: Optional[List[CreateBusinessSubscriptionAddons]] = None
    
class CreateBusinessSubscription(BaseModel):
    service_id: int
    plan_id: int
    billing_period: str
    auto_renew: bool
    
    addons: Optional[List[CreateBusinessSubscriptionAddons]] = None

class CreateBusiness(BaseModel):
    # Business Details
    legal_business_name: str
    dba_name: Optional[str] = None
    owner_name: str

    business_type: Optional[str] = None
    industry: Optional[str] = None

    email: EmailStr
    phone: str
    logo: Optional[str]

    website_url: Optional[str] = None
    business_description: Optional[str] = None
    
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    team_size: Optional[str] = None
    
    product_categories: Optional[List[str]] = None
    
    template: Optional[List[dict]] = None

    # Address
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    #legal details
    tax_number: Optional[str] = None
    employer_identification_number: Optional[str] = None
    business_license_number: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    vat_number: Optional[str] = None
    
    subscriptions: CreateBusinessSubscription
    
    recaptcha_token: str

## response schemas
class BusinessResponse(BaseModel):
    id: UUID
    user_id: UUID
    legal_business_name: str
    dba_name: Optional[str] = None
    owner_name: str
    business_type: Optional[str] = None
    industry: Optional[str] = None
    email: EmailStr
    phone: str
    logo: Optional[str]
    website_url: Optional[str] = None
    business_description: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    team_size: Optional[str] = None
    product_categories: Optional[List[str]] = None
    is_verified: bool
    is_active: bool
    template: Optional[List[dict]] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    employer_identification_number: Optional[str] = None
    business_license_number: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    vat_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
class PaginatedBusinessResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[BusinessResponse]] = None  
    
class BusinessSubscriptionResponse(BaseModel):
    id:UUID
    business_id: UUID
    service_id: int
    plan_id: int
    status: SubscriptionStatus
    billing_period: str
    amount: float
    currency: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: bool
    is_active: bool
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class PaginatedBusinessSubscriptionResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[BusinessSubscriptionResponse]] = None  
    

class SubscriptionPlanAddonResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class BusinessSubscriptionAddonResponse(BaseModel):
    id: int
    business_subscription_id: UUID
    addon_id: int
    addon: SubscriptionPlanAddonResponse
    amount: float
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
class PaginatedBusinessSubscriptionAddonResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[BusinessSubscriptionAddonResponse]] = None 
    
##update schema 
class UpdateBusiness(BaseModel):
    legal_business_name: Optional[str] = None
    dba_name: Optional[str] = None
    owner_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    logo: Optional[str]
    website_url: Optional[str] = None
    business_description: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    team_size: Optional[str] = None
    product_categories: Optional[List[str]] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    template: Optional[List[dict]] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    employer_identification_number: Optional[str] = None
    business_license_number: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    vat_number: Optional[str] = None
    
class UpdateUserBusiness(BaseModel):
    legal_business_name: Optional[str] = None
    dba_name: Optional[str] = None
    owner_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    logo: Optional[str]
    website_url: Optional[str] = None
    business_description: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    team_size: Optional[str] = None
    product_categories: Optional[List[str]] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    employer_identification_number: Optional[str] = None
    business_license_number: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    vat_number: Optional[str] = None

class UpdateBusinessSubscription(BaseModel):
    service_id:  Optional[int] = None
    plan_id:  Optional[int] = None
    status:  Optional[SubscriptionStatus] = None
    billing_period: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    is_active: Optional[bool] = None
    
class UpdateBusinessSubscriptionAddon(BaseModel):
    addon_id: Optional[int] = None
    amount: Optional[float] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    
## create schema for admin
class AdminCreateBusiness(BaseModel):
    user_id: UUID
    
    legal_business_name: str
    dba_name: Optional[str] = None
    owner_name: str
    
    business_type: Optional[str] = None
    industry: Optional[str] = None

    email: EmailStr
    phone: str
    logo: Optional[str]

    website_url: Optional[str] = None
    business_description: Optional[str] = None
    
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    team_size: Optional[str] = None
    
    product_categories: Optional[List[str]] = None
    
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    template: Optional[List[dict]] = None
    
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    tax_number: Optional[str] = None
    employer_identification_number: Optional[str] = None
    business_license_number: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    vat_number: Optional[str] = None
    

class AdminCreateBusinessSubscription(BaseModel):
    business_id: UUID
    service_id:  int
    plan_id:  int
    status:  SubscriptionStatus
    billing_period: str
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: bool
    is_active: bool
    
    @field_validator("starts_at", "expires_at", mode="before")
    @classmethod
    def remove_timezone(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", ""))

        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)

        return v

class AdminCreateBusinessSubscriptionAddon(BaseModel):
    business_subscription_id: UUID
    addon_id: int
    amount: Optional[float] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    
    @field_validator("starts_at", "expires_at", mode="before")
    @classmethod
    def remove_timezone(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", ""))

        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)

        return v