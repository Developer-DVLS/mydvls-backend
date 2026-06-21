from typing import List, Optional
from pydantic import BaseModel

from app.models.offers import DiscountType, Offer, OfferType

class ShopCategoryResponse(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class BOGOGetItemProduct(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True
    
class BOGOGetItem(BaseModel):
    id: int
    sku: str
    price: float = 0.0
    product: BOGOGetItemProduct
    
    class Config:
        from_attributes = True

class ShopBOGOMeta(BaseModel):
    id: int
    buy_item_id: int
    buy_quantity: int
    get_item_id: Optional[int] = None
    get_quantity: int
    apply_to_same_item: bool = True
    get_item: BOGOGetItem

class ShopOfferRead(BaseModel):
    id: int
    name: str
    code: str
    type: OfferType
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = 0
    bogo_meta: Optional[ShopBOGOMeta] = None

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
        
class ShopVariantOptionMini(BaseModel):
    id: int 
    name: str 
    
    class Config:
        from_attributes = True
        
class ShopVariantOptionValueMini(BaseModel):
    id: int 
    value: str
    variant_option: ShopVariantOptionMini
    
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
    variant_options: Optional[List[ShopVariantOptionValueMini]] = None
    
    best_offer: Optional[ShopOfferRead] = None
    
    class Config:
        from_attributes = True


class ShopDetailVariantOptionValueMini(BaseModel):
    id: int 
    value: str
    
    class Config:
        from_attributes = True
        
class ShopDetailVariantOptionMini(BaseModel):
    id: int 
    name: str 
    values: List[ShopDetailVariantOptionValueMini]
    
    class Config:
        from_attributes = True
        
class ShopProductDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: ShopCategoryResponse
    variant_options: Optional[List[ShopDetailVariantOptionMini]] = None
    variants: Optional[List[ShopProductVariant]] = None
    
    class Config:
        from_attributes = True