from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from pydantic import BaseModel, EmailStr

from app.core.config import settings

env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

class MailSettings(BaseModel):
    MAIL_USERNAME: str = settings.MAIL_USERNAME
    MAIL_PASSWORD: str = settings.MAIL_PASSWORD
    MAIL_FROM: EmailStr = settings.MAIL_FROM
    MAIL_PORT: int = settings.MAIL_PORT
    MAIL_SERVER: str = settings.MAIL_SERVER
    MAIL_TLS: bool = settings.MAIL_TLS
    MAIL_SSL: bool = settings.MAIL_SSL
    MAIL_DEBUG: int = settings.MAIL_DEBUG # Set to 1 for debugging


mail_settings = MailSettings()

conf = ConnectionConfig(
    MAIL_USERNAME=mail_settings.MAIL_USERNAME,
    MAIL_PASSWORD=mail_settings.MAIL_PASSWORD,
    MAIL_FROM=mail_settings.MAIL_FROM,
    MAIL_PORT=587,  # Use 465 for SSL
    MAIL_SERVER=mail_settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,  # Correct key for STARTTLS
    MAIL_SSL_TLS=False,  # Correct key for SSL
    USE_CREDENTIALS=True
)


async def send_email(background_tasks: BackgroundTasks, subject: str, recipients: list, template_name: str, context: dict):
    """
        Send an email with a rendered HTML template.
    """

    template = env.get_template(template_name)

    body = template.render(context)

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype="html"
    )

    fm = FastMail(conf)
    if background_tasks:
        background_tasks.add_task(fm.send_message, message)
    else:
        await fm.send_message(message=message)

