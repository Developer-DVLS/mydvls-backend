from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ProductBase(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None
    is_active: bool = False
    is_featured: bool = False

class ProductRequest(ProductBase):
    pass

class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class CategoryMini(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryMini] = None

    class Config:
        from_attributes = True


class PaginatedProductResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ProductResponse]] = None

    class Config:
        from_attributes = True
        
        
# for the nested product and variant 
class ProductVariantNestedRequest(BaseModel):
    sku: str
    price: float = 0.0
    cost_price: float = 0.0
    margin: float = 0.0
    stock_quantity: int = 0
    is_active: bool = True
    is_featured: bool = False

class ProductCreateRequest(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None
    is_active: bool = False
    is_featured: bool = False

    variants: List[ProductVariantNestedRequest]
    
class ProductVariantResponse(BaseModel):
    id: int
    sku: str
    price: float
    stock_quantity: int

    class Config:
        from_attributes = True


class NestedProductResponse(BaseModel):
    id: int
    name: str
    category_id: int
    is_active: bool
    is_featured: bool
    variants: List[ProductVariantResponse]

    class Config:
        from_attributes = True