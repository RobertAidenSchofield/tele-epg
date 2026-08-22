import sys
import asyncio
import logging

import app.config as config
from app.telegram_client import EPGTelegramClient
from app.epg import generate_epg_from_messages
from app.gist_uploader import upload_to_gist

logger = logging.getLogger(__name__)

async def main():
    """Main execution loop."""
    if not config.validate_config():
        logger.error("Missing one or more required environment variables. Please check your configuration.")
        sys.exit(1)

    telegram_client = EPGTelegramClient()
    try:
        await telegram_client.start()
        while True:
            try:
                messages = await telegram_client.fetch_messages()
                generate_epg_from_messages(messages)
                upload_to_gist()
            except KeyboardInterrupt:
                logger.info("Shutdown requested. Exiting.")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            
            logger.info(f"Sleeping for {config.UPDATE_INTERVAL_HOURS} hours...")
            await asyncio.sleep(config.UPDATE_INTERVAL_HOURS * 3600)
    finally:
        logger.info("Shutting down Telegram client...")
        await telegram_client.stop()

if __name__ == '__main__':
    asyncio.run(main())