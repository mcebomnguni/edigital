from typing import Optional

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import (
    User, UserProfile, Biometric, SmartID, VirtualMeeting,
    Document, ActivityLog, InAppNotification
)
from .serializers import (
    UserRegisterSerializer, BiometricSerializer, SmartIDSerializer,
    InAppNotificationSerializer, DocumentRenewalSerializer,
    DocumentRenewalBiometricSerializer, MessageSerializer
)
from .forms import UserRegistrationForm, UserLoginForm, DocumentUploadForm
from .services import activate_user_account, generate_video_token, log_activity
from .face_recognition import detect_face, compare_faces
from .agora import generate_token
from .encryption import hash_document_fields, verify_document

from django.core.exceptions import PermissionDenied
from .models import SmartID

import pyotp
from datetime import datetime


# ----- Helpers -----

def verify_face(user: User, uploaded_file) -> bool:
    """Detect face from uploaded file and compare with user's stored face ID."""
    face_id = detect_face(uploaded_file.path)
    if not face_id:
        return False
    user_profile = UserProfile.objects.filter(user=user).first()
    return user_profile and compare_faces(user_profile.face_id, face_id)


def send_otp_email(user: User) -> None:
    """Generate and send OTP via email."""
    totp = pyotp.TOTP(user.secret_key)
    otp = totp.now()
    send_mail(
        subject='Your OTP Code',
        message=f'Your one-time password is: {otp}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ----- Authentication Views -----

def user_login(request: HttpRequest) -> HttpResponse:
    """Login with password (+biometric in prod); redirects to OTP step."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserLoginForm(request=request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )

        if not user:
            form.add_error(None, 'Invalid username or password')
        elif not settings.DEBUG and 'profile_picture' not in request.FILES:
            form.add_error(None, 'Profile picture is required for biometric authentication')
        elif not settings.DEBUG and not verify_face(user, request.FILES['profile_picture']):
            form.add_error(None, 'Biometric authentication failed')
        else:
            # Store pending user for OTP step; do not call login() yet
            request.session['pre_auth_user_id'] = user.pk
            user.get_or_create_secret_key()
            send_otp_email(user)
            return redirect('verify_otp')

    return render(request, 'core/login.html', {'form': form})


@transaction.atomic
def register(request: HttpRequest) -> HttpResponse:
    """
    User registration with biometric face capture.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserRegistrationForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        user: User = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()

        face_file = request.FILES.get('profile_picture')
        if face_file:
            face_id = detect_face(face_file.path)
            if face_id:
                UserProfile.objects.create(user=user, face_id=face_id)

        login(request, user)
        messages.success(request, 'Registration successful. Welcome!')
        return redirect('dashboard')

    return render(request, 'core/register.html', {'form': form})


def verify_otp(request: HttpRequest) -> HttpResponse:
    """Second factor: verify the TOTP sent by email before granting a session."""
    user_id = request.session.get('pre_auth_user_id')
    if not user_id:
        return redirect('login')

    user = User.objects.filter(pk=user_id).first()
    if not user:
        return redirect('login')

    # In DEBUG, expose current OTP so testers don't need email
    debug_otp = None
    if settings.DEBUG:
        debug_otp = pyotp.TOTP(user.secret_key).now()

    error = None
    if request.method == 'POST':
        otp_entered = request.POST.get('otp', '').strip()
        totp = pyotp.TOTP(user.secret_key)
        if totp.verify(otp_entered, valid_window=1):
            del request.session['pre_auth_user_id']
            login(request, user)
            log_activity(user, 'LOGIN', request.META.get('REMOTE_ADDR'))
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        error = 'Invalid or expired OTP. Please try again.'

    return render(request, 'core/verify_otp.html', {
        'debug_otp': debug_otp,
        'error': error,
    })


# ----- Dashboard & Document Upload -----

@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """
    User dashboard displaying documents and meetings.
    """
    documents = Document.objects.filter(user=request.user)
    meetings = VirtualMeeting.objects.filter(user=request.user)
    context = {
        'user': request.user,
        'documents': documents,
        'meetings': meetings,
    }
    return render(request, 'dashboard.html', context)


@login_required
def upload_document(request: HttpRequest) -> HttpResponse:
    """
    Document upload view for authenticated users.
    """
    form = DocumentUploadForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        document = form.save(commit=False)
        document.user = request.user
        document.save()
        messages.success(request, 'Document uploaded successfully.')
        return redirect('dashboard')

    return render(request, 'core/upload_document.html', {'form': form})


# ----- Admin Actions -----

@login_required
@user_passes_test(lambda u: u.is_admin or u.is_department_official)
def approve_document(request: HttpRequest, document_id: int) -> HttpResponse:
    """
    Approve a document by admin or department official.
    """
    document = get_object_or_404(Document, id=document_id)

    if request.user.is_admin:
        document.is_admin_approved = True
        log_activity(request.user, 'DOCUMENT_ADMIN_APPROVAL', f"Approved document ID {document.id}")
    elif request.user.is_department_official:
        document.is_department_approved = True
        log_activity(request.user, 'DOCUMENT_DEPARTMENT_APPROVAL', f"Approved document ID {document.id}")

    document.save()
    messages.success(request, f'Document #{document.id} approved successfully.')
    return redirect('admin:document_list')


# ----- API Views -----

class PendingUsersView(generics.ListAPIView):
    queryset = User.objects.filter(is_activated=False)
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.IsAdminUser]


class ActivateUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request: HttpRequest, pk: int) -> Response:
        try:
            user = User.objects.get(pk=pk, is_activated=False)
            activate_user_account(user)
            return Response({"message": "User activated successfully."})
        except User.DoesNotExist:
            return Response({"error": "User not found or already activated."}, status=status.HTTP_404_NOT_FOUND)


