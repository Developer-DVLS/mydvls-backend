from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import List

from pytz import timezone

load_dotenv()


class Settings(BaseSettings):
    APP_TIMEZONE: str = "America/Denver"
    
    APP_NAME: str = os.getenv("APP_NAME")
    ENV: str = os.getenv("ENV")
    DEBUG: str = os.getenv("DEBUG")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM:  str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL")
    BASE_URL: str = os.getenv("BASE_URL")
    
    DATABASE_URL: str = 'os.getenv("DATABASE_URL")'
    
    # sendgrid mail 
    MAIL_USERNAME: str = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD: str = os.getenv('MAIL_PASSWORD', '')
    MAIL_FROM: str = os.getenv('MAIL_FROM', '')
    MAIL_PORT: int = os.getenv('MAIL_PORT', '')
    MAIL_SERVER: str = os.getenv('MAIL_SERVER', '')
    MAIL_TLS: bool = os.getenv('MAIL_TLS', '')
    MAIL_SSL: bool = os.getenv('MAIL_SSL', '')
    MAIL_DEBUG: int = os.getenv('MAIL_DEBUG', '')
    MAIL_FROM_NAME : str = os.getenv('MAIL_FROM_NAME', '')
    
    REFRESH_TOKEN_EXPIRE_DAYS: int = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30)
    
    # azure blob container
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
    AZURE_CONTAINER_NAME: str = os.getenv('AZURE_CONTAINER_NAME', '')
    AZURE_ACCOUNT_KEY: str = os.getenv('AZURE_ACCOUNT_KEY', '')
    
    #redis
    REDIS_URL: str = os.getenv('REDIS_URL', '')
    
    #sms server
    MESSAGE_SERVER: str = os.getenv('MESSAGE_SERVER', '')
    
    
    # authorize.net keys
    API_LOGIN_ID: str = os.getenv('API_LOGIN_ID', '')
    TRANSACTION_KEY: str = os.getenv('TRANSACTION_KEY', '')
    ENDPOINT_URL: str = os.getenv('ENDPOINT_URL', '')
    AUTHORIZE_SIGNATURE_KEY: str = os.getenv('AUTHORIZE_SIGNATURE_KEY', '')
    
    ##teams alert 
    TEAMS_ALERT_URL: str = os.getenv('TEAMS_ALERT_URL', '')
    TEAMS_ALERT_SECRET: str = os.getenv('TEAMS_ALERT_SECRET', '')
    
    ## google recaptcha
    RECAPTCHA_VERIFY_URL: str = os.getenv('RECAPTCHA_VERIFY_URL', '')
    RECAPTCHA_SECRET_KEY: str = os.getenv('RECAPTCHA_SECRET_KEY', '')
    
    @property
    def tz(self):
        """Return pytz timezone object"""
        return timezone(self.APP_TIMEZONE)

    class Config:
        env_file = ".env"

settings = Settings()