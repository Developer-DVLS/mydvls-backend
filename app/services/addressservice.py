# services/address_service.py

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address
from app.api.v1.schemas.address import AddressCreate, AddressUpdate


class AddressService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_address(
        self,
        user_id: UUID,
        data: AddressCreate,
    ) -> Address:

        # If this is the first/default address,
        # remove default from existing addresses.
        if data.is_default:
            await self._remove_existing_default(user_id)

        address = Address(
            user_id=user_id,
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
        user_id: UUID,
    ) -> list[Address]:

        result = await self.db.execute(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(
                Address.is_default.desc(),
                Address.created_at.desc(),
            )
        )

        return list(result.scalars().all())

    async def get_address(
        self,
        user_id: UUID,
        address_id: UUID,
    ) -> Address:

        result = await self.db.execute(
            select(Address).where(
                Address.id == address_id,
                Address.user_id == user_id,
            )
        )

        address = result.scalar_one_or_none()

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found",
            )

        return address

    async def update_address(
        self,
        user_id: UUID,
        address_id: UUID,
        data: AddressUpdate,
    ) -> Address:

        address = await self.get_address(
            user_id,
            address_id,
        )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if update_data.get("is_default") is True:
            await self._remove_existing_default(
                user_id,
                exclude_address_id=address.id,
            )

        for field, value in update_data.items():
            setattr(address, field, value)

        await self.db.commit()
        await self.db.refresh(address)

        return address

    async def delete_address(
        self,
        user_id: UUID,
        address_id: UUID,
    ) -> None:

        address = await self.get_address(
            user_id,
            address_id,
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