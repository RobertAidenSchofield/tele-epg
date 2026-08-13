import os
import logging

# --- Docker Environment Variables ---
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '').strip()
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '').strip()
TARGET_CHAT = os.environ.get('TARGET_CHAT', '').strip()
# Automatically convert numeric IDs (including negative ones) to integers
if TARGET_CHAT and TARGET_CHAT.replace('-', '', 1).isdigit():
    TARGET_CHAT = int(TARGET_CHAT)
UPDATE_INTERVAL_HOURS = int(os.environ.get('UPDATE_INTERVAL_HOURS', 6))

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()
GIST_ID = os.environ.get('GIST_ID', '').strip()

SESSION_FILE = '/app/data/telegram_session'
EPG_OUTPUT_FILE = '/app/data/epg.xml'

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def validate_config():
    """Validates that essential configuration is present."""
    return all([API_ID, API_HASH, PHONE_NUMBER, TARGET_CHAT])