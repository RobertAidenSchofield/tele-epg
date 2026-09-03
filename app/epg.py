import os
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import app.config as config
from app.parser import parse_line

logger = logging.getLogger(__name__)
NY_TZ = ZoneInfo("America/New_York")


def format_xmltv_datetime(value):
    return value.strftime("%Y%m%d%H%M%S %z")


def prettify_xml(elem):
    """Converts an ElementTree element to a pretty-printed XML string with a DTD."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    # The first line is the xml declaration, and we want to add our DTD right after.
    xml_declaration, rest_of_xml = reparsed.toprettyxml(indent="  ").split('\n', 1)
    
    return f'{xml_declaration}\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n{rest_of_xml}'


def generate_epg_from_messages(messages):
    """Generates an EPG XML file from a list of Telegram messages."""
    channels = {}
    programs_dict = {}

    current_year = datetime.now(NY_TZ).year
    for message in messages:
        lines = message.text.strip().split('\n')
        for line in lines:
            program_data = parse_line(line, current_year)
            if program_data:
                if program_data['channel_id'] not in channels:
                    channels[program_data['channel_id']] = program_data['channel_name']
                programs_dict[(program_data['channel_id'], program_data['start_time'])] = program_data

    programs = sorted(
        programs_dict.values(),
        key=lambda x: (x['channel_id'], x['start_time'])
    )
    now_ny = datetime.now(NY_TZ)

    logger.info("Generating new EPG XML...")
    tv_elem = ET.Element("tv", {"generator-info-name": "Telegram2EPG"})

    for ch_id, ch_name in sorted(channels.items()):
        ch_elem = ET.SubElement(tv_elem, "channel", {'id': ch_id})
        ET.SubElement(ch_elem, "display-name").text = ch_name

    for i, prog in enumerate(programs):
        if prog["start_time"] < now_ny - timedelta(days=1):
            continue

        if prog.get('stop_time') is None:
            next_prog_start = next(
                (
                    p['start_time']
                    for p in programs[i + 1:]
                    if p['channel_id'] == prog['channel_id']
                ),
                None,
            )
            prog['stop_time'] = next_prog_start or (
                prog['start_time'] + timedelta(hours=3)
            )

        if prog['stop_time'] <= prog['start_time']:
            prog['stop_time'] = prog['start_time'] + timedelta(hours=3)

        prog_elem = ET.SubElement(
            tv_elem,
            "programme",
            {
                "start": format_xmltv_datetime(prog["start_time"]),
                "stop": format_xmltv_datetime(prog["stop_time"]),
                "channel": prog["channel_id"],
            },
        )
        ET.SubElement(prog_elem, 'title').text = prog['title']
        ET.SubElement(prog_elem, 'desc').text = prog['title']

    xml_output = prettify_xml(tv_elem)
    with open(config.EPG_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml_output)
    logger.info(f"Local EPG updated at {config.EPG_OUTPUT_FILE}")