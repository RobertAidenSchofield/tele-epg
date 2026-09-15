import hashlib
import logging
import requests

logger = logging.getLogger(__name__)

_last_uploaded_hashes: dict[tuple[str, str], str] = {}


def upload_epg_to_gist(token: str, gist_id: str, file_path: str) -> bool:
    """Uploads the EPG file content to a GitHub Gist.
    
    Skips upload if the file content has not changed since the last upload.
    Returns True on success or skip, False on failure.
    """
    if not token or not gist_id:
        logger.error("GitHub Token or Gist ID missing! Skipping Gist upload.")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        cache_key = (gist_id, file_path)

        if _last_uploaded_hashes.get(cache_key) == content_hash:
            logger.info("EPG content unchanged; skipping redundant Gist upload.")
            return True

        logger.info("Uploading to GitHub Gist...")
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        data = {"files": {"epg.xml": {"content": content}}}
        response = requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers=headers,
            json=data,
        )

        if response.status_code == 200:
            logger.info("SUCCESS: Gist updated.")
            _last_uploaded_hashes[cache_key] = content_hash
            return True
        else:
            logger.error("Gist Upload Failed: %s - %s", response.status_code, response.text)
            return False
    except Exception as e:
        logger.error("Error during Gist upload: %s", e, exc_info=True)
        return False


def upload_to_gist():
    """Legacy wrapper that reads settings from config module."""
    from app import config
    return upload_epg_to_gist(config.GITHUB_TOKEN, config.GIST_ID, config.EPG_OUTPUT_FILE)
