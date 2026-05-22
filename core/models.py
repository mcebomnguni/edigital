import pyotp

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model extending AbstractUser with additional fields and methods.
    """
    is_admin = models.BooleanField(default=False)
    is_foreigner = models.BooleanField(default=False)
    is_activated = models.BooleanField(
        default=False,
        help_text="Indicates if admin has activated this user."
    )
    date_of_birth = models.DateField(null=True, blank=True)
    secret_key = models.CharField(
        max_length=64,
        blank=True,
        help_text="TOTP secret for 2FA OTP generation."
    )
    otp_verified = models.BooleanField(default=False, help_text="True after OTP verified this session.")
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
        help_text="Optional link to parent user."
    )

    def get_or_create_secret_key(self) -> str:
        if not self.secret_key:
            self.secret_key = pyotp.random_base32()
            self.save(update_fields=['secret_key'])
        return self.secret_key

    def is_minor(self) -> bool:
        """
        Returns True if user is a minor (<18 years old), else False.
        """
        if not self.date_of_birth:
            return False
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        return age < 18

    def clean(self):
        # Prevent user from being their own parent.
        if self.parent and self.parent == self:
            raise ValidationError("User cannot be their own parent.")

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['is_admin']),
            models.Index(fields=['is_activated']),
        ]


class Document(models.Model):
    """
    Represents a document associated with a user.
    """
    DOCUMENT_TYPES = [
        ('id', 'ID Card'),
        ('passport', 'Passport'),
        ('birth_certificate', 'Birth Certificate'),
        ('drivers_license', 'Driver\'s License'),
        ('marriage_certificate', 'Marriage Certificate'),
        ('divorce_decree', 'Divorce Decree'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    name = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    document_image = models.ImageField(upload_to='documents/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    biometric_data = models.JSONField(null=True, blank=True, help_text="Stores biometric metadata.")
    is_admin_approved = models.BooleanField(default=False)
    is_department_approved = models.BooleanField(default=False)
    document_hash = models.CharField(max_length=128, blank=True, help_text="HMAC-SHA256 integrity hash.")

    @property
    def is_fully_approved(self) -> bool:
        """Checks if document has been approved by admin and department."""
        return self.is_admin_approved and self.is_department_approved

    def clean(self):
        if self.expiration_date and self.expiration_date <= self.issue_date:
            raise ValidationError("Expiration date must be after issue date.")

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"

    class Meta:
        ordering = ['issue_date']
        indexes = [
            models.Index(fields=['document_type']),
            models.Index(fields=['is_admin_approved', 'is_department_approved']),
        ]


class ActivityLog(models.Model):
    """
    Logs user actions for auditing.
    """
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('DOCUMENT_RENEWAL', 'Document Renewal'),
        ('MEETING_REQUEST', 'Meeting Request'),
        ('FAILED_BIOMETRIC', 'Failed Biometric Verification'),
        ('FAILED_LOGIN', 'Failed Login'),
        ('DOCUMENT_SUBMISSION', 'Document Submission'),
        ('DOCUMENT_APPROVAL', 'Document Approval'),
        ('MEETING_SCHEDULED', 'Meeting Scheduled'),
        ('MEETING_ENDED', 'Meeting Ended'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    additional_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} performed {self.get_action_display()} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'action']),
        ]


class InAppNotification(models.Model):
    """
    Notifications shown inside the app.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='in_app_notifications')
    message = models.TextField()
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        snippet = (self.message[:20] + '...') if len(self.message) > 20 else self.message
        return f"Notification for {self.user.username}: {snippet}"

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    """
    External notifications via Email, SMS, or App.
    """
    NOTIFICATION_TYPES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('APP', 'App'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)

    def __str__(self):
        return f"{self.get_notification_type_display()} notification for {self.user.username} on {self.sent_at}"

    class Meta:
        ordering = ['-sent_at']


class MeetingLog(models.Model):
    """
    Records meetings between users and workers.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_meetings')
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='worker_meetings')
    room_name = models.CharField(max_length=100)
    start_time = models.DateTimeField(auto_now_add=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    user_verified = models.BooleanField(default=False)
    worker_verified = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField()

    def __str__(self):
        return f"Meeting: {self.user.username} & {self.worker.username} in {self.room_name}"

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'worker']),
        ]


class DocumentRenewal(models.Model):
    """
    Tracks renewal requests for documents.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_renewals')
    document_type = models.CharField(max_length=50)
    document_number = models.CharField(max_length=50)
    renewal_requested_on = models.DateTimeField(auto_now_add=True, db_index=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Renewal request for {self.user.username} - {self.document_type}"

    class Meta:
        ordering = ['-renewal_requested_on']


class VirtualMeeting(models.Model):
    """
    Represents scheduled virtual meetings between a user and worker.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='virtual_meetings')
    worker = models.ForeignKey(User, related_name="worker_virtual_meetings", on_delete=models.CASCADE)
    meeting_token = models.CharField(max_length=255)
    scheduled_on = models.DateTimeField(db_index=True)
    meeting_link = models.URLField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Virtual meeting: {self.user.username} & {self.worker.username} scheduled on {self.scheduled_on}"

    class Meta:
        ordering = ['-scheduled_on']


class Biometric(models.Model):
    """
    Stores biometric data linked to a user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='biometric')
    face_data = models.BinaryField(null=True, blank=True)
    fingerprint_data = models.BinaryField(null=True, blank=True)
    enrolled_on = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Biometric data for {self.user.username}"


class SmartID(models.Model):
    """
    Represents a Smart ID associated with a user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='smart_id')
    id_number = models.CharField(max_length=20, unique=True)
    qr_code = models.ImageField(upload_to='qrcodes/')
    issued_on = models.DateTimeField(auto_now_add=True, db_index=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"SmartID #{self.id_number} for {self.user.username}"


class Message(models.Model):
    """
    Messaging system between users.
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} on {self.sent_at}"

    class Meta:
        ordering = ['-sent_at']


class UserProfile(models.Model):
    """
    Additional profile info for a user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    face_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Worker(models.Model):
    """
    Worker profile linked to User with job info.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    job_title = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    date_joined = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.job_title})"

    class Meta:
        verbose_name = "Worker"
        verbose_name_plural = "Workers"
        indexes = [
            models.Index(fields=['department']),
            models.Index(fields=['active']),
        ]
