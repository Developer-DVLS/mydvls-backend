from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.models.user import UserRole, UserStatus

class UserRegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    recaptcha_token: str
    # role: UserRole
    # bio: str
    # password: Optional[str] = None
    # confirm_password: str

class UserVerified(BaseModel):
    message: str


class UserLoginResponseSchema(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    access_token: str
    refresh_token: str

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    user_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    status: UserStatus
    bio: Optional[str] = None
    is_email_verified: bool
    is_phone_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PaginatedUserResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: Optional[List[UserResponse]] = None  

class ForgotPassword(BaseModel):
    email: EmailStr
        
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    bio: Optional[str] = None
    

class UserLogin(BaseModel):
    email: str
    password: str

class ResetPasswordConfirmation(BaseModel):
    code: str
    new_password: str
    confirm_password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    new_password_again: str
    
    
class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str

class ResendOTPRequest(BaseModel):
    phone: str
    recaptcha_token: str
    
class LoginRequest(BaseModel):
    phone: str