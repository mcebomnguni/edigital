from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User  # Make sure this is your custom user model

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def handle_new_user_creation(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New user created: {instance.email}")

        # Optional: Send welcome email
        try:
            send_mail(
                subject="Welcome to eDigital",
                message=f"Hello {instance.first_name}, your account has been created successfully.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=True
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {instance.email}: {e}")
    else:
        logger.info(f"User updated: {instance.email}")
