from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from documents.models import Document

# Utility functions to reduce duplication
def create_test_user(username='testuser', password='testpassword'):
    return User.objects.create_user(username=username, password=password)

def upload_test_file(filename="test_image.jpg", content=b"file_content", content_type="image/jpeg"):
    return SimpleUploadedFile(filename, content, content_type=content_type)

# Two-Factor Authentication Tests
class TwoFactorAuthenticationTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.client.login(username='testuser', password='testpassword')

    def test_send_otp_success(self):
        response = self.client.get(reverse('send_otp'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('OTP sent', response.content.decode())
    
    def test_send_otp_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('send_otp'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


# Document Upload Flow Tests
class UserDocumentFlowTest(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.client.login(username='testuser', password='testpassword')
        self.file = upload_test_file()

    def test_document_upload(self):
        response = self.client.post(reverse('document_upload'), {
            'document_type': 'ID',
            'name': 'Test Document',
            'document_image': self.file,
            'issue_date': '2023-01-01',
            'expiration_date': '2030-01-01',
            'status': 'Pending'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect on success
        self.assertTrue(Document.objects.filter(user=self.user).exists())


# Document Model Tests
class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.file = upload_test_file()
        self.document = Document.objects.create(
            user=self.user,
            document_type="ID",
            name="Test ID",
            document_image=self.file,
            issue_date="2023-01-01",
            expiration_date="2030-01-01",
            status="Approved"
        )

    def test_document_fields(self):
        self.assertEqual(self.document.document_type, "ID")
        self.assertEqual(self.document.name, "Test ID")
        self.assertTrue(self.document.document_image.name.endswith("test_image.jpg"))
        self.assertEqual(str(self.document), f"{self.document.name} ({self.document.document_type})")


# User Functionality Tests
class UserTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.url = reverse('user_dashboard')

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_dashboard_authenticated_access(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_dashboard.html')

    def test_dashboard_unauthenticated_access(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
