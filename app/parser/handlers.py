import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.parser.time_utils import convert_utc_to_ny, convert_et_to_ny

logger = logging.getLogger(__name__)
ET_MARKER = re.compile(r"\bET\b", re.IGNORECASE)

def _line_has_et(match) -> bool:
    """Check if the matched line contains an 'ET' marker."""
    return bool(ET_MARKER.search(match.string or ""))

def _convert_to_ny(dt, match):
    if _line_has_et(match):
        return convert_et_to_ny(dt)

    return convert_utc_to_ny(dt)


def _time_result(start_dt, match, stop_dt=None):
    result = {
        "start_time": _convert_to_ny(start_dt, match),
        "stop_time": None,
    }

    if stop_dt is not None:
        result["stop_time"] = _convert_to_ny(stop_dt, match)

    return result


def _parse_datetime(value):
    value = value.strip().replace(" ", "T", 1)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)

def _get_ref_dt(ref, source_tz):
    if isinstance(ref, datetime):
        return ref.astimezone(source_tz)
    year = ref if isinstance(ref, int) else datetime.now(source_tz).year
    now = datetime.now(source_tz)
    return now.replace(year=year)


def _handle_exact_utc(match, ref):
    start_dt = _parse_datetime(match.group("start"))
    stop_dt = _parse_datetime(match.group("stop"))

    return _time_result(start_dt, match, stop_dt)


def _handle_iso_utc(match, ref):
    dt = _parse_datetime(match.group("iso"))

    return _time_result(dt, match)

def _handle_month_day_time_et(match, ref):
    year = ref.year if isinstance(ref, datetime) else ref
    date_str = (
        f"{match.group('month')} "
        f"{match.group('day')} "
        f"{year} "
        f"{match.group('time')}"
    )

    start_dt = datetime.strptime(
        date_str,
        "%b %d %Y %I:%M%p"
    )

    return _time_result(start_dt, match)

def _handle_kickoff_time(match, ref):
    """Handler for PPV formats with 'kick-off 8pm'."""
    time_text = match.group("kickoff").strip().lower().replace(" ", "")
    time_format = "%I:%M%p" if ":" in time_text else "%I%p"
    kickoff_time = datetime.strptime(time_text, time_format).time()

    start_dt = _infer_start_datetime(
        kickoff_time,
        ref,
        match,
    )
    return _time_result(start_dt, match)

def _infer_start_datetime(time_obj, ref, match, source_tz=None):
    if source_tz is None:
        source_tz = (
            ZoneInfo("America/New_York")
            if _line_has_et(match)
            else ZoneInfo("UTC")
        )

    ref_dt = _get_ref_dt(ref, source_tz)

    start_dt = ref_dt.replace(
        hour=time_obj.hour,
        minute=time_obj.minute,
        second=0,
        microsecond=0,
    )

    if start_dt < ref_dt:
        start_dt += timedelta(days=1)

    return start_dt

def _handle_simple_time(match, ref):
    time_text = match.group("time").strip().lower().replace(" ", "")
    time_format = "%I:%M%p" if ":" in time_text else "%I%p"
    time_obj = datetime.strptime(time_text, time_format).time()

    start_dt = _infer_start_datetime(time_obj, ref, match)
    return _time_result(start_dt, match)

def _handle_nfl_time(match, ref):
    return _handle_us_channel_time(match, ref)

def _handle_us_channel_time(match, ref):
    time_text = match.group("time").strip().lower().replace(" ", "")
    time_format = "%I:%M%p" if ":" in time_text else "%I%p"
    time_obj = datetime.strptime(time_text, time_format).time()
    start_dt = _infer_start_datetime(
        time_obj,
        ref,
        match,
        ZoneInfo("America/New_York"),
    )
    return {
        "start_time": convert_et_to_ny(start_dt),
        "stop_time": None,
    }

def _handle_time_only_et(match, ref):
    """Handler for formats containing only a time."""
    time_text = match.group("time").strip()
    time_obj = None

    for time_format in ("%H:%M", "%I:%M%p", "%I%p"):
        try:
            time_obj = datetime.strptime(time_text, time_format).time()
            break
        except ValueError:
            continue

    if time_obj is None:
        logger.warning("Could not parse time: %s", time_text)
        return None

    start_dt = _infer_start_datetime(
        time_obj,
        ref,
        match,
    )
    return _time_result(start_dt, match)
