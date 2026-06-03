from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax import TaxConfig

class TaxService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def tax_code_exists(
        self,
        code: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        normalized_code = code.strip().lower()

        query = select(TaxConfig).where(
            func.lower(func.trim(TaxConfig.code)) == normalized_code
        )
        
        if exclude_id:
            query = query.where(TaxConfig.id != exclude_id)

        result = await self.db.scalar(query)
        return result is not None