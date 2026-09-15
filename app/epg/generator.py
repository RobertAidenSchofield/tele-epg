import gzip
import logging
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import app.config as config
from app.parser import parse_message, ProgramData
from app.epg.xmltv import format_xmltv_datetime, prettify_xml

logger = logging.getLogger(__name__)
NY_TZ = ZoneInfo("America/New_York")

DEFAULT_SPORT_DURATIONS = {
    "soccer": timedelta(hours=2),
    "basketball": timedelta(hours=2, minutes=30),
    "baseball": timedelta(hours=2, minutes=45),
    "football": timedelta(hours=3, minutes=30),
    "mma": timedelta(hours=3, minutes=30),
    "boxing": timedelta(hours=3, minutes=30),
    "hockey": timedelta(hours=2, minutes=30),
}
FALLBACK_DURATION = timedelta(hours=3)


def _get_default_duration(sport: str | None) -> timedelta:
    if sport and sport.lower() in DEFAULT_SPORT_DURATIONS:
        return DEFAULT_SPORT_DURATIONS[sport.lower()]
    return FALLBACK_DURATION


def generate_epg_from_messages(messages):
    """Generates an EPG XML file from a list of Telegram messages."""
    current_year = datetime.now(NY_TZ).year
    programs = []
    for message in messages:
        if hasattr(message, 'text') and message.text:
            ref_dt = getattr(message, 'date', None) or current_year
            parsed = parse_message(message.text, ref_dt)
            if parsed:
                programs.extend(parsed)

    generate_epg(programs, config.EPG_OUTPUT_FILE)


def generate_epg(programs: list[ProgramData], output_path: str):
    channels = {}
    programs_dict = {}

    for prog in programs:
        if prog.channel_id not in channels:
            channels[prog.channel_id] = prog.channel_name
        programs_dict[(prog.channel_id, prog.start_time)] = prog

    sorted_programs = sorted(
        programs_dict.values(),
        key=lambda x: (x.channel_id, x.start_time)
    )
    now_ny = datetime.now(NY_TZ)

    logger.info("Generating new EPG XML...")
    tv_elem = ET.Element("tv", {"generator-info-name": "Telegram2EPG"})

    for ch_id, ch_name in sorted(channels.items()):
        ch_elem = ET.SubElement(tv_elem, "channel", {'id': ch_id})
        ET.SubElement(ch_elem, "display-name").text = ch_name

    for i, prog in enumerate(sorted_programs):
        if prog.start_time < now_ny - timedelta(days=1):
            continue

        default_duration = _get_default_duration(prog.sport)

        stop_time = prog.stop_time
        if stop_time is None:
            next_prog_start = next(
                (
                    p.start_time
                    for p in sorted_programs[i + 1:]
                    if p.channel_id == prog.channel_id
                ),
                None,
            )
            stop_time = next_prog_start or (
                prog.start_time + default_duration
            )

        if stop_time <= prog.start_time:
            stop_time = prog.start_time + default_duration

        prog_elem = ET.SubElement(
            tv_elem,
            "programme",
            {
                "start": format_xmltv_datetime(prog.start_time),
                "stop": format_xmltv_datetime(stop_time),
                "channel": prog.channel_id,
            },
        )
        ET.SubElement(prog_elem, 'title').text = prog.title
        ET.SubElement(prog_elem, 'desc').text = prog.desc or prog.title
        if prog.icon_url:
            ET.SubElement(prog_elem, 'icon', {'src': prog.icon_url})

    xml_output = prettify_xml(tv_elem)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_output)
    logger.info(f"Local EPG updated at {output_path}")

    # Also generate gzipped version (epg.xml.gz)
    gz_output_path = f"{output_path}.gz"
    try:
        with open(output_path, "rb") as f_in, gzip.open(gz_output_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        logger.info(f"Gzipped EPG updated at {gz_output_path}")
    except Exception as e:
        logger.warning(f"Failed to create gzipped EPG: {e}")
