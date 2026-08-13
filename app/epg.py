import os
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta

import app.config as config
from app.parser import parse_line

logger = logging.getLogger(__name__)


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

    if os.path.exists(config.EPG_OUTPUT_FILE):
        try:
            tree = ET.parse(config.EPG_OUTPUT_FILE)
            root = tree.getroot()
            for ch in root.findall('channel'):
                ch_id = ch.get('id')
                name_elem = ch.find('display-name')
                if ch_id and name_elem is not None:
                    channels[ch_id] = name_elem.text

            for prog in root.findall('programme'):
                ch_id = prog.get('channel')
                start_str = prog.get('start')
                stop_str = prog.get('stop')
                title_elem = prog.find('title')
                title = title_elem.text if title_elem is not None else ""
                
                if not start_str or not stop_str:
                    continue
                    
                start_dt_str, offset = start_str.split(' ')
                try:
                    start_time = datetime.strptime(start_dt_str, "%Y%m%d%H%M%S")
                    stop_dt_str, _ = stop_str.split(' ')
                    stop_time = datetime.strptime(stop_dt_str, "%Y%m%d%H%M%S")
                except ValueError:
                    continue
                
                programs_dict[(ch_id, start_time)] = {
                    'channel_id': ch_id, 'title': title, 
                    'start_time': start_time, 'stop_time': stop_time, 'offset': f" {offset}"
                }
        except Exception as e:
            logger.warning(f"Could not parse existing EPG file: {e}")

    current_year = datetime.now().year
    for message in messages:
        lines = message.text.strip().split('\n')
        for line in lines:
            program_data = parse_line(line, current_year)
            if program_data:
                if program_data['channel_id'] not in channels:
                    channels[program_data['channel_id']] = program_data['channel_name']
                programs_dict[(program_data['channel_id'], program_data['start_time'])] = program_data

    programs = sorted(programs_dict.values(), key=lambda x: (x['channel_id'], x['start_time']))
    
    logger.info("Generating new EPG XML...")
    tv_elem = ET.Element('tv', {'generator-info-name': 'Telegram2EPG'})
    
    active_prog_channels = {prog['channel_id'] for prog in programs if prog['start_time'] >= datetime.now() - timedelta(days=1)}

    for ch_id, ch_name in sorted(channels.items()):
        ch_elem = ET.SubElement(tv_elem, 'channel', {'id': ch_id})
        ET.SubElement(ch_elem, 'display-name').text = ch_name

    for i, prog in enumerate(programs):
        if prog['start_time'] < datetime.now() - timedelta(days=1):
            continue

        if prog.get('stop_time') is None:
            next_prog_start = next((p['start_time'] for p in programs[i+1:] if p['channel_id'] == prog['channel_id']), None)
            prog['stop_time'] = next_prog_start or (prog['start_time'] + timedelta(hours=3))

        prog_elem = ET.SubElement(tv_elem, 'programme', {
            'start': prog['start_time'].strftime("%Y%m%d%H%M%S") + prog['offset'],
            'stop': prog['stop_time'].strftime("%Y%m%d%H%M%S") + prog['offset'],
            'channel': prog['channel_id']
        })
        ET.SubElement(prog_elem, 'title').text = prog['title']
        ET.SubElement(prog_elem, 'desc').text = prog['title']

    xml_output = prettify_xml(tv_elem)
    with open(config.EPG_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml_output)
    logger.info(f"Local EPG updated at {config.EPG_OUTPUT_FILE}")