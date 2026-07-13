from fastapi import APIRouter,  Depends, HTTPException, BackgroundTasks, Response, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.users import ChangePassword, ForgotPassword, LoginRequest, ResendOTPRequest, ResetPasswordConfirmation, UserLoginResponseSchema, UserRegisterRequest, UserResponse, UserVerified, VerifyOTPRequest
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.services.otpservice import OTPService
from app.services.security import authenticate_user, create_access_token, create_email_verification_token, create_refresh_token, decode_access_token, get_current_user, get_refresh_token_from_cookie, hash_password, verify_password
from app.services.smsservice import send_message
from app.utils.cache import get_cache
from app.utils.send_email import send_email
from app.services.cartservice import CartService
from app.utils.validators import is_valid_phone
from app.utils.limiter import limiter

user_router = APIRouter(prefix="/users", tags=['User auth'])

@user_router.post("/register/", response_model=UserResponse)
async def user_register(background_tasks: BackgroundTasks, data:UserRegisterRequest , db:  AsyncSession = Depends(get_db)):
    """ 
    User registration: Creates new user.
    
    Params:
    background_task: BackgroundTask
    data: User registration data
    db: Database session
    
    Returns new user.
    """
    try:
        # Check if email already exists
        existing_user = await db.execute(
        select(User).filter(User.email == data.email.lower())
        )
        existing_user = existing_user.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="Email already registered"
                )
        
        # Check if phone number already exists
        #check if phone number validity
        if not is_valid_phone(data.phone):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number"
            )
            
        existing_user = await db.execute(
        select(User).filter(User.phone == data.phone)
        )
        existing_user = existing_user.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="User with this phone already registered"
                )
            
        # hash password
        password_hash = hash_password("PASSWORD")
        
        #create user
        new_user = User(
            first_name=data.first_name, 
            last_name=data.last_name,
            user_name=data.first_name + "_" + data.last_name,
            email=func.lower(data.email),   #lowercase the email before adding in db
            phone=data.phone,
            password=password_hash,
            role=UserRole.CUSTOMER,
            is_email_verified=False,
            is_phone_verified=False
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # otp verification
        #generate otp
        otp = OTPService.generate_otp()
        
        #send sms 
        message = (f"Your verification code is {otp}. "
                "It expires in 5 minutes. Do not share it with anyone.")
        send_message(message, new_user.phone)
        
        #save otp
        await OTPService.save_otp(new_user.phone, otp)
        
        return new_user
    except HTTPException as e:
        raise 
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )
        
@user_router.post("/auth/verify-otp/")
async def verify_otp(
    request: Request,
    response: Response,
    data: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    # verify phone
    if not is_valid_phone(data.phone):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number"
            )
            
    # verify otp 
    await OTPService.verify_otp(data.phone, data.otp) 

    # 4. Check if user exists
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid phone number.")
    
    user.is_phone_verified = True
    await db.commit()

    # 6. Generate tokens
     # create token based on login identifier instead of static username/email
    access_token: str = await create_access_token({'email': user.email})
    refresh_token: str = await create_refresh_token({'email': user.email})
    
    response.set_cookie(key="access_token", value=access_token,
                        httponly=False, samesite="none", secure=True, max_age=86400, )
    response.set_cookie(key="refresh_token", value=refresh_token,
                        httponly=False, samesite="none", secure=True, max_age=86400, )
    
     # sync session cart
    cart_service = CartService()
    await cart_service.cart_sync_on_login(request, response, db, user.id)

    return {
        "message": "OTP verified successfully.",
        "access_token": access_token,
        "user_id": user.id
    }

@user_router.post("/resend-otp/")
# @limiter.limit("3/hour; 10/day")
async def resend_otp(
    request: Request,
    data:ResendOTPRequest
):
    # verify phone
    if not is_valid_phone(data.phone):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number"
            )
    
    response = await OTPService.resend_otp(data.phone)
    if response:
        return {
            "message": "OTP sent."
        }
    raise HTTPException(status_code=400, detail="Unexpected error occurred.")

