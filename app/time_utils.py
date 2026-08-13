from zoneinfo import ZoneInfo


def convert_utc_to_ny(naive_dt):
    """Treat naive_dt as UTC, convert to America/New_York, return naive local dt and offset string."""
    try:
        utc_tz = ZoneInfo("UTC")
        ny_tz = ZoneInfo("America/New_York")
        aware_dt = naive_dt.replace(tzinfo=utc_tz).astimezone(ny_tz)
        return aware_dt.replace(tzinfo=None), aware_dt.strftime(" %z")
    except (ValueError, TypeError):
        return naive_dt, " +0000"


def convert_et_to_ny(naive_dt):
    """Treat naive_dt as America/New_York, return naive local dt and offset string."""
    ny_tz = ZoneInfo("America/New_York")
    aware_dt = ny_tz.localize(naive_dt)
    return aware_dt.replace(tzinfo=None), aware_dt.strftime(" %z")