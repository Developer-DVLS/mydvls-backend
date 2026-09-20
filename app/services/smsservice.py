import requests
from app.core.config import settings
import httpx

import logging

logger = logging.getLogger(__name__)

async def send_message(message, phone_number, schedule=False):
    """
    This function sends message request to the message server
    """
    message_server = settings.MESSAGE_SERVER

    payload = {
        "message": message,
        "message_to": phone_number,
        "message_from_service": 1,
        "schedule":schedule
        }
    
    headers = {
        'Content-Type': 'application/json',
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            message_server,
            json=payload,
            headers=headers,
        )

    if response.status_code == 200:
        print('Request was successful!')
    else:
        logger.exception("Failed to send refund SMS:", {response.status_code})
    return 