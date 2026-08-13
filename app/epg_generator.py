import os
import re
import sys
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from xml.dom import minidom

import requests

# --- Docker Environment Variables ---
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '').strip()
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '').strip()
TARGET_CHAT = os.environ.get('TARGET_CHAT', '').strip()
# Automatically convert numeric IDs (including negative ones) to integers
if TARGET_CHAT.replace('-', '', 1).isdigit():
    TARGET_CHAT = int(TARGET_CHAT)
UPDATE_INTERVAL_HOURS = int(os.environ.get('UPDATE_INTERVAL_HOURS', 6))

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()
GIST_ID = os.environ.get('GIST_ID', '').strip()

SESSION_FILE = '/app/data/telegram_session'
EPG_OUTPUT_FILE = '/app/data/epg.xml'

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def extract_time_flexible(time_str):
    """Extract time from various formats like '8:00pm', '8pm', '20:00', etc."""
    if not time_str:
        return None
    time_str = time_str.strip().lower().replace(' ', '')
    
    # Try common 12-hour formats
    for fmt in ["%I:%M%p", "%I%p", "%H:%M", "%H"]:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def prettify_xml(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    xml_str = reparsed.toprettyxml(indent="  ")
    if xml_str.startswith("<?xml"):
        return re.sub(r'<\?xml.*?\?>', '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">', xml_str, count=1)
    else:
        return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n' + xml_str


def convert_utc_to_ny(naive_dt):
    """Treat naive_dt as UTC, convert to America/New_York, return naive local dt and offset string."""
    try:
        utc_tz = ZoneInfo("UTC")
        ny_tz = ZoneInfo("America/New_York")
        aware_dt = naive_dt.replace(tzinfo=utc_tz).astimezone(ny_tz)
        return aware_dt.replace(tzinfo=None), aware_dt.strftime(" %z")
    except (ValueError, TypeError):
        # Fallback for invalid datetime objects
        return naive_dt, " +0000"


def convert_et_to_ny(naive_dt):
    """Treat naive_dt as America/New_York, return naive local dt and offset string."""
    try:
        ny_tz = ZoneInfo("America/New_York")
        aware_dt = naive_dt.replace(tzinfo=ny_tz)
        return aware_dt.replace(tzinfo=None), aware_dt.strftime(" %z")
    except (ValueError, TypeError):
        return naive_dt, " -0400"  # Assume EDT as a fallback

# --- Parsing Handlers ---

def _handle_exact_utc(match, current_year):
    """Handler for formats with exact 'start' and 'stop' UTC timestamps."""
    start_dt_utc = datetime.strptime(match.group('start'), "%Y-%m-%d %H:%M:%S")
    stop_dt_utc = datetime.strptime(match.group('stop'), "%Y-%m-%d %H:%M:%S")
    start_time, offset = convert_utc_to_ny(start_dt_utc)
    stop_time, _ = convert_utc_to_ny(stop_dt_utc)
    return {'start_time': start_time, 'stop_time': stop_time, 'offset': offset}

def _handle_iso_utc(match, current_year):
    """Handler for formats with a full ISO 8601 timestamp in UTC."""
    iso_str = match.group('iso')
    start_dt_utc = datetime.strptime(iso_str, "%Y-%m-%d %H:%M:%S")
    start_time, offset = convert_utc_to_ny(start_dt_utc)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}
 
def _handle_month_day_time_et(match, current_year):
    """Handler for formats with 'Month Day Time ET' (e.g., Jul 04 5:00PM ET)."""
    date_str = f"{match.group('month')} {match.group('day')} {current_year} {match.group('time')}"
    start_dt_et = datetime.strptime(date_str, "%b %d %Y %I:%M%p")
    start_time, offset = convert_et_to_ny(start_dt_et)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}
 
