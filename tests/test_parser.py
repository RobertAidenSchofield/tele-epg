import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.parser import PATTERNS, parse_line, parse_message, ProgramData
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


def test_nfl_live_lines_are_parsed_as_eastern_time():
    lines = [
        "US| NFL LIVE 01: TNF 8:15pm Lions at Bills",
        "US| NFL LIVE 02: 1pm Panthers at Falcons",
        "US| NFL LIVE 03: 1pm Vikings at Bears",
        "US| NFL LIVE 04: 1pm Eagles at Titans",
        "US| NFL LIVE 05: 1pm Steelers at Patriots",
        "US| NFL LIVE 06: 1pm Packers at Jets",
        "US| NFL LIVE 07: 1pm Browns at Buccaneers",
        "US| NFL LIVE 08: 1pm Saints at Ravens",
        "US| NFL LIVE 09: 1pm Bengals at Texans",
        "US| NFL LIVE 10: 4:05pm Jaguars at Broncos",
        "US| NFL LIVE 11: 4:05pm Raiders at Chargers",
        "US| NFL LIVE 12: 4:25pm Commanders at Cowboys",
        "US| NFL LIVE 13: 4:25pm Seahawks at Cardinals",
        "US| NFL LIVE 14: 4:25pm Dolphins at 49ers",
        "US| NFL LIVE 15: SNF 8:20pm Colts at Chiefs",
        "US| NFL LIVE 16: MNF 8:15pm Giants at Rams",
    ]

    results = parse_message("\n".join(lines), datetime(2026, 9, 20, 10, 0))

    assert len(results) == len(lines)
    assert results[0].channel_id == "nfllive01"
    assert results[0].title == "Lions at Bills"
    assert results[0].start_time.strftime("%Y-%m-%d %H:%M %z") == "2026-09-20 20:15 -0400"
    assert results[9].start_time.hour == 16
    assert results[14].title == "Colts at Chiefs"
    assert results[15].start_time.hour == 20


def test_unparsed_message_lines_are_reported(caplog):
    with caplog.at_level("WARNING", logger="app.parser"):
        results = parse_message("US| UNKNOWN FORMAT", 2026)

    assert results == []
    assert "Unparsed EPG line: US| UNKNOWN FORMAT" in caplog.text


def test_generic_us_channel_time_line_is_parsed():
    line = "US| BASKETBALL LIVE 01: 7:30pm Lakers at Celtics"

    result = parse_line(line, datetime(2026, 9, 20, 10, 0))

    assert result is not None
    assert result.channel_name == "BASKETBALL LIVE 01"
    assert result.title == "Lakers at Celtics"
    assert result.start_time.strftime("%Y-%m-%d %H:%M %z") == "2026-09-20 19:30 -0400"


def test_bracketed_ppv_iso_lines_are_parsed():
    lines = [
        "PPV| UFC [BG] 02 [CRYPTO.COM UFC 331: OFFICIAL WEIGH_IN SHOW (2026-09-18 11:50:00)]",
        "PPV| UFC INT [BG] 02 [CRYPTO.COM UFC 331: OFFICIAL WEIGH_IN SHOW (2026-09-18 11:50:00)]",
        "PPV| UFC [BG] 03 [UFC 333: PRESS CONFERENCE (2026-09-18 20:00:00)]",
        "PPV| UFC INT [BG] 03 [UFC 333: PRESS CONFERENCE (2026-09-18 20:00:00)]",
        "PPV| UFC [BG] 04 [CRYPTO.COM UFC 331: CEREMONIAL WEIGH_IN (2026-09-18 21:00:00)]",
        "PPV| UFC INT [BG] 04 [CRYPTO.COM UFC 331: CEREMONIAL WEIGH_IN (2026-09-18 21:00:00)]",
    ]

    results = parse_message("\n".join(lines), 2026)

    assert len(results) == len(lines)
    assert results[0].channel_name == "UFC [BG] 02"
    assert results[0].title == "CRYPTO.COM UFC 331: OFFICIAL WEIGH_IN SHOW"
    assert results[0].start_time.strftime("%Y-%m-%d %H:%M %z") == (
        "2026-09-18 07:50 -0400"
    )
    assert results[2].title == "UFC 333: PRESS CONFERENCE"
    assert results[5].channel_id == "ufcintbg04"


def test_start_stop_event_lines_parse_for_uk_and_setanta():
    lines = [
        "PPV| SETANTA EVENT 01 : EuroLeague Supercup 2026, Olympiacos - Fenerbahce start:2026-09-18 14:55:09 stop:2026-09-18 19:00:09",
        "UK| TNT SPORTS EVENT 01 : Guyana Amazon Warriors - Jamaica Kingsmen start:2026-09-18 23:30:00 stop:2026-09-19 03:45:00",
    ]

    results = parse_message("\n".join(lines), 2026)

    assert len(results) == 2
    assert results[0].channel_id == "setantaevent01"
    assert results[1].channel_id == "tntsportsevent01"
    assert results[0].stop_time > results[0].start_time
    assert results[1].stop_time > results[1].start_time


def test_flexible_iso_and_channel_variants_are_parsed():
    lines = [
        "CA| SPORTS 01 | Event (2026-09-18T20:00Z)",
        "PPV| UFC [BG] 2 [Event (2026-09-18 20:00)]",
        "CA| SPORTS 02 : Event start:2026-09-18T20:00 stop:2026-09-18T22:00",
    ]

    results = parse_message("\n".join(lines), 2026)

    assert len(results) == 3
    assert results[0].channel_id == "sports01"
    assert results[1].channel_id == "ufcbg2"
    assert results[2].stop_time > results[2].start_time


