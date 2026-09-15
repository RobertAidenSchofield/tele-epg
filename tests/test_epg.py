import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.config as config
from app.epg.generator import generate_epg_from_messages


NY_TZ = ZoneInfo("America/New_York")


def _uk_event(channel, title, event_time):
    date_text = event_time.strftime("%a %d %b")
    time_text = event_time.strftime("%-I:%M%p").lower()
    return (
        f"UK| {channel} | {title} // UK {date_text} {time_text} "
        f"// ET {date_text} {time_text}"
    )


def test_generation_writes_ordered_programmes_and_infers_stop_time(
    tmp_path, monkeypatch
):
    output_file = tmp_path / "epg.xml"
    monkeypatch.setattr(config, "EPG_OUTPUT_FILE", str(output_file))

    first_start = datetime.now(NY_TZ).replace(
        hour=15, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    second_start = first_start.replace(hour=17)
    message = SimpleNamespace(
        text="\n".join(
            [
                _uk_event("PREMIER LEAGUE+ 01", "Early match", first_start),
                _uk_event("PREMIER LEAGUE+ 01", "Late match", second_start),
            ]
        )
    )

    generate_epg_from_messages([message])

    root = ET.parse(output_file).getroot()
    programmes = root.findall("programme")

    assert [programme.findtext("title") for programme in programmes] == [
        "Early match",
        "Late match",
    ]
    assert programmes[0].get("channel") == "premierleague01"
    assert programmes[0].get("start") < programmes[0].get("stop")
    assert programmes[0].get("stop") == programmes[1].get("start")
    assert programmes[1].get("stop") > programmes[1].get("start")


def test_generation_replaces_stale_output(tmp_path, monkeypatch):
    output_file = tmp_path / "epg.xml"
    output_file.write_text(
        '<tv><programme channel="old" start="20000101000000 +0000" '
        'stop="20000101010000 +0000"><title>Stale event</title></programme></tv>',
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "EPG_OUTPUT_FILE", str(output_file))

    event_time = datetime.now(NY_TZ) + timedelta(days=1)
    message = SimpleNamespace(
        text=_uk_event("TEST CHANNEL", "Current event", event_time)
    )

    generate_epg_from_messages([message])

    root = ET.parse(output_file).getroot()
    titles = [programme.findtext("title") for programme in root.findall("programme")]

    assert titles == ["Current event"]
    assert "Stale event" not in titles


def test_generation_corrects_invalid_stop_time(tmp_path, monkeypatch):
    output_file = tmp_path / "epg.xml"
    monkeypatch.setattr(config, "EPG_OUTPUT_FILE", str(output_file))

    start = datetime.now(NY_TZ) + timedelta(days=1)
    start = start.replace(hour=15, minute=0, second=0, microsecond=0)
    stop = start - timedelta(hours=1)
    message = SimpleNamespace(
        text=(
            "PPV| TEST CHANNEL | Invalid interval "
            f"start:{start.astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%d %H:%M:%S')} "
            f"stop:{stop.astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%d %H:%M:%S')}"
        )
    )

    generate_epg_from_messages([message])

    programme = ET.parse(output_file).getroot().find("programme")
    start_time = datetime.strptime(programme.get("start"), "%Y%m%d%H%M%S %z")
    stop_time = datetime.strptime(programme.get("stop"), "%Y%m%d%H%M%S %z")

    assert stop_time - start_time == timedelta(hours=3)


def test_generation_includes_icon_and_rich_desc_and_no_category(tmp_path):
    import gzip
    from app.parser import ProgramData
    from app.epg.generator import generate_epg

    output_file = tmp_path / "epg.xml"
    start = datetime.now(NY_TZ) + timedelta(days=1)

    prog = ProgramData(
        channel_name="NFL 01",
        channel_id="nfl01",
        title="Denver Broncos at Kansas City Chiefs",
        start_time=start,
        stop_time=None,
        desc="NFL Regular Season: Denver Broncos at Kansas City Chiefs (Live from Arrowhead)",
        icon_url="https://a.espncdn.com/logo.png",
        sport="football",
    )

    generate_epg([prog], str(output_file))

    root = ET.parse(output_file).getroot()
    p = root.find("programme")
    assert p is not None
    assert p.findtext("title") == "Denver Broncos at Kansas City Chiefs"
    assert p.findtext("desc") == "NFL Regular Season: Denver Broncos at Kansas City Chiefs (Live from Arrowhead)"
    icon = p.find("icon")
    assert icon is not None
    assert icon.get("src") == "https://a.espncdn.com/logo.png"
    # Ensure NO category tags are present
    assert p.find("category") is None

    # Verify gzipped file was created and is valid gzip
    gz_file = tmp_path / "epg.xml.gz"
    assert gz_file.exists()
    with gzip.open(gz_file, "rb") as f:
        decompressed = f.read().decode("utf-8")
    assert "Denver Broncos at Kansas City Chiefs" in decompressed


def test_generation_applies_sport_specific_durations(tmp_path):
    from app.parser import ProgramData
    from app.epg.generator import generate_epg

    output_file = tmp_path / "epg.xml"
    start = datetime.now(NY_TZ) + timedelta(days=1)

    soccer_prog = ProgramData(
        channel_name="PL 01",
        channel_id="pl01",
        title="Arsenal vs Chelsea",
        start_time=start,
        stop_time=None,
        sport="soccer",
    )
    football_prog = ProgramData(
        channel_name="NFL 01",
        channel_id="nfl01",
        title="Chiefs vs Broncos",
        start_time=start,
        stop_time=None,
        sport="football",
    )

    generate_epg([soccer_prog, football_prog], str(output_file))

    root = ET.parse(output_file).getroot()
    progs = root.findall("programme")

    soccer_elem = next(p for p in progs if p.get("channel") == "pl01")
    football_elem = next(p for p in progs if p.get("channel") == "nfl01")

    s_start = datetime.strptime(soccer_elem.get("start"), "%Y%m%d%H%M%S %z")
    s_stop = datetime.strptime(soccer_elem.get("stop"), "%Y%m%d%H%M%S %z")
    assert s_stop - s_start == timedelta(hours=2)  # soccer default is 2 hours

    f_start = datetime.strptime(football_elem.get("start"), "%Y%m%d%H%M%S %z")
    f_stop = datetime.strptime(football_elem.get("stop"), "%Y%m%d%H%M%S %z")
    assert f_stop - f_start == timedelta(hours=3, minutes=30)  # football default is 3.5 hours