@user_router.post("/auth/login/send-otp")
async def send_login_otp(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    # verify phone
    if not is_valid_phone(data.phone):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number"
            )
    
    result = await db.execute(
        select(User).where(User.phone == data.phone)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found. Please register first."
        )

     # otp verification
    #generate otp
    otp = OTPService.generate_otp()
    
    #send sms 
    message = (f"Your verification code is {otp}. "
            "It expires in 5 minutes. Do not share it with anyone.")
    send_message(message, user.phone)
    
    #save otp
    await OTPService.save_otp(user.phone, otp)

    return {"message": "OTP sent"}
    
        
# @user_router.post("/verify-email/", response_model=UserVerified)
# async def verify_email(token: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
#     """ 
#     Email verification link. Verifies email and change active status for login.
    
#     params:
#     token: email verification token [from frontend]
#     background_task: BaackgroundTask
#     db: databse session
    
#     returns:
#     Verification msg.
#     """
#     payload = await decode_access_token(token)
#     if not payload:
#         raise HTTPException(status_code=400, detail="Invalid or expired token")

#     user = await db.execute(select(User).filter(User.email == payload["sub"]))
#     user = user.scalars().first()

#     user.is_email_verified = True
#     user.status = UserStatus.ACTIVE
#     await db.commit()
#     await db.refresh(user)

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     # await send_email(background_tasks=background_tasks,
#     #                  subject="Email Verified",
#     #                  recipients=[settings.ADMIN_EMAIL],
#     #                  template_name='auth/user_approval.html',
#     #                  context={'user': user.name,
#     #                           'user_email': user.email,
#     #                           'update_link': f'{settings.FRONTEND_URL}'       
#     #                  }
#     #                  )

#     return {"message": "Email verified successfully"}


# @user_router.post("/login/")
# async def login(
#         response: Response,
#         request: Request,
#         form_data: OAuth2PasswordRequestForm = Depends(),
#         db_session: AsyncSession = Depends(get_db)
# ):
    
#     """ 
#     User login. 
#     User enter login credentials. Tokens are set in cookie and can access the platform through it.
    
#     params:
#     form_data: user login credentials
#     db_session
    
#     return:
#     User info with tokens.
#     """
    
#     login_identifier, password = form_data.username.lower(), form_data.password
#     user: User | None = await authenticate_user(
#         db_session=db_session, login_identifier=login_identifier, password=password
#     )

    
#     if not user:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail="Incorrect email or password")
    
#     # if not (user.is_email_verified and user.is_active):
#     #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email/Account not verified")
    

#     # create token based on login identifier instead of static username/email
#     access_token: str = await create_access_token({'email': login_identifier})
#     refresh_token: str = await create_refresh_token({'email': login_identifier})

#     user.access_token = access_token
#     user.refresh_token = refresh_token

#     response.set_cookie(key="access_token", value=access_token,
#                         httponly=False, samesite="none", secure=True, max_age=86400, )
#     response.set_cookie(key="refresh_token", value=refresh_token,
#                         httponly=False, samesite="none", secure=True, max_age=86400, )
    
#     # sync session cart
#     cart_service = CartService()
#     await cart_service.cart_sync_on_login(request, response, db_session, user.id)

#     login_response = UserLoginResponseSchema.model_validate(user)

#     return login_response

