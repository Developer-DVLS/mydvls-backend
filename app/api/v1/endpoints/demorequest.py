from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.schemas.demorequest import UserDemoRequestCreate
from app.models.demorequest import DemoRequest
from app.models.user import User
from app.services.security import get_current_user_optional
from app.core.database import get_db

demo_request_router = APIRouter(prefix="/demo-request", tags=["User DemoRequest"])

@demo_request_router.post("/")
async def create_demo_request(
    data: UserDemoRequestCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):

    demo_request = DemoRequest(
        user_id = current_user.id if current_user else None,
        full_name = f"{data.first_name} {data.last_name}".strip(),
        email = data.email,
        phone = data.phone,
        business_name = data.business_name or None,
        business_size = data.business_size or None,
        business_type = data.business_type or None,
        branch_count = data.branch_count,
        opening_type = data.opening_type, 
        preferred_date = data.preferred_date or None,
        timezone = data.timezone or None,
        message = data.message or None
    )
    db.add(demo_request)
    await db.commit()
    await db.refresh(demo_request)
    
    return {
        "status": True,
        "message": "Demo request submitted successfully."
    }
    