from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.models.carts import CartStatus

class CartBase(BaseModel):
    user_id: UUID
    coupon_id: int 
    status: CartStatus

class CartResponse(CartBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PaginatedCartResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[CartResponse]] = None   
        
class CartProductResponse(BaseModel):
    id: int
    product_variant_id: int
    quantity: int
    unit_price: float
    is_free_item:  Optional[bool] = None
    trigger_cart_item_id:  Optional[int] = None
    parent_offer_id: Optional[int] = None
    

class CartDetailResponse(CartBase):
    id: int
    cart_products: Optional[List[CartProductResponse]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True