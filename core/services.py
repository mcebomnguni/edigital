from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from twilio.rest import Client
from django.conf import settings
from .models import ActivityLog, Notification, DocumentRenewal, User
from .utils import send_sms  # Assuming this is your own abstraction over SMS sending

# Use Django settings for credentials — keeps secrets out of source code
TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
TWILIO_API_KEY_SID = settings.TWILIO_API_KEY_SID
TWILIO_API_KEY_SECRET = settings.TWILIO_API_KEY_SECRET
TWILIO_PHONE_NUMBER = settings.TWILIO_PHONE_NUMBER


def activate_user_account(user):
    """
    Activates a user account after document approval or other conditions.
    Sends an activation email.
    """
    user.is_active = True
    user.is_activated = True
    user.save(update_fields=['is_active', 'is_activated'])

    send_mail(
        subject='Account Activation',
        message='Your account has been activated successfully!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def approve_document_and_activate_user(document_renewal_id):
    """
    Approves the document and activates the user's account.
    Sends notification upon approval.
    """
    try:
        renewal = DocumentRenewal.objects.get(id=document_renewal_id)
    except DocumentRenewal.DoesNotExist:
        # Optionally log or raise a custom error
        return None

    if not renewal.is_approved:
        renewal.is_approved = True
        renewal.save(update_fields=['is_approved'])

        activate_user_account(renewal.user)

        send_notification(
            renewal.user,
            f'Your {renewal.document_type} has been approved and your account is now active.',
            notification_type='EMAIL'
        )
    return renewal


def send_notification(user, message, notification_type='APP'):
    """
    Sends notification via email, SMS, or creates in-app notification.

    :param user: User instance to notify
    :param message: Message string
    :param notification_type: 'EMAIL', 'SMS', or 'APP'
    :return: Notification instance
    """
    notification = Notification.objects.create(
        user=user,
        message=message,
        notification_type=notification_type
    )

    if notification_type == 'EMAIL':
        send_mail(
            subject='Notification',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    elif notification_type == 'SMS':
        if user.phone_number:
            send_sms(user.phone_number, message)
        else:
            # Log warning or handle missing phone number
            pass
    # For 'APP', we just create the notification in the DB to be shown in UI

    return notification


def log_activity(user, action, ip_address=None, additional_info=""):
    """
    Logs an activity with optional IP and additional info.
    """
    ActivityLog.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        additional_info=additional_info
    )


def verify_biometric(biometric_data):
    """
    Placeholder for biometric verification logic.

    :param biometric_data: Data to verify
    :return: bool success
    """
    # Integration with actual biometric verification should happen here
    return bool(biometric_data)


def send_sms_reminder(user, renewal):
    """
    Sends SMS reminder for document renewal using Twilio Client.

    :param user: User instance
    :param renewal: DocumentRenewal instance
    """
    if not user.phone_number:
        # Consider logging or raising an error
        return

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        to=user.phone_number,
        from_=TWILIO_PHONE_NUMBER,
        body=f'Your {renewal.document_type} is about to expire. Please renew it soon.',
    )


def send_document_renewal_reminder(user):
    """
    Sends email reminders for documents nearing expiration.

    :param user: User instance
    """
    # Adjust timedelta if needed; here it finds documents older than 30 days from renewal_requested_on
    cutoff_date = timezone.now() - timedelta(days=30)

    renewals = DocumentRenewal.objects.filter(
        user=user,
        is_approved=True,
        renewal_requested_on__lte=cutoff_date
    )

    for renewal in renewals:
        send_mail(
            subject='Document Renewal Reminder',
            message=f'Your {renewal.document_type} is about to expire. Please renew it as soon as possible.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


def generate_video_token(user_id, meeting_id):
    """
    Generates a Twilio Access Token for video communication.

    :param user_id: str or int - user's unique identity
    :param meeting_id: str or int - meeting identifier
    :return: JWT token bytes
    """
    video_grant = VideoGrant(room=f"room_{meeting_id}")
    token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, identity=str(user_id))
    token.add_grant(video_grant)
    return token.to_jwt()
