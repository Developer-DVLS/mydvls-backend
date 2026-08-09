import secrets
import string

from fastapi import HTTPException

from app.services.smsservice import send_message
from app.utils.cache import delete_cache, get_cache, set_cache


class OTPService:
    
    # generate a 6 digit otp 
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        return ''.join(
            secrets.choice(string.digits)
            for _ in range(length)
        )

    # save otp in redis cache with 5mins expiration time 
    @staticmethod
    async def save_otp(
        phone: str,
        otp: str,
        expiry_seconds: int = 300
    ):
        await set_cache(
            f"otp:{phone}",
            otp,
            expiry_seconds
        )

    # verify otp and delete redis cache once verified
    @staticmethod
    async def verify_otp(
        phone: str,
        submitted_otp: str
    ) -> bool:

        stored_otp = await get_cache(f"otp:{phone}")
        
         # Redis may return bytes
        stored_otp = stored_otp.decode() if isinstance(stored_otp, bytes) else stored_otp

        if not stored_otp:
            raise HTTPException(
                status_code=400,
                detail="OTP expired or not found"
            )

        if stored_otp != submitted_otp:
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP"
            )

        # OTP can only be used once
        await delete_cache(f"otp:{phone}")

        return True

    # resend otp 
    @staticmethod
    async def resend_otp(phone: str):
        
        # delete OTP if exists
        await delete_cache(f"otp:{phone}")
        
        otp = OTPService.generate_otp()

        await OTPService.save_otp(
            phone,
            otp
        )

        # send SMS here
        message = (f"Your verification code is {otp}. "
                "It expires in 5 minutes. Do not share it with anyone.")
        await send_message(message, phone)

        return True