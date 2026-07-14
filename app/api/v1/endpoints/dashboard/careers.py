from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.careers import CareerResponse, CreateCareer, PaginatedCareerResponse, UpdateCareerStatus
from app.core.database import get_db
from app.models.careers import Career
from app.models.user import User
from app.auth.permissions import staff_only
from app.services.recaptchaservice import RecaptchaService
from app.utils.pagination import get_paginated_result

career_router = APIRouter(prefix="/career", tags=['Career'])
admin_career_router = APIRouter(prefix="/dashboard/career", tags=['Admin Career CRUD'])

@career_router.post("/")
# @limiter.limit("3/hour; 5/day")
async def create_career(
    request: Request,
    data: CreateCareer,
    db: AsyncSession = Depends(get_db)
):
    await RecaptchaService.verify(
        token=data.recaptcha_token,
        action="career"
    )
    
    career = Career(
        full_name = data.full_name, 
        email = data.email.lower(), 
        phone = data.phone, 
        address = data.address, 
        type = data.type or None,
        position = data.position or None,
        cover_letter  = data.cover_letter or None, 
        resume = data.resume,
        linkedin_url = data.linkedin_url or None, 
        portfolio_url = data.portfolio_url or None, 
        qna = data.qna
    )
    db.add(career)
    await db.commit()
    
    return {
        "status": True,
        "message": "Submitted successfully."
    }

@admin_career_router.get("/", response_model=PaginatedCareerResponse)
async def list_career(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    query = select(Career).order_by(Career.created_at.desc())
    return await get_paginated_result(db, query, skip, limit)

@admin_career_router.get("/{career_id}/", response_model=CareerResponse)
async def get_career(
    career_id: int,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Career)
        .where(Career.id == career_id)
    )
    career = result.scalars().first()
    if not career:
        raise HTTPException(
            status_code= 404,
            detail="Career info not found."
        )
    return career

@admin_career_router.patch("/{career_id}/", response_model=CareerResponse)
async def update_career(
    career_id: int,
    data: UpdateCareerStatus,
    current_user: User = Depends(staff_only),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Career)
        .where(Career.id == career_id)
    )
    career = result.scalars().first()
    if not career:
        raise HTTPException(
            status_code= 404,
            detail="Career info not found."
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(career, field, value)

    await db.commit()
    await db.refresh(career)
    
    return career