from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.visits import VisitCreate
from app.core.database import get_db
from app.models.visits import Visit


visit_routers = APIRouter(prefix="/user-visits", tags=["User visits"])

@visit_routers.post("/")
async def create_visit(
        data: VisitCreate,
        db:  AsyncSession = Depends(get_db)
    ):
        visit = Visit(
            source=data.source,
            medium=data.medium,
            campaign=data.campaign,
        )

        db.add(visit)
        await db.commit()
        await db.refresh(visit)

        return {
            "message": "Visit tracked successfully.",
            "id": visit.id,
        }
    
