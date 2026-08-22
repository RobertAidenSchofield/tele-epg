import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from time_utils import convert_utc_to_ny, convert_et_to_ny

logger = logging.getLogger(__name__)
ET_MARKER = re.compile(r"\bET\b", re.IGNORECASE)

# --- Parsing Handlers ---

def _line_has_et(match) -> bool:
    """Check if the matched line contains an 'ET' marker."""
    return bool(ET_MARKER.search(match.string or ""))

def _handle_exact_utc(match, current_year):
    start_dt = datetime.strptime(match.group('start'), "%Y-%m-%d %H:%M:%S")
    stop_dt = datetime.strptime(match.group('stop'), "%Y-%m-%d %H:%M:%S")

    if _line_has_et(match):
        start_time, offset = convert_et_to_ny(start_dt)
        stop_time, _ = convert_et_to_ny(stop_dt)
    else:
        start_time, offset = convert_utc_to_ny(start_dt)
        stop_time, _ = convert_utc_to_ny(stop_dt)

    return {'start_time': start_time, 'stop_time': stop_time, 'offset': offset}


def _handle_iso_utc(match, current_year):
    dt = datetime.strptime(match.group('iso'), "%Y-%m-%d %H:%M:%S")

    if _line_has_et(match):
        start_time, offset = convert_et_to_ny(dt)
    else:
        start_time, offset = convert_utc_to_ny(dt)

    return {'start_time': start_time, 'stop_time': None, 'offset': offset}

def _handle_month_day_time_et(match, current_year):
    """Handler for formats with 'Month Day Time ET' (e.g., Jul 04 5:00PM ET)."""
    date_str = f"{match.group('month')} {match.group('day')} {current_year} {match.group('time')}"
    start_dt_et = datetime.strptime(date_str, "%b %d %Y %I:%M%p")
    start_time, offset = convert_et_to_ny(start_dt_et)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}

def _handle_kickoff_time(match, current_year):
    """Handler for PPV formats with 'kick-off 8pm'."""
    time_text = match.group('kickoff').strip().lower().replace(' ', '')
    time_format = "%I:%M%p" if ':' in time_text else "%I%p"
    kickoff_time_obj = datetime.strptime(time_text, time_format).time()

    now_ny = datetime.now(ZoneInfo("America/New_York"))
    start_dt_et = now_ny.replace(year=current_year, month=now_ny.month, day=now_ny.day,
                                hour=kickoff_time_obj.hour, minute=kickoff_time_obj.minute,
                                second=0, microsecond=0)

    if start_dt_et < now_ny:
        start_dt_et += timedelta(days=1)

    start_time, offset = convert_et_to_ny(start_dt_et)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}

def _handle_simple_time(match, current_year):
    """Handler for simple formats with just a time (e.g., '8:30pm')."""
    time_text = match.group('time').strip().lower().replace(' ', '')
    time_format = "%I:%M%p" if ':' in time_text else "%I%p"
    time_obj = datetime.strptime(time_text, time_format).time()

    now_ny = datetime.now(ZoneInfo("America/New_York"))
    start_dt_et = now_ny.replace(year=current_year, month=now_ny.month, day=now_ny.day,
                                hour=time_obj.hour, minute=time_obj.minute,
                                second=0, microsecond=0)

    if start_dt_et < now_ny:
        start_dt_et += timedelta(days=1)

    start_time, offset = convert_et_to_ny(start_dt_et)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}

def _handle_time_only_et(match, current_year):
    """Handler for formats with only a time (e.g., '17:15') in ET, inferring date."""
    time_text = match.group('time').strip()
    time_obj = None
    for fmt in ("%H:%M", "%I:%M%p", "%I%p"):
        try:
            time_obj = datetime.strptime(time_text, fmt).time()
            break
        except ValueError:
            continue

    if time_obj is None:
        logger.warning(f"Could not parse time: {time_text}")
        return None

    now_ny = datetime.now(ZoneInfo("America/New_York"))
    start_dt_ny = now_ny.replace(year=current_year, month=now_ny.month, day=now_ny.day,
                                hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)

    if start_dt_ny < now_ny:
        start_dt_ny += timedelta(days=1)

    start_time, offset = convert_et_to_ny(start_dt_ny)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}


PATTERNS = [
    {
        "regex": re.compile(
            r"^(?P<prefix>PPV|UK|US|AU)\|\s*(?P<channel>[^|:-]+?)\s*(?:\||:|-)\s*"
            r"(?P<title>.*?)\s+start:(?P<start>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+"
            r"stop:(?P<stop>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})"
        ),
        "handler": _handle_exact_utc
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>US|UK|AU|CA|PPV)\|\s*(?P<channel>[^|]+?)\s*\|\s*(?P<title>.*?)\s*\((?P<iso>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\)"
        ),
        "handler": _handle_iso_utc
    },
    {
        "regex": re.compile(
            r"^(?P<channel>[^:]+?):\s*(?:\d{4}\s*)?(?P<title>.+?)\s*\(.+?\)\s*"
            r"\((?P<iso>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\)"
        ),
        "handler": _handle_iso_utc
    },
    {
        "regex": re.compile(
            r"^(?P<channel>ESPN\+ \d{3})\s*:\s*(?P<title>.*?)\s+"
            r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{1,2}:\d{2}[ap]m)\s+ET",
            re.IGNORECASE
        ),
        "handler": _handle_month_day_time_et
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>PPV)\|\s*(?P<channel>[^|]+?)\|\s*(?P<time>\d{1,2}:\d{2}(?:[ap]m)?)\s*(?P<title>.*)"
        ),
        "handler": _handle_time_only_et
    },
    {
        "regex": re.compile(
            r"^PPV\|\s*(?P<channel>[^|:-]+?)\s*(?:\||:|-)\s*(?P<title>.*?)\s*,\s*kick-off\s*(?P<kickoff>\d{1,2}(?::\d{2})?\s*[ap]m)",
            re.IGNORECASE
        ),
        "handler": _handle_kickoff_time
    },
    {
        "regex": re.compile(
            r"^PPV\|\s*(?P<channel>[^:]+?)\s*:\s*(?P<title>.*?)\s+(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))\s*$",
            re.IGNORECASE
        ),
        "handler": _handle_simple_time
    },
]

def parse_line(line, current_year):
    """Parse a single line using the configured patterns and handlers."""
    line = line.strip()
    if not line:
        return None

    for p in PATTERNS:
        match = p['regex'].match(line)
        if match:
            try:
                groups = match.groupdict()
                channel_name = groups.get('channel', '').strip()
                title = groups.get('title', '').strip()
                channel_id = re.sub(r'[^a-z0-9]', '', channel_name.lower())

                time_data = p['handler'](match, current_year)
                if time_data is None:
                    continue

                return {
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'title': title,
                    **time_data
                }
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse line with handler '{p['handler'].__name__}': {line} | Error: {e}")
                continue
    return None