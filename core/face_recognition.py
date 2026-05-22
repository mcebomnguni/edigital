import requests
import os
import logging
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Load Azure API credentials from environment variables
API_KEY = os.getenv('AZURE_API_KEY')
ENDPOINT = os.getenv('AZURE_ENDPOINT')

if not API_KEY or not ENDPOINT:
    logger.warning("Azure Face API credentials are not fully configured in environment variables.")


def detect_face(image_path: str) -> Optional[str]:
    """
    Detect a face in the given image and return the face ID.

    Args:
        image_path (str): Path to the image file.

    Returns:
        Optional[str]: Face ID if detected, else None.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at: {image_path}")

    url = f"{ENDPOINT}/face/v1.0/detect"
    headers = {
        'Ocp-Apim-Subscription-Key': API_KEY,
        'Content-Type': 'application/octet-stream',
    }
    params = {'returnFaceId': 'true'}

    try:
        with open(image_path, 'rb') as image_file:
            response = requests.post(url, headers=headers, params=params, data=image_file.read())

        response.raise_for_status()
        faces = response.json()

        if faces:
            return faces[0].get('faceId')
        return None

    except requests.RequestException as e:
        logger.error(f"Failed to detect face: {e}")
        raise Exception(f"Azure Face API error: {e}")


def compare_faces(face_id_1: str, face_id_2: str) -> bool:
    """
    Compare two face IDs to determine if they belong to the same person.

    Args:
        face_id_1 (str): First face ID.
        face_id_2 (str): Second face ID.

    Returns:
        bool: True if faces are identical, False otherwise.
    """
    url = f"{ENDPOINT}/face/v1.0/verify"
    headers = {
        'Ocp-Apim-Subscription-Key': API_KEY,
        'Content-Type': 'application/json',
    }
    payload = {'faceId1': face_id_1, 'faceId2': face_id_2}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        return result.get('isIdentical', False)

    except requests.RequestException as e:
        logger.error(f"Face comparison failed: {e}")
        raise Exception(f"Azure Face API error: {e}")
