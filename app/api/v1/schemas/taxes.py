from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.models.tax import TaxScope

class TaxConfigBase(BaseModel):
    name: str
    code: str
    tax_scope: TaxScope
    tax_percentage: float
    description: Optional[str] = None
    is_active: bool
    
class TaxConfigCreate(TaxConfigBase):
    pass 

class TaxConfigResponse(TaxConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime 
    
    class Config:
        from_attributes = True

class PaginatedTaxConfigResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[TaxConfigResponse]] = None  
    
class TaxConfigUpdate(BaseModel):
    name:  Optional[str] = None
    code:  Optional[str] = None
    tax_scope:  Optional[TaxScope] = None
    tax_percentage:  Optional[float] = None
    description: Optional[str] = None
    is_active:  Optional[bool] = None