class InAppNotificationListView(generics.ListAPIView):
    serializer_class = InAppNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InAppNotification.objects.filter(user=self.request.user, seen=False)


class SecureDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, document_id: int) -> HttpResponse:
        document = get_object_or_404(Document, id=document_id, user=request.user)
        if not document.is_fully_approved:
            return JsonResponse({'error': 'Document is not fully approved yet.'}, status=status.HTTP_403_FORBIDDEN)
        return HttpResponse(document.file, content_type="application/pdf")


class DocumentRenewalView(generics.CreateAPIView):
    serializer_class = DocumentRenewalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        log_activity(self.request.user, 'DOCUMENT_RENEWAL', self.request.META.get('REMOTE_ADDR'))
        serializer.save()


class DocumentRenewalWithBiometricView(generics.CreateAPIView):
    serializer_class = DocumentRenewalBiometricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request: HttpRequest, *args, **kwargs) -> Response:
        biometric_data = request.data.get('biometric_data')
        if not biometric_data or not self.verify_biometric(biometric_data):
            return Response({"error": "Biometric verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @staticmethod
    def verify_biometric(data) -> bool:
        # Implement your biometric verification logic here
        # For now, returning True as a placeholder
        return True


# ----- Meeting Views -----

class VirtualMeetingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest) -> Response:
        worker_id = request.data.get('worker_id')
        scheduled_on_str = request.data.get('scheduled_on')

        if not worker_id or not scheduled_on_str:
            return Response({"error": "worker_id and scheduled_on are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            scheduled_on = datetime.strptime(scheduled_on_str, '%Y-%m-%dT%H:%M:%S')
            worker = get_object_or_404(User, id=worker_id, is_active=True)
            token = generate_video_token(request.user.id, worker.id)
            meeting = VirtualMeeting.objects.create(
                user=request.user,
                worker=worker,
                scheduled_on=scheduled_on,
                meeting_token=token
            )
            return Response({
                "meeting_link": f"https://video-platform.com/{token}",
                "meeting_id": meeting.id,
                "scheduled_on": scheduled_on,
            })
        except ValueError:
            return Response({"error": "Invalid date format for scheduled_on."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class AgoraTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest) -> JsonResponse:
        channel_name = request.GET.get("channel")
        if not channel_name:
            return JsonResponse({"error": "Channel name is required."}, status=400)
        user_id = str(request.user.id)
        token = generate_token(channel_name, user_id)
        return JsonResponse({"token": token})


# ----- SmartID View -----

class SmartIDView(generics.RetrieveAPIView):
    serializer_class = SmartIDSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> SmartID:
        user = self.request.user
        if not user.is_activated:
            raise PermissionDenied("Your account has not been activated yet.")
        return get_object_or_404(SmartID, user=user)


# ----- Utility & Reporting -----

class RegisterUserView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]


class BiometricUploadView(generics.CreateAPIView):
    serializer_class = BiometricSerializer
    permission_classes = [permissions.IsAuthenticated]


class SendMessageView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


@login_required
def user_activity_report(request: HttpRequest) -> JsonResponse:
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    logs = ActivityLog.objects.filter(
        action='LOGIN',
        timestamp__range=[start_date, end_date]
    )
    data = {
        'total_logins': logs.count(),
        'unique_users': logs.values('user').distinct().count(),
    }
    return JsonResponse(data)


@login_required
def document_submission_report(request: HttpRequest) -> JsonResponse:
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    documents = Document.objects.filter(issue_date__range=[start_date, end_date])
    data = {
        'total_documents': documents.count(),
        'approved_documents': documents.filter(status='APPROVED').count(),
        'rejected_documents': documents.filter(status='REJECTED').count(),
    }
    return JsonResponse(data)

def contact(request):
    return render(request, 'core/contact.html')

def about(request):
    return render(request, 'core/about.html')

@login_required
def profile(request):
    from .models import Document, DocumentRenewal
    doc_count = Document.objects.filter(user=request.user).count()
    renewal_count = DocumentRenewal.objects.filter(user=request.user).count()
    return render(request, 'core/profile.html', {
        'doc_count': doc_count,
        'renewal_count': renewal_count,
    })

@login_required
def smart_id_page(request):
    user = request.user
    smart_id = SmartID.objects.filter(user=user).first()
    return render(request, 'core/id.html', {'smart_id': smart_id})


@login_required
def renewals(request):
    from .models import DocumentRenewal
    user_renewals = DocumentRenewal.objects.filter(user=request.user).order_by('-renewal_requested_on')
    return render(request, 'core/renewals.html', {'renewals': user_renewals})


@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk, user=request.user)

    # Compute integrity verification flag
    current_hash = hash_document_fields(document)
    is_verified = bool(document.document_hash) and verify_document(
        document.pk,
        f"{document.pk}|{document.user_id}|{document.document_type}"
        f"|{document.name}|{document.issue_date}",
        document.document_hash,
    )

    # Stamp hash if not set yet (e.g. legacy records)
    if not document.document_hash:
        document.document_hash = current_hash
        document.save(update_fields=['document_hash'])
        is_verified = True

    template_map = {
        'id': 'core/doc_id.html',
        'passport': 'core/doc_passport.html',
        'drivers_license': 'core/doc_drivers_license.html',
        'birth_certificate': 'core/doc_birth_certificate.html',
        'marriage_certificate': 'core/doc_marriage_certificate.html',
        'divorce_decree': 'core/document_details.html',
    }
    template = template_map.get(document.document_type, 'core/document_details.html')
    return render(request, template, {
        'document': document,
        'user': request.user,
        'is_verified': is_verified,
        'is_encrypted': True,
    })
