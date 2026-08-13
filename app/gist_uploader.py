import logging
import requests
from app import config

logger = logging.getLogger(__name__)

def upload_to_gist():
    """Uploads the EPG file content to a GitHub Gist."""
    if not config.GITHUB_TOKEN or not config.GIST_ID:
        logger.error("GitHub Token or Gist ID missing! Skipping Gist upload.")
        return

    logger.info("Uploading to GitHub Gist...")
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        with open(config.EPG_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        data = {"files": { "epg.xml": {"content": content}}}
        response = requests.patch(f"https://api.github.com/gists/{config.GIST_ID}", headers=headers, json=data)

        if response.status_code == 200:
            logger.info("SUCCESS: Gist updated.")
        else:
            logger.error(f"Gist Upload Failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error during Gist upload: {e}", exc_info=True)