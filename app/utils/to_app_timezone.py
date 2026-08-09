from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

APP_TIMEZONE = ZoneInfo(settings.APP_TIMEZONE)


def to_app_timezone(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None

    # DB value is UTC but stored without timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(APP_TIMEZONE)