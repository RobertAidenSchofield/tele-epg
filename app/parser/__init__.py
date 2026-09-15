import re
import logging
from dataclasses import dataclass
from datetime import datetime

from app.parser.patterns import PATTERNS

logger = logging.getLogger(__name__)

@dataclass
class ProgramData:
    channel_name: str
    channel_id: str
    title: str
    start_time: datetime
    stop_time: datetime | None
    desc: str | None = None
    icon_url: str | None = None
    sport: str | None = None

def parse_line(line: str, reference_dt: datetime | int | None = None) -> ProgramData | None:
    """Parse a single line using the configured patterns and handlers."""
    line = line.strip()
    if not line:
        return None

    ref = reference_dt if reference_dt is not None else datetime.now().year

    for p in PATTERNS:
        match = p['regex'].match(line)
        if match:
            try:
                groups = match.groupdict()
                channel_name = groups.get('channel', '').strip()
                title = groups.get('title', '').strip()
                channel_id = re.sub(r'[^a-z0-9]', '', channel_name.lower())

                time_data = p['handler'](match, ref)
                if time_data is None:
                    continue

                return ProgramData(
                    channel_name=channel_name,
                    channel_id=channel_id,
                    title=title,
                    start_time=time_data['start_time'],
                    stop_time=time_data.get('stop_time')
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse line with handler '{p['handler'].__name__}': {line} | Error: {e}")
                continue
    return None

def parse_message(text: str, reference_dt: datetime | int | None = None) -> list[ProgramData]:
    """Parse a multi-line message into a list of ProgramData objects."""
    results = []
    for line in text.splitlines():
        parsed = parse_line(line, reference_dt)
        if parsed:
            results.append(parsed)
    return results

__all__ = ["ProgramData", "parse_line", "parse_message", "PATTERNS"]
