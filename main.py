import sys
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import load_settings
from app.telegram.client import EPGTelegramClient
from app.parser import parse_message
from app.espn import enrich_programs
from app.epg.generator import generate_epg
from app.output.gist import upload_epg_to_gist

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    """Main execution loop."""
    settings = load_settings()
    if not settings.validate():
        logger.error("Missing one or more required environment variables. Please check your configuration.")
        sys.exit(1)

    client = EPGTelegramClient(settings)
    try:
        await client.start()
        while True:
            try:
                # 1. Fetch message texts and timestamps from Telegram
                messages = await client.fetch_epg_messages()

                # 2. Parse all messages into ProgramData
                programs = []
                for text, msg_date in messages:
                    programs.extend(parse_message(text, reference_dt=msg_date))

                # 3. Enrich with ESPN data (exact times)
                programs = enrich_programs(programs)

                # 4. Generate XMLTV file
                generate_epg(programs, settings.epg_output_file)

                # 5. Upload to GitHub Gist
                upload_epg_to_gist(
                    settings.github_token,
                    settings.gist_id,
                    settings.epg_output_file,
                )
            except KeyboardInterrupt:
                logger.info("Shutdown requested. Exiting.")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)

            logger.info(f"Sleeping for {settings.update_interval_hours} hours...")
            await asyncio.sleep(settings.update_interval_hours * 3600)
    finally:
        logger.info("Shutting down Telegram client...")
        await client.stop()


if __name__ == '__main__':
    asyncio.run(main())