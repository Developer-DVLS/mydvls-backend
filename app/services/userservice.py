from typing import Optional
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.security import hash_password

class UserService:
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_guest_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        ):
        # check if guest-email exists else create guest user 
        existing_guest_user_result = await self.db.execute(
            select(User)
            .where(func.lower(User.email) == email.lower())
        )
        guest_user = existing_guest_user_result.scalars().first()
        
        if not guest_user:
            guest_user = User(
                first_name = first_name,
                last_name = last_name or None,
                user_name = f"{first_name or None} + {last_name or None}",
                email = email.lower(),
                phone = phone,
                role = UserRole.GUEST_CUSTOMER,
                password = hash_password("PASSWORD")
            )
            self.db.add(guest_user)
            await self.db.commit()
            await self.db.refresh(guest_user)
            
        return guest_user