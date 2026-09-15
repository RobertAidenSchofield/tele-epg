import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

NY_TZ = ZoneInfo("America/New_York")
UTC_TZ = ZoneInfo("UTC")


def convert_utc_to_ny(utc_dt: datetime) -> datetime:
    """Return a timezone-aware New York datetime."""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC_TZ)

    return utc_dt.astimezone(NY_TZ)


def convert_et_to_ny(et_dt: datetime) -> datetime:
    """Treat the input as Eastern Time and return an aware datetime."""
    if et_dt.tzinfo is None:
        et_dt = et_dt.replace(tzinfo=NY_TZ)

    return et_dt.astimezone(NY_TZ)
