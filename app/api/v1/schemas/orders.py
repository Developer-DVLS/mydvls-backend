from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_serializer

from app.core.config import settings
from app.models.orders import DeliveryStatus, OrderStatus


APP_TIMEZONE = ZoneInfo(settings.APP_TIMEZONE)

class OrderBillingAddressBase(BaseModel):
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country:Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class OrderShippingAddressBase(BaseModel):
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country:Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
class OrderBase(BaseModel):
    billing_address_id: Optional[UUID] = None
    shipping_address_id: Optional[UUID] = None
    billing_address: Optional[OrderBillingAddressBase] = None
    shipping_address: Optional[OrderShippingAddressBase] = None
    
    receiver_first_name: str
    receiver_last_name: str
    receiver_email: str
    receiver_phone: str
    
    shipping_full_name: Optional[str] = None
    shipping_company: Optional[str] = None
    shipping_phone: Optional[str] = None
    
    currency: Optional[str] = None
    notes: Optional[str] = None
    
class OrderCreate(OrderBase):
    opaqueDataDescriptor: str
    opaqueDataValue: str

class OrderResponse(BaseModel):
    id: int
    user_id: UUID
    cart_id: Optional[int] = None
    billing_address_id: Optional[UUID] = None
    shipping_address_id: Optional[UUID] = None
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
    
    shipping_full_name: Optional[str] = None
    shipping_company: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_address_line_1: Optional[str] = None
    shipping_address_line_2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_latitude: Optional[float] = None
    shipping_longitude: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        
    @field_serializer(
        "created_at",
        "updated_at",
        "confirmed_at",
        "completed_at",
        "cancelled_at"
        )
    def serialize_created_at(self, value: datetime) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(APP_TIMEZONE).isoformat()
    
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
    billing_address_id: Optional[UUID] = None
    shipping_address_id: Optional[UUID] = None
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
    
    shipping_full_name: Optional[str] = None
    shipping_company: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_address_line_1: Optional[str] = None
    shipping_address_line_2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_latitude: Optional[float] = None
    shipping_longitude: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        
    @field_serializer(
        "created_at",
        "updated_at",
        "confirmed_at",
        "completed_at",
        "cancelled_at"
        )
    def serialize_created_at(self, value: datetime) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(APP_TIMEZONE).isoformat()
        
class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderDeliveryStatusUpdate(BaseModel):
    delivery_status: DeliveryStatus