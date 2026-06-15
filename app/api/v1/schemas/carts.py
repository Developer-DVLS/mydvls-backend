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
    category_id: Optional[int] = None
    
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
    price: float
    product_id: int
    product: Optional[ProductResponse] = None
    # images: Optional[List[VariantImageResponse]] = None
    image: Optional[str] = None
    
    class Config:
        from_attributes = True

class CartGetItemProduct(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category_id: int
    
    class Config:
        from_attributes = True
        
class CartGetItem(BaseModel):
    id: int
    sku: str
    price: float = 0.0
    image: Optional[str] = None
    product: CartGetItemProduct
    
    class Config:
        from_attributes = True
        
class CartBOGOMeta(BaseModel):
    id: int
    buy_item_id: int
    buy_quantity: int
    get_item_id: Optional[int] = None
    get_quantity: int
    apply_to_same_item: bool = True
    get_item: Optional[CartGetItem] = None
    
    class Config:
        from_attributes = True

class CartOfferResponse(BaseModel):
    id: int
    name: str
    code: str
    type: OfferType
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = 0
    bogo_meta: Optional[CartBOGOMeta] = None

    class Config:
        from_attributes = True

class CartBOGOFreeItem(BaseModel):
    product_variant_id: int
    quantity: int
    unit_price: Optional[float] = 0
    # product_variant: Optional[ProductVariantResponse] = None
    
    class Config:
        from_attributes = True
    
class CartProductResponse(BaseModel):
    id: int
    product_variant_id: int
    quantity: int
    quantity_after_combo: int = 0
    unit_price: float
    product_variant: Optional[ProductVariantResponse] = None
    offer: Optional[CartOfferResponse] = None
    bogo_free_item: Optional[CartBOGOFreeItem] = None
    subtotal: Optional[float] = 0
    discount_amount: Optional[float] = 0
    discounted_amount: Optional[float] = 0
    # created_at: datetime
    # updated_at: datetime
    
    class Config:
        from_attributes = True
        
class CartComboOfferItem(BaseModel):
    id: int
    product_variant_id: int 
    quantity: int
    
    class Config:
        from_attributes = True

class CartComboOffer(BaseModel):
    id: int
    name: str
    discount_type: str
    applied_count: int
    bundle_price: float
    discount: float
    final_price: float
    # stackable: bool
    priority: int
    items: List[CartComboOfferItem]
    
    class Config:
        from_attributes = True
    
class CartResponse(BaseModel):
    id: int
    user_id: Optional[UUID] = None
    coupon_id: Optional[int] = None
    status: CartStatus
    cart_products: Optional[List[CartProductResponse]] = None
    subtotal: Optional[float] = 0
    discount_amount: Optional[float] = 0
    discounted_amount: Optional[float] = 0
    total_discount_amount: Optional[float] = 0
    tax_percent: Optional[float] = 0.00
    tax_amount: Optional[float] = 0.00
    total_amount: Optional[float] = 0
    coupon_applied: Optional[bool] = False
    coupon_applicable: Optional[bool] = None
    coupon_message: Optional[str] = None
    coupon_discount_amount: Optional[float] = 0
    combo_offers: Optional[List[CartComboOffer]] = None
    bogo_offer_exists: Optional[bool] = False
    
    class Config:
        from_attributes = True
        
class ComboOfferToCart(BaseModel):
    combo_offer_id: int
    quantity: int

class CartProductQtyUpdate(BaseModel):
    quantity: int