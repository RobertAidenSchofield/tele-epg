import asyncio
import logging
import sys
from telethon.sync import TelegramClient

sys.path.append('.') # Allow importing from root directory

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    A helper script to connect to Telegram and list all chats with their IDs.
    This helps in finding the correct TARGET_CHAT ID for the main application.
    """
    print("--- Telegram Chat ID Finder ---")
    try:
        import app.config as config
        api_id = config.API_ID
        api_hash = config.API_HASH
        phone = config.PHONE_NUMBER
        if not all([api_id, api_hash, phone]):
            raise ImportError
        print("Configuration loaded from .env file.")
    except (ImportError, AttributeError):
        print("Could not load from .env, please enter details manually.")
        api_id = int(input("Enter your API_ID: ").strip())
        api_hash = input("Enter your API_HASH: ").strip()
        phone = input("Enter your phone number: ").strip()

    async with TelegramClient('get_chat_id_session', api_id, api_hash) as client:
        print("\nListing your recent chats and their IDs...\n")
        print(f"{'Chat Name':<50} | {'Chat ID'}")
        print("-" * 80)
        async for dialog in client.iter_dialogs(limit=50):
            chat_id = dialog.id
            print(f"{dialog.name:<50} | {chat_id}")

if __name__ == "__main__":
    asyncio.run(main())