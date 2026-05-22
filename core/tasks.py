from celery import shared_task
import logging
from .services import send_document_renewal_reminder, send_sms_reminder
from .models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_document_renewals(self):
    """
    Celery task to send document renewal reminders (email + SMS)
    to all activated users. Retries on failure and logs results.
    """
    try:
        users = User.objects.filter(is_activated=True)

        if not users.exists():
            logger.info("No activated users found for document renewal reminders.")
            return "No activated users to notify."

        for user in users:
            try:
                # Email reminder
                send_document_renewal_reminder(user)
                logger.info(f"Email reminder sent to {user.email}")

                # SMS reminder
                send_sms_reminder(user)
                logger.info(f"SMS reminder sent to {user.username}")
            except Exception as user_error:
                logger.warning(f"Reminder failed for user {user.username}: {str(user_error)}")

        return f"Reminders processed for {users.count()} users."

    except Exception as exc:
        logger.error(f"Failed to execute send_document_renewals task: {str(exc)}")
        self.retry(exc=exc)
