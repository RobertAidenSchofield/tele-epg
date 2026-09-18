import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    api_id: int
    api_hash: str
    phone_number: str
    target_chat: int | str
    update_interval_hours: int = 3
    github_token: str = ""
    gist_id: str = ""
    session_file: str = "/app/data/telegram_session"
    epg_output_file: str = "/app/data/epg.xml"

    def validate(self) -> bool:
        """Validates that essential configuration is present."""
        return all([self.api_id, self.api_hash, self.phone_number, self.target_chat])


def load_settings() -> Settings:
    """Load settings from environment variables."""
    target_chat_raw = os.environ.get('TARGET_CHAT', '').strip()
    target_chat: int | str = target_chat_raw
    if target_chat_raw and target_chat_raw.replace('-', '', 1).isdigit():
        target_chat = int(target_chat_raw)

    return Settings(
        api_id=int(os.environ.get('API_ID', 0)),
        api_hash=os.environ.get('API_HASH', '').strip(),
        phone_number=os.environ.get('PHONE_NUMBER', '').strip(),
        target_chat=target_chat,
        update_interval_hours=int(os.environ.get('UPDATE_INTERVAL_HOURS', 3)),
        github_token=os.environ.get('GITHUB_TOKEN', '').strip(),
        gist_id=os.environ.get('GIST_ID', '').strip(),
    )


# --- Legacy module-level access (for backward compatibility during migration) ---
# These will be removed once all modules use Settings directly.
_settings = load_settings()
API_ID = _settings.api_id
API_HASH = _settings.api_hash
PHONE_NUMBER = _settings.phone_number
TARGET_CHAT = _settings.target_chat
UPDATE_INTERVAL_HOURS = _settings.update_interval_hours
GITHUB_TOKEN = _settings.github_token
GIST_ID = _settings.gist_id
SESSION_FILE = _settings.session_file
EPG_OUTPUT_FILE = _settings.epg_output_file


def validate_config() -> bool:
    """Legacy validation function."""
    return _settings.validate()