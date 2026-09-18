import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.espn.client import ESPNEvent, fetch_espn_events
from app.espn.matcher import find_best_match, _normalize
from app.parser import ProgramData

NY_TZ = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def _make_program(title, channel="TEST CHANNEL", hours_from_now=2):
    start = datetime.now(NY_TZ) + timedelta(hours=hours_from_now)
    return ProgramData(
        channel_name=channel,
        channel_id="testchannel",
        title=title,
        start_time=start,
        stop_time=None,
    )


def _make_espn_event(name, short_name="", hours_from_now=2):
    start = datetime.now(UTC) + timedelta(hours=hours_from_now)
    return ESPNEvent(
        espn_id="12345",
        name=name,
        short_name=short_name or name[:7],
        start_time=start,
        broadcast="ESPN",
        status="pre",
    )


def test_normalize_strips_noise():
    assert _normalize("Manchester United FC") == "manchester united"
    assert _normalize("Arsenal vs Chelsea") == "arsenal chelsea"
    assert _normalize("NEW @ LEE") == "new lee"


def test_exact_title_match():
    prog = _make_program("Arsenal vs Chelsea")
    events = [_make_espn_event("Arsenal at Chelsea", "ARS @ CHE")]
    match = find_best_match(prog, events)
    assert match is not None
    assert match.name == "Arsenal at Chelsea"


def test_reversed_name_order_matches():
    prog = _make_program("Aston Villa vs Arsenal")
    events = [_make_espn_event("Arsenal at Aston Villa", "ARS @ AVL")]
    match = find_best_match(prog, events)
    assert match is not None


def test_no_match_for_unrelated_event():
    prog = _make_program("Chelsea vs Spurs")
    events = [_make_espn_event("Real Madrid at Barcelona", "RMA @ BAR")]
    match = find_best_match(prog, events)
    assert match is None


def test_time_proximity_filter_rejects_distant_events():
    prog = _make_program("Arsenal vs Chelsea", hours_from_now=2)
    # Event is 5 days away — should be rejected by default 48h filter
    events = [_make_espn_event("Arsenal at Chelsea", hours_from_now=120)]
    match = find_best_match(prog, events)
    assert match is None


def test_best_match_selected_from_multiple():
    prog = _make_program("Manchester City vs Liverpool")
    events = [
        _make_espn_event("Chelsea at Arsenal", "CHE @ ARS"),
        _make_espn_event("Manchester City at Liverpool", "MCI @ LIV"),
        _make_espn_event("Wolves at Everton", "WOL @ EVE"),
    ]
    match = find_best_match(prog, events)
    assert match is not None
    assert match.name == "Manchester City at Liverpool"


def test_empty_events_returns_none():
    prog = _make_program("Arsenal vs Chelsea")
    match = find_best_match(prog, [])
    assert match is None


def test_short_name_matching():
    """Sometimes the short name is a closer match than the full name."""
    prog = _make_program("DEN vs KC")
    events = [_make_espn_event("Denver Broncos at Kansas City Chiefs", "DEN @ KC")]
    match = find_best_match(prog, events)
    assert match is not None


def test_fetch_espn_events_handles_network_failure():
    with patch("requests.get", side_effect=Exception("Network error")):
        assert fetch_espn_events("football", "nfl") == []
