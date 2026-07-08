from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.orders import DeliveryStatus, OrderStatus

class OrderBase(BaseModel):
    # subtotal: float
    # tax_amount: float
    # discount_amount: float
    # delivery_charge: float
    # total: float
    currency: Optional[str] = None
    notes: Optional[str] = None
    receiver_first_name: str
    receiver_last_name: str
    receiver_email: str
    receiver_phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: float
    longitude: float
    
class OrderCreate(OrderBase):
    opaqueDataDescriptor: str
    opaqueDataValue: str

class OrderResponse(OrderBase):
    id: int
    user_id: UUID
    cart_id: Optional[int] = None
    order_number: str
    status: OrderStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    delivery_charge: float
    total: float
    delivery_status: DeliveryStatus
    payment_intent_id: Optional[str] = None
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
class PaginatedOrderResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[OrderResponse]] = None

    class Config:
        from_attributes = True
        
class OrderItemsResponse(BaseModel):
    id: int
    product_variant_id: int
    quantity: int
    unit_price: float
    total_price: float
    created_at: datetime
        
class OrderDetailResponse(OrderBase):
    id: int
    user_id: UUID
    cart_id: Optional[int] = None
    order_number: str
    status: OrderStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    delivery_charge: float
    total: float
    delivery_status: DeliveryStatus
    payment_intent_id: Optional[str] = None
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None
    items: List[OrderItemsResponse]
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        
class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderDeliveryStatusUpdate(BaseModel):
    delivery_status: DeliveryStatus