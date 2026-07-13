from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.contacts import ContactCreate, ContactResponse, PaginatedContactResponse
from app.core.database import get_db
from app.models.contacts import Contact
from app.utils.pagination import get_paginated_result
from app.utils.limiter import limiter

contact_router = APIRouter(prefix="/contact", tags=['Contact'])

@contact_router.post("/")
# @limiter.limit("1/minute; 5/day")
async def create_contact(
    request: Request,
    data: ContactCreate,
    db: AsyncSession = Depends(get_db)
):
    contact = Contact(
        first_name = data.first_name, 
        last_name = data.last_name or None,
        email = data.email.lower() or None, 
        phone = data.phone, 
        message = data.message or None
    )
    db.add(contact)
    await db.commit()
    
    return {
        "status": True,
        "message": "Submitted successfully."
    }

@contact_router.get("/", response_model=PaginatedContactResponse)
async def list_contact(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    query = select(Contact).order_by(Contact.created_at.desc())
    
    return await get_paginated_result(db, query, skip, limit)

@contact_router.get("/{contact_id}/", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
         select(Contact)
         .where(Contact.id == contact_id)
        )
    contact = result.scalars().first()
    
    if not contact:
        raise HTTPException(
            status_code= 404,
            detail="Contact not found."
        )
    return contact


# @contact_router.delete("/{contact_id}/")
# async def delete_contact(
#     contact_id: int,
#     db: AsyncSession = Depends(get_db)
# ):
#     result = await db.execute(
#          select(Contact)
#          .where(Contact.id == contact_id)
#         )
#     contact = result.scalars().first()
#     if not contact:
#         raise HTTPException(
#             status_code= 404,
#             detail="Contact not found."
#         )
    
#     await db.delete(contact)
#     await db.commit()
    
#     return  {
#         "status": True,
#         "message": "Contact deleted successfully."
#     }
