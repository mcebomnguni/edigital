import qrcode
from io import BytesIO
from django.core.files import File
from django.utils.crypto import get_random_string
from .models import SmartID

def generate_id_number(user):
    # Sample logic for ID number
    return f"ID{user.id:06d}"

def generate_qr_code(data):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')
    return File(buffer, name='qr_code.png')

def activate_user_account(user):
    if user.is_activated:
        return False  # Already activated

    id_number = generate_id_number(user)
    qr_code_file = generate_qr_code(f"SmartID:{id_number}")

    SmartID.objects.create(
        user=user,
        id_number=id_number,
        qr_code=qr_code_file,
        is_active=True,
    )

    user.is_activated = True
    user.save()

    return True
