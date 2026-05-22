import logging
from django.contrib import admin
from .models import (
    User, Biometric, SmartID, DocumentRenewal, ActivityLog, Worker,
    Document, MeetingLog, Notification, Message, InAppNotification
)
from .services import activate_user_account

logger = logging.getLogger(__name__)


@admin.action(description="Activate selected users and generate SmartID")
def activate_users(modeladmin, request, queryset):
    """
    Custom admin action to activate selected users.
    """
    success_count = 0
    for user in queryset:
        try:
            if activate_user_account(user):
                success_count += 1
        except Exception as e:
            logger.error("Failed to activate user %s: %s", user.username, str(e))

    modeladmin.message_user(request, f"{success_count} user(s) activated successfully.")


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_activated', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active', 'is_activated')
    actions = [activate_users]
    ordering = ('username',)


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'department', 'active', 'date_joined')
    search_fields = ('user__username', 'job_title', 'department')
    list_filter = ('active', 'department')
    ordering = ('-date_joined',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'name', 'status', 'issue_date', 'expiration_date')
    search_fields = ('user__username', 'document_type', 'name')
    list_filter = ('document_type', 'status')
    ordering = ('-issue_date',)


@admin.register(MeetingLog)
class MeetingLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'worker', 'room_name', 'start_time', 'end_time')
    search_fields = ('user__username', 'worker__username', 'room_name')
    list_filter = ('start_time', 'end_time')
    ordering = ('-start_time',)


@admin.register(DocumentRenewal)
class DocumentRenewalAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'document_number', 'renewal_requested_on', 'is_approved')
    search_fields = ('user__username', 'document_type', 'document_number')
    list_filter = ('is_approved', 'renewal_requested_on')
    ordering = ('-renewal_requested_on',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_address')
    search_fields = ('user__username', 'action')
    list_filter = ('action', 'timestamp')
    ordering = ('-timestamp',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'sent_at')
    search_fields = ('user__username', 'notification_type')
    list_filter = ('notification_type', 'sent_at')
    ordering = ('-sent_at',)


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'seen', 'created_at')
    search_fields = ('user__username', 'message')
    list_filter = ('seen', 'created_at')
    ordering = ('-created_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'sent_at', 'read')
    search_fields = ('sender__username', 'receiver__username', 'content')
    list_filter = ('read', 'sent_at')
    ordering = ('-sent_at',)


@admin.register(Biometric)
class BiometricAdmin(admin.ModelAdmin):
    list_display = ('user', 'enrolled_on')
    search_fields = ('user__username',)
    ordering = ('-enrolled_on',)


@admin.register(SmartID)
class SmartIDAdmin(admin.ModelAdmin):
    list_display = ('user', 'id_number', 'issued_on', 'is_active')
    search_fields = ('user__username', 'id_number')
    list_filter = ('is_active', 'issued_on')
    ordering = ('-issued_on',)
