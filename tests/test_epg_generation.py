import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.config as config
from app.epg import generate_epg_from_messages


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
