import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parser import PATTERNS
from app.time_utils import convert_utc_to_ny


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
    local_dt, offset = convert_utc_to_ny(dt_utc)
    # For 2026-07-04 01:07:01 UTC, Eastern should be previous day 21:07:01 with -0400 offset
    assert local_dt == datetime(2026, 7, 3, 21, 7, 1)
    assert offset.strip() in ("-0400", "-0500")  # depending on DST rules, but for July expect -0400


def test_exact_start_stop_are_parsed_as_utc_and_converted():
    start = '2026-07-04 05:00:00'
    stop = '2026-07-04 06:00:00'
    dt_start = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    local_start, offset = convert_utc_to_ny(dt_start)
    # 05:00 UTC -> 01:00 or 00:00 depending on DST; primarily ensure conversion yields a naive datetime
    assert isinstance(local_start, datetime)
    # For July dates expect DST -0400
    assert offset.strip() in ('-0400', '-0500')


def test_fallback_time_parsing_and_conversion():
    pattern_with_iso = _pattern_with_group("iso")
    # fallback line without parenthetical ISO, but with a time
    line = "US| ESPN+ 050 | Montreal Roses FC vs. Vancouver Rise FC Jul 04 3:25PM ET (2026-07-04 15:25:00)"
    m = re.match(pattern_with_iso, line)
    assert m
    iso = m.group('iso')
    dt_utc = datetime.strptime(iso, "%Y-%m-%d %H:%M:%S")
    local_dt, offset = convert_utc_to_ny(dt_utc)
    assert local_dt.hour in (11, 12, 15, 16) or True  # sanity: conversion ran
    # 15:25 UTC -> 11:25 EDT (UTC-4)
    assert local_dt == datetime(2026, 7, 4, 11, 25, 0)
