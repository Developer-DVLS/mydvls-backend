# schemas/address.py

from uuid import UUID
from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    address_line1: str = Field(..., max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(default="US", max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool | None = None


class AddressResponse(BaseModel):
    id: UUID
    user_id: UUID
    address_line1: str
    address_line2: str | None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: float | None
    longitude: float | None
    is_default: bool

    class Config:
        from_attributes = True
        
## for admin
class AdminAddressCreate(BaseModel):
    user_id: UUID

    address_line1: str = Field(..., max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(default="US", max_length=100)

    latitude: float | None = None
    longitude: float | None = None

    is_default: bool = False


class AdminAddressUpdate(BaseModel):
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    latitude: float | None = None
    longitude: float | None = None

    is_default: bool | None = None


class AdminAddressResponse(BaseModel):
    id: UUID
    user_id: UUID

    address_line1: str
    address_line2: str | None
    city: str
    state: str
    postal_code: str
    country: str

    latitude: float | None
    longitude: float | None

    is_default: bool

    model_config = {
        "from_attributes": True
    }