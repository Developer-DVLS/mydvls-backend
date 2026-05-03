from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from typing import Any, Dict, List, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T") # Used for typing the SQLAlchemy model

async def get_paginated_result(
    db: AsyncSession,
    query: Select,
    skip: int,
    limit: int
) -> Dict[str, Any]:
    """
    Utility function to apply pagination and return a dictionary 
    containing both data and metadata (total count).
    """
    # 1. Count query (derived from the base query's from_statement or selection)
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0
    
    # 2. Apply limit and offset to data query
    paginated_query = query.offset(skip).limit(limit)
    result = await db.execute(paginated_query)
    data = result.scalars().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "data": list(data)
    }