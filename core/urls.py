from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    # Authentication and User Pages
    path('', views.user_login, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_document, name='upload_document'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    path('id/', views.smart_id_page, name='id'),
    path('renewals/', views.renewals, name='renewals'),
    path('documents/<int:pk>/', views.document_detail, name='document_detail'),


    # Admin Panel
    path('admin/pending-users/', views.PendingUsersView.as_view(), name='admin_pending_users'),
    path('admin/activate-user/<int:pk>/', views.ActivateUserView.as_view(), name='admin_activate_user'),
    path('admin/approve-document/<int:document_id>/', views.approve_document, name='admin_approve_document'),

    # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='api_token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),

    # Biometric & Smart ID
    path('api/biometric/', views.BiometricUploadView.as_view(), name='api_biometric_upload'),
    path('api/smart-id/', views.SmartIDView.as_view(), name='api_smart_id'),

    # Document Renewals
    path('api/renew-document/', views.DocumentRenewalView.as_view(), name='api_document_renewal'),
    path('api/renew-document/biometric/', views.DocumentRenewalWithBiometricView.as_view(), name='api_document_renewal_biometric'),

    # Virtual Meetings (Agora)
    path('api/agora/token/', views.AgoraTokenView.as_view(), name='api_agora_token'),
    path('api/create-meeting/', views.VirtualMeetingCreateView.as_view(), name='api_create_meeting'),

    # API Registration
    path('api/register/', views.RegisterUserView.as_view(), name='api_register'),
]
