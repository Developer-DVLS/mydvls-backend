from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class DeliveryConfigBase(BaseModel):
    min_distance: float
    max_distance: float
    delivery_fee: float
    is_active: bool

class DeliveryConfigCreate(DeliveryConfigBase):
    pass 

class DeliveryConfigResponse(DeliveryConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class PaginatedDeliveryConfigResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[DeliveryConfigResponse]] = None  

class DeliveryConfigUpdate(BaseModel):
    min_distance: Optional[float] = None
    max_distance: Optional[float] = None
    delivery_fee: Optional[float] = None
    is_active: Optional[bool] = None