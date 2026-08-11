# services/admin_address_service.py

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address
from app.models.user import User
from app.api.v1.schemas.address import (
    AdminAddressCreate,
    AdminAddressUpdate,
)


class AdminAddressService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_address(
        self,
        data: AdminAddressCreate,
    ) -> Address:

        # Make sure user exists
        user = await self.db.scalar(
            select(User).where(
                User.id == data.user_id
            )
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Handle default address
        if data.is_default:
            await self._remove_existing_default(
                user_id=data.user_id
            )

        address = Address(
            user_id=data.user_id,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
            latitude=data.latitude,
            longitude=data.longitude,
            is_default=data.is_default,
        )

        self.db.add(address)

        await self.db.commit()
        await self.db.refresh(address)

        return address

    async def get_addresses(
        self,
        user_id: UUID | None = None,
    ) -> list[Address]:

        query = select(Address)

        if user_id:
            query = query.where(
                Address.user_id == user_id
            )

        query = query.order_by(
            Address.created_at.desc()
        )

        result = await self.db.execute(query)

        return list(result.scalars().all())

    async def get_address(
        self,
        address_id: UUID,
    ) -> Address:

        address = await self.db.scalar(
            select(Address).where(
                Address.id == address_id
            )
        )

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found",
            )

        return address

    async def update_address(
        self,
        address_id: UUID,
        data: AdminAddressUpdate,
    ) -> Address:

        address = await self.get_address(
            address_id
        )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if update_data.get("is_default") is True:
            await self._remove_existing_default(
                user_id=address.user_id,
                exclude_address_id=address.id,
            )

        for field, value in update_data.items():
            setattr(address, field, value)

        await self.db.commit()
        await self.db.refresh(address)

        return address

    async def delete_address(
        self,
        address_id: UUID,
    ) -> None:

        address = await self.get_address(
            address_id
        )

        await self.db.delete(address)

        await self.db.commit()

    async def _remove_existing_default(
        self,
        user_id: UUID,
        exclude_address_id: UUID | None = None,
    ):

        query = select(Address).where(
            Address.user_id == user_id,
            Address.is_default.is_(True),
        )

        if exclude_address_id:
            query = query.where(
                Address.id != exclude_address_id
            )

        result = await self.db.execute(query)

        addresses = result.scalars().all()

        for address in addresses:
            address.is_default = False