def _handle_kickoff_time(match, current_year):
    """Handler for PPV formats with 'kick-off 8pm'."""
    time_text = match.group('kickoff').strip().lower().replace(' ', '')
    time_format = "%I:%M%p" if ':' in time_text else "%I%p"
    kickoff_time_obj = datetime.strptime(time_text, time_format).time()
 
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    start_dt_et = now_ny.replace(year=current_year, month=now_ny.month, day=now_ny.day,
                                 hour=kickoff_time_obj.hour, minute=kickoff_time_obj.minute,
                                 second=0, microsecond=0)
 
    if start_dt_et < now_ny:
        start_dt_et += timedelta(days=1)
 
    start_time, offset = convert_et_to_ny(start_dt_et)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}
 
def _handle_simple_time(match, current_year):
    """Handler for simple formats with just a time (e.g., '8:30pm')."""
    time_text = match.group('time').strip().lower().replace(' ', '')
    time_format = "%I:%M%p" if ':' in time_text else "%I%p"
    time_obj = datetime.strptime(time_text, time_format).time()
 
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    start_dt_et = now_ny.replace(year=current_year, month=now_ny.month, day=now_ny.day,
                                 hour=time_obj.hour, minute=time_obj.minute,
                                 second=0, microsecond=0)
 
    if start_dt_et < now_ny:
        start_dt_et += timedelta(days=1)
 
    start_time, offset = convert_et_to_ny(start_dt_et)
    return {'start_time': start_time, 'stop_time': None, 'offset': offset}
 
def _handle_time_only_et(match, current_year):
    """Handler for formats with only a time (e.g., '17:15') in ET, inferring date."""
    time_text = match.group('time').strip()
    time_obj = None
    try:
        time_obj = datetime.strptime(time_text, "%H:%M").time()
    except ValueError:
        try:
            time_obj = datetime.strptime(time_text, "%I:%M%p").time()
        except ValueError:
            try:
                time_obj = datetime.strptime(time_text, "%I%p").time()
            except ValueError:
                pass
 
    if time_obj is None:
        logger.warning(f"Could not parse time: {time_text}")
        return None
 
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    start_dt_ny = now_ny.replace(year=current_year, month=now_ny.month, day=now_ny.day,
                                 hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
 
    if start_dt_ny < now_ny:
        start_dt_ny += timedelta(days=1)
 
    start_time, offset = convert_et_to_ny(start_dt_ny)
    return {
        'start_time': start_time,
        'stop_time': None,
        'offset': offset
    }


# --- Regex Pattern Configuration ---
# The script will try to match each pattern in this list in order.
# The first one that matches will be used.

PATTERNS = [
    {
        # Format: PREFIX | Title start:YYYY-MM-DD HH:MM:SS stop:YYYY-MM-DD HH:MM:SS
        # e.g., PPV| FLO SPORTS TV 09 : 2026 Tour of Austria start:2026-07-08 13:45:00 stop:2026-07-13 01:59:59
        # e.g., US| MLB LIVE 09 | Cubs x Nationals start:2026-08-12 23:45:00 stop:2026-08-13 06:58:20
        "regex": re.compile(
            r"^(?P<prefix>PPV|UK|US|AU)\|\s*(?P<channel>[^|:-]+?)\s*(?:\||:|-)\s*"
            r"(?P<title>.*?)\s+start:(?P<start>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+"
            r"stop:(?P<stop>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})"
        ),
        "handler": _handle_exact_utc
    },
    {
        # New: PREFIX| Channel | Title (ISO Timestamp)
        # e.g., US| MLS LIVE 01 | Leagues Cup: Leagues Cup Countdown (2026-08-12 18:25:00)
        # e.g., US| ESPN+ 109 | PGA TOUR: PGA TOUR LIVE BetCast ... (2026-08-13 14:00:55)
        "regex": re.compile(
            r"^(?P<prefix>US|UK|AU|CA|PPV)\|\s*(?P<channel>[^|]+?)\s*\|\s*(?P<title>.*?)\s*\((?P<iso>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\)"
        ),
        "handler": _handle_iso_utc
    },
    {
        # Existing: flolive: 2026 Title (Description) (2026-06-28 09:30:00)
        "regex": re.compile(
            r"^(?P<channel>[^:]+?):\s*(?:\d{4}\s*)?(?P<title>.+?)\s*\(.+?\)\s*"
            r"\((?P<iso>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\)"
        ),
        "handler": _handle_iso_utc
    },
    {
        # Existing: ESPN+ 060 : Sat_ 7/4 _ ESPNFC Jul 04 7:00PM ET
        "regex": re.compile(
            r"^(?P<channel>ESPN\+ \d{3})\s*:\s*(?P<title>.*?)\s+"
            r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{1,2}:\d{2}[ap]m)\s+ET",
            re.IGNORECASE # Added IGNORECASE for robustness
        ),
        "handler": _handle_month_day_time_et
    },
    {
        # New: PPV| PSF 01| 17:15 Newcastle United vs Everton
        "regex": re.compile(
            r"^(?P<prefix>PPV)\|\s*(?P<channel>[^|]+?)\|\s*(?P<time>\d{1,2}:\d{2}(?:[ap]m)?)\s*(?P<title>.*)"
        ),
        "handler": _handle_time_only_et
    },
    {
        # Existing: PPV| Channel | Title , kick-off 8pm
        "regex": re.compile(
            r"^PPV\|\s*(?P<channel>[^|:-]+?)\s*(?:\||:|-)\s*(?P<title>.*?)\s*,\s*kick-off\s*(?P<kickoff>\d{1,2}(?::\d{2})?\s*[ap]m)",
            re.IGNORECASE # Added IGNORECASE for robustness
        ),
        "handler": _handle_kickoff_time
    },
    {
        # Existing: PPV| Channel: Title 8:30pm
        "regex": re.compile(
            r"^PPV\|\s*(?P<channel>[^:]+?)\s*:\s*(?P<title>.*?)\s+(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))\s*$",
            re.IGNORECASE # Added IGNORECASE for robustness
        ),
        "handler": _handle_simple_time
    },
]

