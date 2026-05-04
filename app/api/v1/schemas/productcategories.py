from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class CategoryRequest(BaseModel):
    name : str
    description: str
    image_url: str
    is_active: bool
    is_featured: bool
    ordering: int

class CategoryResponse(BaseModel):
    id: int
    name : str
    description: str
    image_url: str
    is_active: bool
    is_featured: bool
    ordering: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class PaginatedCategoryResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[CategoryResponse]] = None

    class Config:
        from_attributes = True

class CategoryUpdateRequest(BaseModel):
    name : Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    ordering: Optional[int] = None
    
class ProductCategoryDropdown(BaseModel):
    id: int
    name: str