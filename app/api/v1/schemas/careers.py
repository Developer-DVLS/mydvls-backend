from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from app.models.careers import CareerStatus


class CareerQnA(BaseModel):
    question: str
    answer: str

class CareerBase(BaseModel):
    full_name: str 
    email: EmailStr 
    phone: str 
    address: str 
    position: Optional[str] = None
    cover_letter: Optional[str] = None
    resume: str 
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None 
    qna: Optional[List[CareerQnA]] = []
    
class CreateCareer(CareerBase):
    pass 

class CareerResponse(CareerBase):
    id: int 
    notes: Optional[str] = None
    status: CareerStatus
    created_at: datetime
    
    class Config:
        from_attributes = True

class PaginatedCareerResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[CareerResponse]] = None  

class UpdateCareerStatus(BaseModel):
    notes: Optional[str] = None
    status: CareerStatus