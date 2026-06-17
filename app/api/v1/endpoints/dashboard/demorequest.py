from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import  or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.demorequest import DemoRequestResponse, DemoRequestUpdate, PaginatedDemoRequestResponse
from app.core.database import get_db
from app.models.demorequest import DemoRequest, DemoRequestStatus
from app.models.user import User
from app.auth.permissions import staff_only
from app.utils.pagination import get_paginated_result

admin_demo_request_router = APIRouter(prefix="/dashboard/demo-request", tags=["Admin DemoRequest"])

@admin_demo_request_router.get("/", response_model=PaginatedDemoRequestResponse)
async def list_demo_request(
    status: Optional[DemoRequestStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    query = select(DemoRequest).order_by(
                DemoRequest.created_at.desc()
                )  #later have to change ordering based on scheduled time
    
    if status:
        query = query.where(
            DemoRequest.status == DemoRequestStatus
            )
    
    if search:
        query = query.where(
            or_(
                DemoRequest.full_name.ilike(f"%{search}%"),
                DemoRequest.email == search,
                DemoRequest.phone.ilike(f"%{search}%"),
                
                DemoRequest.business_name.ilike(f"%{search}%"),
                DemoRequest.business_size == search,
                DemoRequest.business_type == search,
                DemoRequest.branch_count == search,
                DemoRequest.opening_type == search
            )
        )
    
    return await get_paginated_result(db, query, skip, limit)

@admin_demo_request_router.get("/{demo_request_id}/", response_model=DemoRequestResponse)
async def get_demo_request(
    demo_request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(DemoRequest)
        .where(DemoRequest.id == demo_request_id)
    )
    demo_request = result.scalars().first()
    if not demo_request:
        raise HTTPException(
            status_code= 404,
            detail= "Demo request not found."
        )
    
    return demo_request

@admin_demo_request_router.patch("/{demo_request_id}/")
async def update_demo_request(
    demo_request_id: UUID,
    data: DemoRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(DemoRequest)
        .where(DemoRequest.id == demo_request_id)
    )
    demo_request = result.scalars().first()
    if not demo_request:
        raise HTTPException(
            status_code= 404,
            detail= "Demo request not found."
        )
    
    # apply only provided fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(demo_request, field, value)
    
    await db.commit()
    await db.refresh(demo_request)
    
    return {
        "status": True,
        "message": "Demo request updated successfully."
    }
    
@admin_demo_request_router.delete("/{demo_request_id}/")
async def delete_demo_request(
    demo_request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    result = await db.execute(
        select(DemoRequest)
        .where(DemoRequest.id == demo_request_id)
    )
    demo_request = result.scalars().first()
    if not demo_request:
        raise HTTPException(
            status_code= 404,
            detail= "Demo request not found."
        )
    
    await db.delete(demo_request)
    await db.commit()

    return {
        "status": True,
        "message": "Offer deleted successfully"
    }