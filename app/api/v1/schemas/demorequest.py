from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, PositiveInt
from uuid import UUID
from pydantic import field_validator

class UserDemoRequestCreate(BaseModel):
    first_name: str 
    last_name: str 
    email: EmailStr 
    phone: str 
    business_name: Optional[str] = None
    business_size: Optional[str] = None
    business_type: Optional[str] = None
    branch_count: str
    opening_type: str
    preferred_date: Optional[datetime] = None
    timezone: Optional[str] = None
    message: Optional[str] = None
    recaptcha_token: str
    
    @field_validator("preferred_date", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        return None if v == "" else v

class DemoRequestResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    full_name: str
    email: EmailStr 
    phone: str 
    business_name: Optional[str] = None
    business_size: Optional[str] = None
    business_type: Optional[str] = None
    branch_count: str
    opening_type: str
    plan_id: Optional[int] = None
    preferred_date: Optional[datetime] = None
    timezone: Optional[str] = None
    message: Optional[str] = None
    status:  Optional[str] = None
    assigned_to: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meeting_link: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
class PaginatedDemoRequestResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[DemoRequestResponse]] = None

    class Config:
        from_attributes = True

class DemoRequestUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None 
    phone: Optional[str] = None 
    business_name: Optional[str] = None
    business_size: Optional[str] = None
    business_type: Optional[str] = None
    branch_count: Optional[str] = None
    opening_type: Optional[str] = None
    plan_id: Optional[int] = None
    preferred_date: Optional[datetime] = None
    timezone: Optional[str] = None
    message: Optional[str] = None
    status:  Optional[str] = None
    assigned_to: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meeting_link: Optional[str] = None