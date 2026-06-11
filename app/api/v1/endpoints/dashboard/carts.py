from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.admincart import PaginatedCartResponse
from app.models.carts import Cart, CartStatus
from app.models.user import User
from app.utils.pagination import get_paginated_result
from app.auth.permissions import staff_only
from app.core.database import get_db

admin_cart_router = APIRouter(prefix="/dashboard/cart", tags=['Admin Cart'])

@admin_cart_router.get("/", response_model=PaginatedCartResponse)
async def list_carts(
    user_id: Optional[UUID] = None,
    status: Optional[CartStatus] = None,
    created_at: Optional[datetime] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(staff_only)
):
    query = select(Cart).order_by(Cart.created_at.desc())
    
    if user_id:
        query = query.where(Cart.user_id == user_id)
    if status:
        query = query.where(Cart.status == status)
    if created_at:
        query = query.where(func.date(Cart.created_at) == created_at.date())
    
    return await get_paginated_result(db, query, skip, limit)