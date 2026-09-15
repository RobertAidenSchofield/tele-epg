import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.espn.client import ESPNEvent
from app.espn.enricher import enrich_programs
from app.parser import ProgramData

NY_TZ = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def _make_program(title, channel="PREMIER LEAGUE+ 01", hours_from_now=2):
    start = datetime.now(NY_TZ) + timedelta(hours=hours_from_now)
    return ProgramData(
        channel_name=channel,
        channel_id="premierleague01",
        title=title,
        start_time=start,
        stop_time=None,
    )


def _make_espn_event(name, hours_from_now=2):
    start = datetime.now(UTC) + timedelta(hours=hours_from_now)
    return ESPNEvent(
        espn_id="99999",
        name=name,
        short_name=name[:7],
        start_time=start,
        broadcast="USA Net",
        status="pre",
    )


def test_enrichment_replaces_time_on_match():
    prog = _make_program("Arsenal vs Chelsea", hours_from_now=3)
    espn_event = _make_espn_event("Arsenal at Chelsea", hours_from_now=2)

    with patch("app.espn.enricher.fetch_espn_events", return_value=[espn_event]):
        result = enrich_programs([prog])

    assert len(result) == 1
    # The enriched time should be the ESPN time (converted to NY), not the original
    expected_time = espn_event.start_time.astimezone(NY_TZ)
    assert result[0].start_time == expected_time


def test_enrichment_populates_desc_icon_and_sport():
    prog = _make_program("Arsenal vs Chelsea", hours_from_now=2)
    start = datetime.now(UTC) + timedelta(hours=2)
    espn_event = ESPNEvent(
        espn_id="111",
        name="Arsenal at Chelsea",
        short_name="ARS @ CHE",
        start_time=start,
        broadcast="NBC",
        status="pre",
        sport="soccer",
        league_name="English Premier League",
        venue="Stamford Bridge, London",
        summary_desc="Arsenal at Chelsea (English Premier League | Live from Stamford Bridge, London | Broadcast: NBC)",
        icon_url="https://a.espncdn.com/chelsea.png",
    )

    with patch("app.espn.enricher.fetch_espn_events", return_value=[espn_event]):
        result = enrich_programs([prog])

    assert len(result) == 1
    assert result[0].desc == espn_event.summary_desc
    assert result[0].icon_url == "https://a.espncdn.com/chelsea.png"
    assert result[0].sport == "soccer"


def test_unmatched_programs_keep_original_time():
    prog = _make_program("Some Random Event", channel="PPV")
    espn_event = _make_espn_event("Arsenal at Chelsea")

    with patch("app.espn.enricher.fetch_espn_events", return_value=[espn_event]):
        with patch("app.espn.enricher.detect_leagues", return_value={("soccer", "eng.1")}):
            result = enrich_programs([prog])

    assert len(result) == 1
    assert result[0].start_time == prog.start_time


def test_empty_espn_response_returns_unchanged():
    prog = _make_program("Arsenal vs Chelsea")

    with patch("app.espn.enricher.fetch_espn_events", return_value=[]):
        result = enrich_programs([prog])

    assert len(result) == 1
    assert result[0].start_time == prog.start_time


def test_no_leagues_detected_skips_enrichment():
    prog = _make_program("Unknown Event", channel="RANDOM CHANNEL")

    with patch("app.espn.enricher.detect_leagues", return_value=set()):
        result = enrich_programs([prog])

    assert len(result) == 1
    assert result[0].start_time == prog.start_time


def test_empty_programs_returns_empty():
    result = enrich_programs([])
    assert result == []
