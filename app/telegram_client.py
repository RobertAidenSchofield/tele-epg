import logging
from telethon import TelegramClient
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
            

    async def is_connected(self):
        """Checks if the client is connected."""
        return self.client.is_connected()

    async def ensure_connected(self):
        """Ensures the client is connected, reconnecting if necessary."""
        if not await self.is_connected():
            logger.warning("Telegram client was not connected. Attempting to reconnect...")
            await self.start()
            logger.info("Telegram client reconnected.")

    async def fetch_messages(self, limit=500):
        await self.ensure_connected()
        """Fetch recent messages from the target chat."""
        logger.info(f"Fetching messages from {config.TARGET_CHAT}...")
        messages = self.client.iter_messages(config.TARGET_CHAT, limit=limit) # type: ignore
        message_list = [message async for message in messages if message.text]
        logger.info(f"Fetched {len(message_list)} messages with text.")
        return message_list
