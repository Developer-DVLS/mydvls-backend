# app/services/recaptcha.py

import httpx
from fastapi import HTTPException
from app.core.config import settings


class RecaptchaService:

    VERIFY_URL =settings.RECAPTCHA_VERIFY_URL

    @classmethod
    async def verify(cls, token: str, action: str):
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                cls.VERIFY_URL,
                data={
                    "secret": settings.RECAPTCHA_SECRET_KEY,
                    "response": token,
                },
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail="Captcha verification failed."
            )

        if data.get("action") != action:
            raise HTTPException(
                status_code=400,
                detail="Invalid captcha action."
            )

        score = data.get("score", 0)

        if score < 0.5:
            raise HTTPException(
                status_code=400,
                detail="Suspicious activity detected."
            )

        return data