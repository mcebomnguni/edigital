import os
import logging
import requests
from typing import Optional, Dict

# Logger setup
logger = logging.getLogger(__name__)

# Agora constants
AGORA_BASE_URL = os.getenv("AGORA_BASE_URL", "https://api.agora.io")
AGORA_APP_ID = os.getenv("AGORA_APP_ID")
AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE")
AGORA_CUSTOMER_ID = os.getenv("AGORA_CUSTOMER_ID")
AGORA_CUSTOMER_SECRET = os.getenv("AGORA_CUSTOMER_SECRET")

# HTTP configuration
DEFAULT_TIMEOUT = 10  # seconds


class AgoraTokenError(Exception):
    """Custom exception for Agora token errors."""
    pass


def _validate_agora_credentials() -> None:
    """
    Ensure all necessary Agora credentials are available.
    Raises:
        AgoraTokenError: If any credential is missing.
    """
    missing = []
    if not AGORA_APP_ID:
        missing.append("AGORA_APP_ID")
    if not AGORA_APP_CERTIFICATE:
        missing.append("AGORA_APP_CERTIFICATE")
    if not AGORA_CUSTOMER_ID:
        missing.append("AGORA_CUSTOMER_ID")
    if not AGORA_CUSTOMER_SECRET:
        missing.append("AGORA_CUSTOMER_SECRET")

    if missing:
        msg = f"Missing required Agora credentials: {', '.join(missing)}"
        logger.error(msg)
        raise AgoraTokenError(msg)


def generate_token(channel_name: str, user_id: str) -> Dict:
    """
    Generate an Agora token for a given channel and user.

    Args:
        channel_name (str): The name of the Agora channel.
        user_id (str): The unique user ID for the token.

    Returns:
        dict: Token data returned by Agora.

    Raises:
        AgoraTokenError: If token generation fails or credentials are invalid.
    """
    _validate_agora_credentials()

    token_url = f"{AGORA_BASE_URL}/v1/tokens/generate"

    payload = {
        "channelName": channel_name,
        "uid": user_id,
        "appId": AGORA_APP_ID,
        "appCertificate": AGORA_APP_CERTIFICATE,
    }

    try:
        response = requests.post(token_url, json=payload, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        logger.info("Successfully generated token for channel '%s' and user '%s'.", channel_name, user_id)
        return response.json()
    except requests.RequestException as e:
        logger.exception("HTTP request failed while generating Agora token.")
        raise AgoraTokenError(f"Token generation failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error during Agora token generation.")
        raise AgoraTokenError(f"Unexpected error: {str(e)}")
