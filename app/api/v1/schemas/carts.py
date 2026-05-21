from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.models.carts import CartStatus
from app.models.offers import DiscountType, OfferType

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    
    class Config:
        from_attributes = True

class VariantImageResponse(BaseModel):
    id: int
    image_url: str
    
    class Config:
        from_attributes = True
    
class ProductVariantResponse(BaseModel):
    id: int
    sku: str
    price: int
    product: ProductResponse
    # images: VariantImageResponse
    
    class Config:
        from_attributes = True

class CartOfferResponse(BaseModel):
    id: int
    name: str
    code: str
    type: OfferType
    discount_type: Optional[DiscountType]
    discount_value: Optional[float]

    class Config:
        from_attributes = True
        
class CartProductResponse(BaseModel):
    id: int
    product_variant_id: int
    quantity: int
    unit_price: int
    product_variant: Optional[ProductVariantResponse] = None
    offer: Optional[CartOfferResponse] = None
    subtotal: Optional[int] = 0
    discount_amount: Optional[int] = 0
    discounted_amount: Optional[int] = 0
    # created_at: datetime
    # updated_at: datetime
    
    class Config:
        from_attributes = True
        
class CartResponse(BaseModel):
    id: int
    user_id: Optional[UUID] = None
    status: CartStatus
    cart_products: Optional[List[CartProductResponse]] = None
    subtotal: Optional[int] = 0
    discount_amount: Optional[int] = 0
    discounted_amount: Optional[int] = 0
    total_amount: Optional[int] = 0
    coupon_applied: Optional[bool] = False
    coupon_applicable: Optional[bool] = None
    coupon_message: Optional[str] = None
    coupon_discount_amount: Optional[int] = 0
    
    class Config:
        from_attributes = True