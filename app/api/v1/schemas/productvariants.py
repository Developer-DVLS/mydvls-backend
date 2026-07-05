from pydantic import BaseModel, field_validator
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
    features: Optional[str] = None
    description: Optional[str] = None
    
    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str):
        return v.strip().lower().replace(" ", "-")
    
class ProductVariantImageBase(BaseModel):
    image_url: str

class CreateProductVariantImage(ProductVariantImageBase):
    variant_id: int

class ProductVariantImageRequest(ProductVariantImageBase):
    pass

class ProductVariantImageResponse(ProductVariantImageBase):
    id: int
    variant_id: int
    
class ProductAttributeRequest(BaseModel):
    key: str
    value: str

class ProductAttributeCreate(BaseModel):
    variant_id: int
    key: str
    value: str

class ProductAttributeResponse(ProductAttributeCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class ProductAttributeUpdate(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    
class ProductVariantRequest(ProductVariantBase):
    variant_images: Optional[List[ProductVariantImageRequest]] = None
    attributes: Optional[List[ProductAttributeRequest]] = None
    variant_option_value_ids: Optional[List[int]] = []

class ProductVariantUpdate(BaseModel):
    product_id: Optional[int] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    margin: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    variant_option_value_ids: Optional[List[int]] = []
    features: Optional[str] = None
    description: Optional[str] = None
    
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
        
class ProductAttributeMini(BaseModel):
    id: int
    key: str
    value: str

class VariantOptionMini(BaseModel):
    id: int 
    name: str 
class VariantOptionMini(BaseModel):
    id: int 
    value: str
    variant_option: VariantOptionMini
    
class ProductVariantResponse(ProductVariantBase):
    id: int
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductMini] = None
    images: Optional[List[ImageMini]] = None
    attributes: Optional[List[ProductAttributeMini]] = None
    variant_options: Optional[List[VariantOptionMini]] = None

    class Config:
        from_attributes = True

class PaginatedProductVariantResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ProductVariantResponse]] = None

    class Config:
        from_attributes = True

class ProductVariantDropdown(BaseModel):
    id: int
    sku: str
    product_name: str
    
    class Config:
        from_attributes = True