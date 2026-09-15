import logging
from telethon import TelegramClient
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class EPGTelegramClient:
    def __init__(self, settings=None):
        if settings is None:
            # Legacy: fall back to module-level config
            import app.config as config
            self.session_file = config.SESSION_FILE
            self.api_id = config.API_ID
            self.api_hash = config.API_HASH
            self.phone_number = config.PHONE_NUMBER
            self.target_chat = config.TARGET_CHAT
        else:
            self.session_file = settings.session_file
            self.api_id = settings.api_id
            self.api_hash = settings.api_hash
            self.phone_number = settings.phone_number
            self.target_chat = settings.target_chat

        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)

    async def start(self):
        """Connects and logs in the client."""
        logger.info("Connecting to Telegram...")
        await self.client.start(phone=self.phone_number)
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
        """Fetch raw message objects from the last specified number of days."""
        await self.ensure_connected()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        logger.info(
            "Fetching messages from %s from the last %s day(s)...",
            self.target_chat,
            days,
        )

        messages = self.client.iter_messages(
            self.target_chat,
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

    async def fetch_epg_messages(self, days=7):
        """Fetch message texts and post timestamps from the last specified number of days.
        
        Returns a list of (text, date) tuples so downstream code doesn't
        depend on Telethon Message types but has access to the post date.
        """
        raw_messages = await self.fetch_messages(days=days)
        return [(msg.text, msg.date) for msg in raw_messages]
