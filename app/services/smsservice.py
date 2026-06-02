import requests
from app.core.config import settings


def send_message(message, phone_number, schedule=False):
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

    response = requests.post(message_server, json=payload, headers=headers)

    if response.status_code == 200:
        print('Request was successful!')
    else:
        print(f'Failed with status code: {response.status_code}')
    return 