
from datetime import datetime, timedelta
from enum import Enum
from calendar import monthrange

class DateFilter(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    LAST_7_DAYS = "last_7_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_30_DAYS = "last_30_days"
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    
    CUSTOM = "custom"
        
class ReportService:
    def get_date_range(
        self,
        filter_type: DateFilter,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        print("filtertype!!!!", filter_type)
        now = datetime.utcnow()

        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if filter_type == DateFilter.TODAY:
            return today, today + timedelta(days=1)
        
        # Daily (Year-to-date)
        if filter_type == DateFilter.DAILY:
            return datetime(today.year, 1, 1), now

        if filter_type == DateFilter.YESTERDAY:
            start = today - timedelta(days=1)
            return start, today
        
        # Weekly (12 complete weekly buckets)
        if filter_type == DateFilter.WEEKLY:
            current_week_start = today - timedelta(days=today.weekday())
            start = current_week_start - timedelta(weeks=11)
            end = current_week_start + timedelta(days=7)
            return start, end

        if filter_type == DateFilter.THIS_WEEK:
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=7)

        if filter_type == DateFilter.LAST_WEEK:
            end = today - timedelta(days=today.weekday())
            start = end - timedelta(days=7)
            return start, end

        if filter_type == DateFilter.LAST_7_DAYS:
            return today - timedelta(days=6), now

        if filter_type == DateFilter.THIS_MONTH:
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
            return start, end

        if filter_type == DateFilter.LAST_MONTH:
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

            start = datetime(year, month, 1)
            end = datetime(
                year,
                month,
                monthrange(year, month)[1],
                23,
                59,
                59,
                999999,
            )

            return start, end

        if filter_type == DateFilter.LAST_30_DAYS:
            return today - timedelta(days=29), now

        if filter_type == DateFilter.LAST_3_MONTHS:
            return today - timedelta(days=90), now

        if filter_type == DateFilter.LAST_6_MONTHS:
            return today - timedelta(days=180), now

        if filter_type == DateFilter.THIS_YEAR:
            start = datetime(today.year, 1, 1)
            end = datetime(today.year + 1, 1, 1)
            return start, end

        if filter_type == DateFilter.LAST_YEAR:
            return (
                datetime(today.year - 1, 1, 1),
                datetime(today.year, 1, 1),
            )
        
        # Monthly (Year-to-date)
        if filter_type == DateFilter.MONTHLY:
            return datetime(today.year, 1, 1), now

        if filter_type == DateFilter.CUSTOM:
            return start_date, end_date

        return None, None