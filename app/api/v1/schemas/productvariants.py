from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ProductVariantBase(BaseModel):
    product_id: int
    sku: str
    price: float = 0.0
    cost_price: float = 0.0
    margin: float = 0.0
    stock_quantity: int = 0
    is_active: bool = True
    is_featured: bool = False
    
class ProductVariantImageBase(BaseModel):
    image_url: str

class ProductVariantImageRequest(ProductVariantImageBase):
    pass

class ProductVariantImageResponse(ProductVariantImageBase):
    id: int
    variant_id: int
    
class ProductVariantRequest(ProductVariantBase):
    variant_images: Optional[List[ProductVariantImageRequest]] = None

class ProductVariantUpdate(BaseModel):
    product_id: Optional[int] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    margin: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    
# class ProductVariantResponse(ProductVariantBase):
#     id: int
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True
        
class ProductMini(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
        
class ImageMini(BaseModel):
    id: int
    image_url: str

    class Config:
        from_attributes = True

class ProductVariantResponse(ProductVariantBase):
    id: int
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductMini] = None
    images: Optional[List[ImageMini]] = None

    class Config:
        from_attributes = True

class PaginatedProductVariantResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ProductVariantResponse]] = None

    class Config:
        from_attributes = True