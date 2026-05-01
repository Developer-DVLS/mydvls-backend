from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal

from app.models.user import User, UserRole,  UserStatus
from app.services.security import hash_password

"""
Create super user on runtime.
"""
async def create_superuser():
    async with AsyncSessionLocal() as db:
        
        result = await db.execute(
            select(User).where(User.is_superuser == True)
        )
        admin = result.scalar_one_or_none()

        if admin:
            print("Superuser already exists")
            return
        
        hp = hash_password("password")
        user = User(
            first_name="super", 
            last_name="user",
            user_name="super_user",
            email="admin@yopmail.com",   #change in prod
            password=hp, #change in prod
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_superuser=True,
            is_email_verified=True,
            is_phone_verified=True
        )

        db.add(user)
        await db.commit()