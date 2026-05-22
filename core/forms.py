from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from .models import Document

# -------------------------------
# Document Upload Form
# -------------------------------
class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'document_type',
            'name',
            'document_image',
            'issue_date',
            'expiration_date',
            'status',
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
        }


# -------------------------------
# User Registration Form
# -------------------------------
class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'}),
        label="Password",
        help_text="Your password must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
        label="Confirm Password"
    )
    profile_picture = forms.ImageField(required=False, label="Profile Picture")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password


# -------------------------------
# User Login Form
# -------------------------------
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


# -------------------------------
# Views (Consider moving to views.py)
# -------------------------------
def upload_document(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.save()
            return redirect('dashboard')
    else:
        form = DocumentUploadForm()

    return render(request, 'upload_document.html', {'form': form})


def dashboard(request):
    documents = Document.objects.filter(user=request.user)
    return render(request, 'dashboard.html', {'documents': documents})
