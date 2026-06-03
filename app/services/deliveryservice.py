from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery import DeliveryConfig


class DeliveryService:
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def validate_distance_range(
        self,
        min_distance: float,
        max_distance: float,
        exclude_id: int | None = None
    ):
        if min_distance >= max_distance:
            raise ValueError(
                "Minimum distance must be less than maximum distance."
            )

        query = select(DeliveryConfig).where(
            and_(
                DeliveryConfig.min_distance < max_distance,
                DeliveryConfig.max_distance > min_distance
            )
        )

        # For update operation
        if exclude_id:
            query = query.where(
                DeliveryConfig.id != exclude_id
            )

        existing = (await self.db.execute(query)).scalars().first()

        if existing:
            raise ValueError(
                f"Distance range overlaps with existing range "
                f"({existing.min_distance} - {existing.max_distance} km)"
            )