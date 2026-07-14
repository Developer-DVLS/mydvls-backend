from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.schemas.demorequest import UserDemoRequestCreate
from app.models.demorequest import DemoRequest
from app.models.user import User
from app.services.recaptchaservice import RecaptchaService
from app.services.security import get_current_user_optional
from app.core.database import get_db
from app.utils.teams_alert import team_alert
from app.utils.limiter import limiter

demo_request_router = APIRouter(prefix="/demo-request", tags=["User DemoRequest"])

@demo_request_router.post("/")
# @limiter.limit("3/hour; 5/day")
async def create_demo_request(
    request: Request,
    data: UserDemoRequestCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    await RecaptchaService.verify(
        token=data.recaptcha_token,
        action="demorequest"
    )
    
    demo_request = DemoRequest(
        user_id = current_user.id if current_user else None,
        full_name = f"{data.first_name} {data.last_name}".strip(),
        email = data.email.lower(),
        phone = data.phone,
        business_name = data.business_name.lower() or None if "business_name" in data else None,
        business_size = data.business_size or None if "business_size" in data else None,
        business_type = data.business_type.lower() or None,
        branch_count = data.branch_count,
        opening_type = data.opening_type.lower(), 
        preferred_date = data.preferred_date or None if "preferred_date" in data else None,
        timezone = data.timezone or None if "preferred_date" in data else None,
        message = data.message or None if "message" in data else None
    )
    db.add(demo_request)
    await db.commit()
    await db.refresh(demo_request)
    
    # send team alert
    await team_alert(
        title="DEMO REQUEST ALERT -MYDVLS",
        monitor="Demo request application in Mydvls. Review it ASAP.",
        monitor_url="https://mydvls.chowchownow.com/"
    )
    
    return {
        "status": True,
        "message": "Demo request submitted successfully."
    }
    