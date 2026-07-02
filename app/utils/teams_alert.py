import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter()


async def team_alert(
    title,
    monitor,
    monitor_url
):
    url = settings.TEAMS_ALERT_URL
    secret = settings.TEAMS_ALERT_SECRET

    payload={
            "title": title,
            "monitor": monitor,
            # "cause": cause,
            # "length": "",
            # "checked_url": f"Threshold count: {threshold}",
            # "response": f"Current count: {order_count}",
            # "incident_url": monitor_url,
            "monitor_url": monitor_url,
            # "incident_key": "",
        }
        
    headers = {
        "Content-Type": "application/json",
        "x-alert-secret": secret
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers
            )
            
        response.raise_for_status()

        return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to external API: {str(e)}"
        )
