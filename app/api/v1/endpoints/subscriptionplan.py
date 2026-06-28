from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
import json

from app.api.v1.schemas.subscriptionplan import AddAddonRequest

SUBSCRIPTION_ADDON_SELECTION_COOKIE_KEY = "subscription_selection"

addon_router = APIRouter(
    prefix="/subscription-plan",
    tags=["User Subscription Plan Addons"]
)

@addon_router.post("/update-addon/")
async def update_addon(
    payload: AddAddonRequest,
    request: Request,
    response: Response
):
    if not payload.addon_ids:
        response.delete_cookie(
            key=SUBSCRIPTION_ADDON_SELECTION_COOKIE_KEY,
            samesite="none",
            secure=True,
        )

        return {
            "message": "Addon selection cleared"
        }
        
    data = {
        "service_id": payload.service_id,
        "plan_id": payload.plan_id,
        "addon_ids": payload.addon_ids
    }

    response.set_cookie(
        key=SUBSCRIPTION_ADDON_SELECTION_COOKIE_KEY,
        value=json.dumps(data),
        httponly=True,
        samesite="none",
        secure=True,
        max_age=3600,  # 1 hour
    )

    return data