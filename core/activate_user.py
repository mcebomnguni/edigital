import logging
import qrcode
from io import BytesIO
from django.core.files import File
from django.db import transaction
from .models import SmartID

logger = logging.getLogger(__name__)

def generate_id_number(user):
    """
    Generate a unique ID number based on the user's ID.
    
    :param user: User instance
    :return: A formatted unique ID string
    """
    return f"ID{user.id:06d}"


def generate_qr_code(data):
    """
    Generate a QR code image from provided data.

    :param data: String to encode in QR
    :return: File object containing PNG image
    """
    try:
        qr = qrcode.make(data)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        buffer.seek(0)
        return File(buffer, name='qr_code.png')
    except Exception as e:
        logger.error("QR Code generation failed: %s", str(e))
        raise


@transaction.atomic
def activate_user_account(user):
    """
    Activates the user's account by generating a SmartID and marking the account as activated.

    :param user: User instance to be activated
    :return: True if activated successfully, False if already activated
    :raises: Exception if QR generation or DB operations fail
    """
    if user.is_activated:
        logger.info("User %s is already activated.", user.username)
        return False

    try:
        id_number = generate_id_number(user)
        qr_code_file = generate_qr_code(f"SmartID:{id_number}")

        SmartID.objects.create(
            user=user,
            id_number=id_number,
            qr_code=qr_code_file,
            is_active=True
        )

        user.is_activated = True
        user.save(update_fields=["is_activated"])
        logger.info("Successfully activated user account and created SmartID for %s", user.username)

        return True

    except Exception as e:
        logger.error("Failed to activate user account for %s: %s", user.username, str(e))
        raise
