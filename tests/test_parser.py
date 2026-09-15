import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parser import PATTERNS, parse_line, ProgramData
from app.parser.time_utils import convert_utc_to_ny


def _pattern_with_group(group_name):
    for pattern in PATTERNS:
        if group_name in pattern["regex"].groupindex:
            return pattern["regex"]
    raise AssertionError(f"No parser regex contains group '{group_name}'")


def test_pattern_with_iso_matches_and_converts():
    pattern_with_iso = _pattern_with_group("iso")
    line = "US| ESPN+ 001 | GMA`s 50 States in 50 Weeks Jul 04 1:07AM ET (2026-07-04 01:07:01)"
    m = re.match(pattern_with_iso, line)
    assert m, "ISO parser pattern should match the sample line"
    assert m.group('channel').strip() == 'ESPN+ 001'
    assert m.group('title').strip().startswith("GMA`s 50 States")
    iso = m.group('iso')
    assert iso == '2026-07-04 01:07:01'

    # convert ISO (UTC) to NY
    dt_utc = datetime.strptime(iso, "%Y-%m-%d %H:%M:%S")
    local_dt = convert_utc_to_ny(dt_utc)
    # For 2026-07-04 01:07:01 UTC, Eastern should be previous day 21:07:01 with -0400 offset
    assert local_dt == datetime(2026, 7, 3, 21, 7, 1, tzinfo=local_dt.tzinfo)
    assert local_dt.strftime("%z") == "-0400"


def test_exact_start_stop_are_parsed_as_utc_and_converted():
    start = '2026-07-04 05:00:00'
    stop = '2026-07-04 06:00:00'
    dt_start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    local_start = convert_utc_to_ny(dt_start)
    # 05:00 UTC -> 01:00 or 00:00 depending on DST; primarily ensure conversion yields a naive datetime
    assert isinstance(local_start, datetime)
    # For July dates expect DST -0400
    assert local_start.strftime("%z") == "-0400"


def test_fallback_time_parsing_and_conversion():
    pattern_with_iso = _pattern_with_group("iso")
    # fallback line without parenthetical ISO, but with a time
    line = "US| ESPN+ 050 | Montreal Roses FC vs. Vancouver Rise FC Jul 04 3:25PM ET (2026-07-04 15:25:00)"
    m = re.match(pattern_with_iso, line)
    assert m
    iso = m.group('iso')
    dt_utc = datetime.strptime(iso, "%Y-%m-%d %H:%M:%S")
    local_dt = convert_utc_to_ny(dt_utc)
    # 15:25 UTC -> 11:25 EDT (UTC-4)
    assert local_dt == datetime(2026, 7, 4, 11, 25, 0, tzinfo=local_dt.tzinfo)


def test_uk_et_schedule_line_returns_program_data():
    line = (
        "UK| PREMIER LEAGUE+ 01 | Aston Villa vs Arsenal "
        "// UK Mon 31 Aug 8:00pm // ET Mon 31 Aug 3:00pm"
    )

    result = parse_line(line, 2026)

    assert result is not None
    assert isinstance(result, ProgramData)
    assert result.channel_id == "premierleague01"
    assert result.title == "Aston Villa vs Arsenal"
    assert result.start_time.strftime("%Y-%m-%d %H:%M %z") == (
        "2026-08-31 15:00 -0400"
    )
    assert result.start_time.tzinfo is not None
    assert result.stop_time is None


def test_reference_dt_anchors_kickoff_time():
    from zoneinfo import ZoneInfo
    line = "PPV| UFC 300 | Main Card, kick-off 10pm ET"
    # Suppose message was sent on 2026-05-10 at 14:00 NY time
    ref_dt = datetime(2026, 5, 10, 14, 0, 0, tzinfo=ZoneInfo("America/New_York"))

    result = parse_line(line, ref_dt)
    assert result is not None
    assert result.start_time.year == 2026
    assert result.start_time.month == 5
    assert result.start_time.day == 10
    assert result.start_time.hour == 22  # 10pm ET
    assert result.start_time.minute == 0


def test_reference_dt_anchors_simple_time_utc():
    from zoneinfo import ZoneInfo
    # Without ET marker, time is assumed UTC and converted to NY (-4 hours during EDT)
    line = "PPV| BOXING : Canelo vs Crawford 9:00pm"
    ref_dt = datetime(2026, 9, 20, 11, 0, 0, tzinfo=ZoneInfo("America/New_York"))

    result = parse_line(line, ref_dt)
    assert result is not None
    assert result.start_time.year == 2026
    assert result.start_time.month == 9
    assert result.start_time.day == 20
    # 21:00 UTC -> 17:00 EDT
    assert result.start_time.hour == 17