@user_router.post("/admin-login/")
async def admin_login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db_session: AsyncSession = Depends(get_db)):
    
    """ 
    Admin/ Staff login. 
    User enter login credentials. Tokens are set in cookie and can access the platform through it.
    
    params:
    form_data: user login credentials
    db_session
    
    return:
    User info with tokens.
    """
    
    login_identifier, password = form_data.username.lower(), form_data.password
    user: User | None = await authenticate_user(
        db_session=db_session, login_identifier=login_identifier, password=password
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Incorrect email or password")
    
    if not (user.is_email_verified and user.is_active):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email/Account not verified")
    
    if user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized user.")

    # create token based on login identifier instead of static username/email
    access_token: str = await create_access_token({'email': login_identifier})
    refresh_token: str = await create_refresh_token({'email': login_identifier})

    user.access_token = access_token
    user.refresh_token = refresh_token

    response.set_cookie(key="access_token", value=access_token,
                        httponly=False, samesite="none", secure=True, max_age=86400, )
    response.set_cookie(key="refresh_token", value=refresh_token,
                        httponly=False, samesite="none", secure=True, max_age=86400, )

    login_response = UserLoginResponseSchema.model_validate(user)
    return login_response

@user_router.get("/me/", response_model=UserResponse)
async def get_loggedin_user(user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """ 
    Get user info of logged in user.
    """
    user = await db.execute(select(User).where(User.id == user.id))
    user = user.scalars().first()
    return UserResponse.model_validate(user)

@user_router.post("/refresh-token/")
async def refresh_token( response: Response,
                        refresh_token: str = Depends(get_refresh_token_from_cookie), 
                        db: AsyncSession = Depends(get_db),
                       
                        ):
    """ 
    Gets refresh token from cookie and sets new access token in cookie. Also returns the token.
    """
    try:
        # Decode the refresh token (synchronous decoding, ensure error handling)
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[
                             settings.ALGORITHM], options={"verify_exp": True})
        user_email = payload.get("email")

        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Query the user from the database
        result = await db.execute(select(User).filter(User.email == user_email))
        db_user = result.scalars().first()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create a new access token asynchronously
        new_access_token = await create_access_token({"email": db_user.email})

        response.set_cookie(key="access_token", value=new_access_token,
                        httponly=False, samesite="none", secure=True, max_age=86400, )

        return {"access_token": new_access_token, "token_type": "bearer"}
    except JWTError as e :
        # Handle invalid JWT error
        raise HTTPException(status_code=401, detail=e)
    except Exception as e:
        # Catch any other exceptions (e.g., DB or other unforeseen issues)
        raise HTTPException(status_code=500, detail=str(e))
    

@user_router.post("/forgot-password/", response_model=UserVerified)
async def forgot_password( user: ForgotPassword, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """ 
    Sends password change email to the email.
    
    params:
    user: User email

    """
    db_user = await db.execute(
        select(User).filter(User.email == user.email)
    )
    db_user = db_user.scalars().first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Invalid Email.")
    
    verification_token = create_email_verification_token(email=user.email)
    await send_email(background_tasks=background_tasks,
                     subject="Forgot Password Link",
                     recipients=[user.email],
                     template_name='auth/forgot_password.html',
                     context={'user': db_user.name,
                              'verification_code': verification_token,
                              'verification_link': f'{settings.FRONTEND_URL}/reset_password/{verification_token}'}
                     )
    return {"message": "Password reset link sent successfully to your email"}


@user_router.post("/reset-password/", response_model=UserVerified)
async def reset_password(password: ResetPasswordConfirmation, db: AsyncSession = Depends(get_db)):
    """ 
    Helps to reset password.
    
    params:
    password: takes in old password, new password, and a reset code
    
    returns msg.
    """
    if password.new_password != password.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    payload = await decode_access_token(password.code)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await db.execute(select(User).filter(User.email == payload["sub"]))
    user = user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(password.new_password)
    await db.commit()
    return {"message": "Password reset successfully"}


@user_router.post("/change-password/")
async def change_password(
    response: Response,
    data: ChangePassword, 
    db: AsyncSession = Depends(get_db), 
    user: str = Depends(get_current_user),
    ):
    """ 
    Changes user password.
    
    params:
    data: takes in old password, new password, and confirm new password
    user: returns logged in user
    """
    if not user or not verify_password(data.old_password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    if not(data.new_password == data.new_password_again):
        raise HTTPException(status_code=400, detail="Password don't match.")

    user.password = hash_password(data.new_password)
    await db.commit()
    
    ##logout after change in password
    response.delete_cookie(key="access_token",  httponly=False, samesite="none", secure=True)
    response.delete_cookie(key="refresh_token",  httponly=False, samesite="none", secure=True)
    
    return {"message": "Password changed successfully"}


@user_router.get('/logout/')
async def logout(response: Response):
    response.delete_cookie(key="access_token",  httponly=False, samesite="none", secure=True)
    response.delete_cookie(key="refresh_token",  httponly=False, samesite="none", secure=True)
    return {"message": "Successfully logged out"}