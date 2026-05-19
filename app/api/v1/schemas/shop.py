from typing import List, Optional
from pydantic import BaseModel

from app.models.offers import DiscountType, Offer, OfferType

class ShopCategoryResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class ShopOfferRead(BaseModel):
    id: int
    name: str
    code: str
    type: OfferType
    discount_type: Optional[DiscountType]
    discount_value: Optional[float]

    class Config:
        from_attributes = True

class ShopProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: Optional[int] = None
    is_featured: Optional[bool] = None
    image_url: Optional[str] = None
    category_id: int
    best_offer: Optional[ShopOfferRead] = None
    
    class Config:
        from_attributes = True

class PaginatedShopProductResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ShopProductResponse]] = None

    class Config:
        from_attributes = True
        

class ShopImageMini(BaseModel):
    id: int
    image_url: str

    class Config:
        from_attributes = True

class ShopProductAttribute(BaseModel):
    id: int
    key: str
    value: str 
    
    class Config:
        from_attributes = True

class ShopProductVariant(BaseModel):
    id: int
    sku: str
    price: float = 0.0
    cost_price: float = 0.0
    margin: float = 0.0
    stock_quantity: int = 0
    is_active: bool = True
    is_featured: bool = False
    
    images: Optional[List[ShopImageMini]] = None
    attributes: Optional[List[ShopProductAttribute]] = None
    
    class Config:
        from_attributes = True
    
        
class ShopProductDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: ShopCategoryResponse
    variants: Optional[List[ShopProductVariant]] = None
    
    class Config:
        from_attributes = True