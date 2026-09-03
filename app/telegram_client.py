import logging
from telethon import TelegramClient
import app.config as config
from datetime import datetime, timedelta, timezone

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

    async def fetch_messages(self, days=7):
        """Fetch text messages from the last specified number of days."""
        await self.ensure_connected()

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        logger.info(
            "Fetching messages from %s from the last %s day(s)...",
            config.TARGET_CHAT,
            days,
        )

        messages = self.client.iter_messages(
            config.TARGET_CHAT,
            limit=None,
        )

        message_list = []

        async for message in messages:
            if message.date < cutoff:
                break

            if message.text:
                message_list.append(message)

        logger.info(
            "Fetched %s messages with text from the last %s day(s).",
            len(message_list),
            days,
        )

        return message_list
