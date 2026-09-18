import re
from app.parser.handlers import (
    _handle_exact_utc,
    _handle_iso_utc,
    _handle_month_day_time_et,
    _handle_kickoff_time,
    _handle_nfl_time,
    _handle_us_channel_time,
    _handle_simple_time,
    _handle_time_only_et
)

PATTERNS = [
    {
        "regex": re.compile(
            r"^(?P<prefix>US)\|\s*"
            r"(?P<channel>NFL LIVE \d{2})\s*:\s*"
            r"(?:(?P<label>TNF|SNF|MNF)\s+)?"
            r"(?P<time>\d{1,2}(?::\d{2})?(?:am|pm))\s+"
            r"(?P<title>.+?)\s*$",
            re.IGNORECASE
        ),
        "handler": _handle_nfl_time
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>US)\|\s*"
            r"(?P<channel>[^|:]+?)\s*:\s*"
            r"(?:(?P<label>[A-Za-z][A-Za-z0-9+&-]*)\s+)?"
            r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm))\s+"
            r"(?P<title>.+?)\s*$",
            re.IGNORECASE
        ),
        "handler": _handle_us_channel_time
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>UK)\|\s*"
            r"(?P<channel>[^|]+?)\s*\|\s*"
            r"(?P<title>.*?)\s*//\s*"
            r"UK\s+\w{3}\s+\d{1,2}\s+\w{3}\s+"
            r"\d{1,2}:\d{2}(?:am|pm)\s*//\s*"
            r"ET\s+\w{3}\s+"
            r"(?P<day>\d{1,2})\s+"
            r"(?P<month>\w{3})\s+"
            r"(?P<time>\d{1,2}:\d{2}[ap]m)\s*$",
            re.IGNORECASE
        ),
        "handler": _handle_month_day_time_et
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>PPV|UK|US|AU|CA)\|\s*(?P<channel>[^|:-]+?)\s*(?:\||:|-)\s*"
            r"(?P<title>.*?)\s+start:(?P<start>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
            r"stop:(?P<stop>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)"
        ),
        "handler": _handle_exact_utc
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>US|UK|AU|CA|PPV)\|\s*(?P<channel>[^|]+?)\s*\|\s*(?P<title>.*?)\s*\((?P<iso>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)\)"
        ),
        "handler": _handle_iso_utc
    },
    {
        "regex": re.compile(
            r"^(?P<prefix>PPV)\|\s*"
            r"(?P<channel>.+?\s+\[[^\]]+\]\s+\d{1,3})\s+\["
            r"(?P<title>.+?)\s+"
            r"\((?P<iso>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)\)\]$"
        ),
        "handler": _handle_iso_utc
    },
    {
        "regex": re.compile(
            r"^(?P<channel>[^:]+?):\s*(?:\d{4}\s*)?(?P<title>.+?)\s*\(.+?\)\s*"
            r"\((?P<iso>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)\)"
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
