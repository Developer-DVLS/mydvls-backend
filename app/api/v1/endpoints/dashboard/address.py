# routers/admin/address.py

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.schemas.address import (
    AdminAddressCreate,
    AdminAddressUpdate,
    AdminAddressResponse,
)
from app.services.admin_address_service import (
    AdminAddressService,
)
from app.auth.permissions import staff_only


admin_address_router = APIRouter(
    prefix="/dashboard/addresses",
    tags=["Admin - Addresses"],
)

@admin_address_router.post(
    "/",
    response_model=AdminAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_address(
    data: AdminAddressCreate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    service = AdminAddressService(db)

    return await service.create_address(data)

@admin_address_router.get(
    "/",
    response_model=list[AdminAddressResponse],
)
async def list_addresses(
    user_id: UUID | None = None,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    service = AdminAddressService(db)

    return await service.get_addresses(
        user_id=user_id
    )
    
@admin_address_router.get(
    "/{address_id}",
    response_model=AdminAddressResponse,
)
async def get_address(
    address_id: UUID,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    service = AdminAddressService(db)

    return await service.get_address(
        address_id
    )
    
@admin_address_router.put(
    "/{address_id}",
    response_model=AdminAddressResponse,
)
async def update_address(
    address_id: UUID,
    data: AdminAddressUpdate,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    service = AdminAddressService(db)

    return await service.update_address(
        address_id=address_id,
        data=data,
    )
    
@admin_address_router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_address(
    address_id: UUID,
    current_admin: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db),
):
    service = AdminAddressService(db)

    await service.delete_address(
        address_id
    )

    return None