from typing import Any, Dict, Optional

from pydantic import BaseModel

class OrderCreate(BaseModel):
    subtotal: float
    tax_amount: float
    discount_amount: float
    delivery_charge: float
    total: float
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



