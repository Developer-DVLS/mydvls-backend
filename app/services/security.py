import asyncio
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_email_verification_token(email: str):
    expire = datetime.now() + timedelta(hours=24)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def decode_access_token(token: str):
    try:
        return await asyncio.to_thread(jwt.decode, token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    
async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return await asyncio.to_thread(jwt.encode, to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_login_identifier(db_session: AsyncSession, *, login_identifier: str) -> User | None:
    query = select(User).where(
        User.email == login_identifier)
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()
    return user

async def authenticate_user(db_session: AsyncSession, login_identifier: str, password: str) -> User | None:
    # Introduce a small delay to mitigate user enumeration attacks
    await asyncio.sleep(0.1)

    user: User | None = await get_user_by_login_identifier(db_session, login_identifier=login_identifier)
    if not user:
        return None
    # if user is found check password
    if not verify_password(plain_password=password, hashed_password=user.password):
        return None
    return user

def get_refresh_token_from_cookie(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - token missing in cookie",
        )
    return token

async def verify_access_token(token: str, credentials_exception) -> int:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=settings.ALGORITHM)
        id = payload.get('email')
        if not id:
            raise credentials_exception

        token_data = id
    except JWTError:
        raise credentials_exception
    return token_data

def get_token_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - token missing in cookie",
        )
    return token

async def get_current_user(token: str = Depends(get_token_from_cookie), db_session: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

    email = await verify_access_token(token, credentials_exception=credentials_exception)

    query = select(User).where(User.email == email)
    result = await db_session.execute(query)
    user: User = result.scalar_one_or_none()

    return user

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        credentials_exception = HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})

        email = await verify_access_token(token, credentials_exception=credentials_exception)

        result = await db.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    except:
        return None