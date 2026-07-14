from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

class ContactBase(BaseModel):
    first_name: str 
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None 
    phone: str 
    message: Optional[str]
    
class ContactCreate(ContactBase):
    recaptcha_token: str

class ContactResponse(ContactBase):
    id: int 
    created_at: datetime 
    updated_at: datetime

class PaginatedContactResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ContactResponse]] = None  