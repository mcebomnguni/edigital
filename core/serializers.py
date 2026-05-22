from rest_framework import serializers
from .models import (
    User, Biometric, SmartID, DocumentRenewal,
    ActivityLog, Message, InAppNotification
)
from .services import verify_biometric  # Ensure this function handles security properly

# -------------------------------
# Messaging and Notification
# -------------------------------

class MessageSerializer(serializers.ModelSerializer):
    """Serializer for sending in-app messages."""
    
    class Meta:
        model = Message
        fields = ['receiver', 'content']


class InAppNotificationSerializer(serializers.ModelSerializer):
    """Serializer for displaying in-app notifications."""
    
    class Meta:
        model = InAppNotification
        fields = ['message', 'created_at']


# -------------------------------
# Document Renewal
# -------------------------------

class DocumentRenewalSerializer(serializers.ModelSerializer):
    """Serializer for requesting document renewal."""
    
    class Meta:
        model = DocumentRenewal
        fields = ['user', 'document_type', 'document_number']


class DocumentRenewalBiometricSerializer(serializers.ModelSerializer):
    """Serializer for document renewal with biometric validation."""
    
    biometric_data = serializers.CharField(write_only=True)

    class Meta:
        model = DocumentRenewal
        fields = ['document_type', 'document_number', 'biometric_data']

    def validate_biometric_data(self, value):
        if not verify_biometric(value):
            raise serializers.ValidationError("Biometric verification failed.")
        return value


# -------------------------------
# Smart ID
# -------------------------------

class SmartIDSerializer(serializers.ModelSerializer):
    """Serializer for SmartID, with dynamic QR code URL support."""
    
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = SmartID
        fields = ['id_number', 'qr_code', 'issued_on', 'qr_code_url']

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None


# -------------------------------
# User Registration
# -------------------------------

class UserRegisterSerializer(serializers.ModelSerializer):
    """Secure registration serializer with password handling and optional parent linking."""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password',
            'date_of_birth', 'is_foreigner', 'parent'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')  # Don't save confirm_password
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            date_of_birth=validated_data.get('date_of_birth'),
            is_foreigner=validated_data.get('is_foreigner', False),
            parent=validated_data.get('parent')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


# -------------------------------
# Biometric
# -------------------------------

class BiometricSerializer(serializers.ModelSerializer):
    """Serializer to manage biometric (face + fingerprint) data."""

    class Meta:
        model = Biometric
        fields = ['face_data', 'fingerprint_data']

    def create(self, validated_data):
        user = self.context['request'].user
        if Biometric.objects.filter(user=user).exists():
            raise serializers.ValidationError("Biometric data already exists for this user.")
        return Biometric.objects.create(user=user, **validated_data)


# -------------------------------
# Activity Log
# -------------------------------

class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer to capture and expose user activity logs."""

    class Meta:
        model = ActivityLog
        fields = [
            'user', 'action', 'timestamp',
            'ip_address', 'additional_info'
        ]