def parse_line(line, current_year):
    """Parse a single line using the configured patterns and handlers."""
    line = line.strip()
    if not line:
        return None

    for p in PATTERNS:
        match = p['regex'].match(line)
        if match:
            try:
                groups = match.groupdict()
                channel_name = groups.get('channel', '').strip()
                title = groups.get('title', '').strip()
                channel_id = re.sub(r'[^a-z0-9]', '', channel_name.lower())

                time_data = p['handler'](match, current_year)

                return {
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'title': title,
                    **time_data
                }
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse line with handler '{p['handler'].__name__}': {line} | Error: {e}")
                continue  # Try next pattern
    return None


def upload_to_gist():
    if not GITHUB_TOKEN or not GIST_ID:
        logger.error("GitHub Token or Gist ID missing!")
        return

    logger.info("Uploading to GitHub Gist...")
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        with open(EPG_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        data = {
            "files": {
                "epg.xml": {
                    "content": content
                }
            }
        }

        response = requests.patch(f"https://api.github.com/gists/{GIST_ID}", headers=headers, json=data)
        
        if response.status_code == 200:
            logger.info("SUCCESS: Gist updated.")
        else:
            logger.error(f"Gist Upload Failed: {response.text}")
            
    except Exception as e:
        logger.error(f"Error during Gist upload: {e}")

def generate_epg():
    logger.info("Connecting to Telegram...")
    from telethon.sync import TelegramClient
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    client.start(PHONE_NUMBER)

    channels = {}
    programs_dict = {}

    if os.path.exists(EPG_OUTPUT_FILE):
        try:
            tree = ET.parse(EPG_OUTPUT_FILE)
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
                    
                start_dt_str = start_str[:14]
                offset = start_str[14:]
                try:
                    start_time = datetime.strptime(start_dt_str, "%Y%m%d%H%M%S")
                    stop_dt_str = stop_str[:14]
                    stop_time = datetime.strptime(stop_dt_str, "%Y%m%d%H%M%S")
                except ValueError:
                    continue
                
                programs_dict[(ch_id, start_time)] = {
                    'channel_id': ch_id, 'title': title, 
                    'start_time': start_time, 'stop_time': stop_time, 'offset': offset
                }
        except Exception as e:
            logger.warning(f"Could not parse existing EPG file: {e}")

    current_year = datetime.now().year

    logger.info(f"Fetching messages from {TARGET_CHAT}...")
    for message in client.iter_messages(TARGET_CHAT, limit=500):
        if not message.text:
            continue
        lines = message.text.strip().split('\n')
        
        for line in lines:
            program_data = parse_line(line, current_year)
            if program_data:
                if program_data['channel_id'] not in channels:
                    channels[program_data['channel_id']] = program_data['channel_name']
                programs_dict[(program_data['channel_id'], program_data['start_time'])] = program_data

    client.disconnect()
    
    programs = list(programs_dict.values())
    programs.sort(key=lambda x: (x['channel_id'], x['start_time']))
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    logger.info("Generating new EPG XML...")

    tv_elem = ET.Element('tv', {'generator-info-name': 'Telegram2EPG'})
    
    for ch_id, ch_name in sorted(channels.items()):
        ch_elem = ET.SubElement(tv_elem, 'channel', {'id': ch_id})
        name_elem = ET.SubElement(ch_elem, 'display-name')
        name_elem.text = ch_name

    active_prog_channels = set()
    for i, prog in enumerate(programs):
        if not (yesterday <= prog['start_time']):
            continue
            
        active_prog_channels.add(prog['channel_id'])

        if prog['stop_time'] is None:
            if i + 1 < len(programs) and programs[i+1]['channel_id'] == prog['channel_id']:
                prog['stop_time'] = programs[i+1]['start_time']
            else:
                prog['stop_time'] = prog['start_time'] + timedelta(hours=3)

        start_xmltv = prog['start_time'].strftime("%Y%m%d%H%M%S") + prog['offset']
        stop_xmltv = prog['stop_time'].strftime("%Y%m%d%H%M%S") + prog['offset']

        prog_elem = ET.SubElement(tv_elem, 'programme', {'start': start_xmltv, 'stop': stop_xmltv, 'channel': prog['channel_id']})
        title_elem = ET.SubElement(prog_elem, 'title')
        title_elem.text = prog['title']
        
        desc_elem = ET.SubElement(prog_elem, 'desc')
        desc_elem.text = prog['title']

    # Add placeholder events for channels with no active programs
    now = datetime.now()
    dummy_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    dummy_stop = dummy_start + timedelta(days=2) # 48 hour block
    dummy_start_str = dummy_start.strftime("%Y%m%d%H%M%S") + " +0000"
    dummy_stop_str = dummy_stop.strftime("%Y%m%d%H%M%S") + " +0000"

    for ch_id in sorted(channels.keys()):
        if ch_id not in active_prog_channels:
            prog_elem = ET.SubElement(tv_elem, 'programme', {'start': dummy_start_str, 'stop': dummy_stop_str, 'channel': ch_id})
            title_elem = ET.SubElement(prog_elem, 'title')
            title_elem.text = "To Be Announced"
            desc_elem = ET.SubElement(prog_elem, 'desc')
            desc_elem.text = "To Be Announced"

    xml_output = prettify_xml(tv_elem)
    with open(EPG_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(xml_output)
        
    logger.info("Local EPG updated.")
    upload_to_gist()

if __name__ == '__main__':
    if not all([API_ID, API_HASH, PHONE_NUMBER, TARGET_CHAT]):
        logger.error("Missing one or more required environment variables: API_ID, API_HASH, PHONE_NUMBER, TARGET_CHAT")
        sys.exit(1)

    while True:
        try:
            generate_epg()
        except Exception as e:
            logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
        logger.info(f"Sleeping for {UPDATE_INTERVAL_HOURS} hours...")
        time.sleep(UPDATE_INTERVAL_HOURS * 3600)