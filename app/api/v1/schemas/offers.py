# app/schemas/offer.py

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from app.models.offers import (
    ComboDiscountType,
    OfferType,
    DiscountType,
    TargetType,
)


# -----------------------------
# Offer Target Schemas
# -----------------------------
class OfferTargetBase(BaseModel):
    target_type: TargetType
    target_id: int


class OfferTargetCreate(OfferTargetBase):
    pass


class OfferTargetResponse(OfferTargetBase):
    id: int

    class Config:
        from_attributes = True

class OfferTargetUpdate(BaseModel):
    target_id: Optional[int] = None
    
# -----------------------------
# BOGO Schemas
# -----------------------------
class OfferBOGOBase(BaseModel):
    buy_item_id: int
    buy_quantity: int
    get_item_id: Optional[int] = None
    get_quantity: int
    apply_to_same_item: bool = True


class OfferBOGOCreate(OfferBOGOBase):
    pass


class OfferBOGOResponse(OfferBOGOBase):
    id: int

    class Config:
        from_attributes = True

class OfferBOGOUpdate(BaseModel):
    buy_item_id: Optional[int] = None
    buy_quantity: Optional[int] = None
    get_item_id: Optional[int] = None
    get_quantity: Optional[int] = None
    apply_to_same_item: Optional[bool] = None

# -----------------------------
# Offer Schemas
# -----------------------------
class OfferBase(BaseModel):
    name: str
    code: str
    image_url: Optional[str] = None

    type: OfferType
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None

    start_date: datetime
    end_date: datetime

    is_active: bool = True

    usage_limit_per_user: Optional[int] = None
    usage_limit_total: Optional[int] = None

    min_spent_amount: float = 0.0
    max_discount_amount: float = 0.0


class OfferCreate(OfferBase):
    targets: Optional[List[OfferTargetCreate]] = None
    bogo_meta: Optional[OfferBOGOCreate] = None
    
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def remove_timezone(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", ""))

        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)

        return v


class OfferUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    image_url: Optional[str] = None

    # type: Optional[OfferType] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    is_active: Optional[bool] = None

    usage_limit_per_user: Optional[int] = None
    usage_limit_total: Optional[int] = None

    min_spent_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None

class OfferResponse(OfferBase):
    id: int

    targets: List[OfferTargetResponse] = []
    bogo_meta: Optional[OfferBOGOResponse] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaginatedOfferResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[OfferResponse]] = None    
    

# combo offer
class ComboOfferBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool
    start_date: datetime
    end_date: datetime
    discount_type: ComboDiscountType
    discount_value: float
    priority: int
    stackable: bool 
    
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def remove_timezone(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", ""))

        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)

        return v

class ComboOfferItemBase(BaseModel):
    product_variant_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = 1
    
class ComboOfferCreate(ComboOfferBase):
    items: List[ComboOfferItemBase]

class ComboOfferItemCreate(ComboOfferItemBase):
    combo_offer_id: int

class ComboOfferProductVariantProduct(BaseModel):
    id: int
    name: str 
    
    class Config:
        from_attributes = True
    
class ComboOfferProductVariant(BaseModel):
    id: int 
    sku: str
    price: float
    product: ComboOfferProductVariantProduct
    
    class Config:
        from_attributes = True
        
class ComboOfferItemResponse(ComboOfferItemBase):
    id: int
    product_variant: Optional[ComboOfferProductVariant] = None
    # combo_offer_id: int
    created_at: datetime
    updated_at:  datetime
    
    class Config:
        from_attributes = True
class ComboOfferResponse(ComboOfferBase):
    id: int
    items: Optional[List[ComboOfferItemResponse]] = None
    created_at: datetime
    updated_at:  datetime
    
    class Config:
        from_attributes = True
        
class PaginatedComboOfferResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[ComboOfferResponse]] = None   
    
class ComboOfferUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    discount_type: Optional[ComboDiscountType] = None
    discount_value: Optional[float] = None
    priority: Optional[int] = None
    stackable: Optional[bool] = None 
    
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def remove_timezone(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", ""))

        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)

        return v