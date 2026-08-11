# routers/address.py

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.schemas.address import (
    AddressCreate,
    AddressUpdate,
    AddressResponse,
)
from app.services.addressservice import AddressService
from app.services.security import get_current_user


user_address_router = APIRouter(
    prefix="/addresses",
    tags=["User Addresses"],
)


@user_address_router.post(
    "/user-address/",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AddressService(db)

    return await service.create_address(
        user_id=current_user.id,
        data=data,
    )


@user_address_router.get(
    "/user-address/",
    response_model=list[AddressResponse],
)
async def list_user_addresses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AddressService(db)

    return await service.get_addresses(
        user_id=current_user.id,
    )


@user_address_router.get(
    "/user-address/{address_id}/",
    response_model=AddressResponse,
)
async def get_user_address(
    address_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AddressService(db)

    return await service.get_address(
        user_id=current_user.id,
        address_id=address_id,
    )


@user_address_router.put(
    "/user-address/{address_id}/",
    response_model=AddressResponse,
)
async def update_user_address(
    address_id: UUID,
    data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AddressService(db)

    return await service.update_address(
        user_id=current_user.id,
        address_id=address_id,
        data=data,
    )


@user_address_router.delete(
    "/user-address/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user_address(
    address_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AddressService(db)

    await service.delete_address(
        user_id=current_user.id,
        address_id=address_id,
    )

    return None