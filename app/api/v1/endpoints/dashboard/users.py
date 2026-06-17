from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.users import PaginatedUserResponse, UserResponse
from app.core.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.auth.permissions import admin_only
from app.utils.pagination import get_paginated_result

admin_user_router = APIRouter(prefix="/dashboard", tags=['Admin User CRUD'])

""" 
User crud api for admin dashboard.
"""

@admin_user_router.get("/users/", response_model=PaginatedUserResponse)
async def list_user(
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    ):
    query = select(User).order_by(User.created_at.desc())
    
    # search filter
    if search:
        query = query.where(
            or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                
            )
        )
    
    # role filter 
    if role:
        query = query.where(
            User.role == role
        )
    # status filter
    if status:
        query = query.where(
            User.status == status
        )

    return await get_paginated_result(db, query, skip, limit)
    

@admin_user_router.get("/user/{user_id}", response_model=UserResponse)
async def list_user(
    user_id: UUID,
    current_user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
    ):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return user