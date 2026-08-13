import logging
from telethon.sync import TelegramClient
import app.config as config

logger = logging.getLogger(__name__)


class EPGTelegramClient:
    def __init__(self):
        self.client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH)

    async def start(self):
        """Connects and logs in the client."""
        logger.info("Connecting to Telegram...")
        await self.client.start(phone=config.PHONE_NUMBER)
        logger.info("Telegram client connected.")

    async def stop(self):
        """Disconnects the client."""
        if self.client.is_connected():
            await self.client.disconnect()
            logger.info("Telegram client disconnected.")

    def fetch_messages(self, limit=500):
        """Fetch recent messages from the target chat."""
        logger.info(f"Fetching messages from {config.TARGET_CHAT}...")
        messages = self.client.iter_messages(config.TARGET_CHAT, limit=limit)
        message_list = [message for message in messages if message.text]
        logger.info(f"Fetched {len(message_list)} messages with text.")
        return message_list

