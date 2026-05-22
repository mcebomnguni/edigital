import logging
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from twilio.rest import Client
from cryptography.fernet import Fernet, InvalidToken
import pyotp

logger = logging.getLogger(__name__)

# IMPORTANT:
# Load Fernet key from Django settings as bytes.
FERNET_KEY = getattr(settings, 'FERNET_KEY', None)
if not FERNET_KEY:
    raise ValueError("FERNET_KEY must be set in Django settings securely!")

# Fernet expects bytes, so encode the string key
cipher = Fernet(FERNET_KEY.encode())


def encrypt_document(file_content: bytes) -> bytes:
    """
    Encrypts the binary content of a document using Fernet symmetric encryption.

    Args:
        file_content (bytes): Raw binary content of the document.

    Returns:
        bytes: Encrypted binary data.
    """
    try:
        encrypted = cipher.encrypt(file_content)
        return encrypted
    except Exception as e:
        logger.error(f"Document encryption failed: {e}")
        raise


def decrypt_document(encrypted_content: bytes) -> bytes:
    """
    Decrypts previously encrypted document content.

    Args:
        encrypted_content (bytes): Encrypted document content.

    Returns:
        bytes: Decrypted original document content.
    """
    try:
        decrypted = cipher.decrypt(encrypted_content)
        return decrypted
    except InvalidToken:
        logger.warning("Invalid encryption token during document decryption.")
        raise
    except Exception as e:
        logger.error(f"Document decryption failed: {e}")
        raise


def send_sms(to: str, body: str) -> str:
    """
    Sends an SMS message using Twilio API.

    Args:
        to (str): Recipient phone number (E.164 format recommended).
        body (str): SMS message body.

    Returns:
        str: Twilio message SID on success.

    Raises:
        Exception: On failure to send SMS.
    """
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to
        )
        logger.info(f"SMS sent to {to} with SID {message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"Failed to send SMS to {to}: {e}")
        raise


def send_verification_email(subject: str, message: str, recipient_list: list, html_message: str = None) -> None:
    """
    Sends an email using Django's email backend.

    Args:
        subject (str): Email subject.
        message (str): Plain text email body.
        recipient_list (list): List of recipient email addresses.
        html_message (str, optional): HTML formatted email body.

    Raises:
        Exception: On failure to send email.
    """
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        if html_message:
            email.content_subtype = 'html'
            email.body = html_message

        email.send(fail_silently=False)
        logger.info(f"Verification email sent to: {', '.join(recipient_list)}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {recipient_list}: {e}")
        raise


def generate_totp(secret_key: str, interval: int = 30) -> str:
    """
    Generate a time-based one-time password (TOTP) using pyotp.

    Args:
        secret_key (str): Base32 encoded secret key for TOTP.
        interval (int, optional): Time step in seconds. Defaults to 30.

    Returns:
        str: Current TOTP code.
    """
    totp = pyotp.TOTP(secret_key, interval=interval)
    return totp.now()
