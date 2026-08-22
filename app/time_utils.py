import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

NY_TZ = ZoneInfo("America/New_York")


def convert_utc_to_ny(utc_dt: datetime) -> tuple[datetime, str]:
    """
    Converts a naive UTC datetime to a naive NY datetime and returns the offset.
    """
    try:
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))

        ny_dt = utc_dt.astimezone(NY_TZ)
        offset_str = ny_dt.strftime('%z')

        return ny_dt.replace(tzinfo=None), f" {offset_str}"
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting UTC to NY time: {utc_dt} | {e}")
        return utc_dt, " +0000"


def convert_et_to_ny(et_dt: datetime) -> tuple[datetime, str]:
    """
    Converts a datetime object (assumed to be in ET) to a naive NY datetime
    and returns the offset string. Handles both naive and aware inputs.
    """
    # If naive, assume it's in NY time and make it aware using .replace()
    aware_dt = et_dt.replace(tzinfo=NY_TZ) if et_dt.tzinfo is None else et_dt.astimezone(NY_TZ)

    offset_str = aware_dt.strftime('%z')
    return aware_dt.replace(tzinfo=None), f" {offset_str}"