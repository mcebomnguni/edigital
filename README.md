# eDigital — South African Digital Identity Platform

A Django-based digital identity and document management system that allows South African citizens to securely store, view, and manage their government-issued documents online.

---

## Features

- **Digital Document Vault** — Store and view ID cards, passports, driver's licences, birth certificates, and marriage certificates
- **Smart ID Card Viewer** — Realistic 3D flip-card rendering matching the SA Department of Home Affairs design
- **Two-Factor Authentication** — TOTP-based OTP sent via email on every login
- **Document Integrity Verification** — HMAC-SHA256 signing on all documents; tamper detection on every access
- **Fernet Encryption** — Symmetric encryption for sensitive document fields at rest
- **Biometric Authentication** — Face recognition using stored face ID (production mode)
- **Document Renewals** — Submit and track renewal requests
- **Virtual Meetings** — Schedule video appointments with department workers (Agora-powered)
- **JWT API** — REST API with JWT token authentication for external integrations
- **Admin Panel** — Approve/reject documents and activate new user accounts

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2.1 |
| API | Django REST Framework + SimpleJWT |
| Auth | pyotp (TOTP 2FA), bcrypt, custom biometric |
| Encryption | Fernet (cryptography), HMAC-SHA256 |
| Task Queue | Celery |
| Video | Agora RTC |
| Notifications | Twilio |
| Database | SQLite (dev) / PostgreSQL (prod) |

---

## Getting Started

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/mcebomnguni/edigital.git
cd edigital

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install bcrypt cryptography pyotp
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
FERNET_KEY=your-fernet-key
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your@gmail.com
AGORA_APP_ID=your-agora-app-id
AGORA_APP_CERTIFICATE=your-agora-certificate
```

Generate a Fernet key:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Database Setup

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Run the Development Server

```bash
# Windows (--noreload required on Python 3.13)
python manage.py runserver --noreload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Project Structure

```
eDigital/
├── civica_core/         # Django project settings & root URLs
│   └── settings.py
├── core/                # Main application
│   ├── models.py        # User, Document, SmartID, VirtualMeeting, etc.
│   ├── views.py         # All views (auth, documents, API)
│   ├── urls.py          # URL routing
│   ├── forms.py         # Registration & login forms
│   ├── serializers.py   # DRF serializers
│   ├── encryption.py    # Fernet encryption + HMAC document signing
│   ├── face_recognition.py  # Biometric face detection
│   ├── agora.py         # Agora video token generation
│   ├── services.py      # Business logic (activate user, video token)
│   └── templates/core/  # All HTML templates
├── static/              # CSS, JS, images
├── manage.py
└── requirements.txt
```

---

## Supported Document Types

| Document | Template |
|---|---|
| Smart ID Card | 3D flip card — green/gold SA DHA design |
| Passport | Bio-data page with MRZ zone |
| Driver's Licence | 3D flip card — Road Traffic Act format |
| Birth Certificate | A4 DHA double-border format |
| Marriage Certificate | A4 formal serif format |
| Unabridged Documents | Standard detail view |

---

## Authentication Flow

1. User submits username + password
2. Credentials verified; `pre_auth_user_id` stored in session
3. OTP generated and sent to registered email address
4. User enters OTP on the `/verify-otp/` page
5. On success, full Django session is granted
6. All sessions expire after 30 minutes of inactivity

> In `DEBUG=True` mode, the current OTP is displayed on screen so you can log in without email.

---

## Document Security

Every document is protected by two mechanisms:

- **Encryption** — Sensitive fields are encrypted with Fernet symmetric encryption using the `FERNET_KEY` environment variable
- **Integrity hash** — An HMAC-SHA256 signature is computed over `pk|user_id|document_type|name|issue_date` and stored in `document_hash`. This is verified on every document view. A tampered record shows as **Unverified**.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/token/refresh/` | Refresh JWT token |
| POST | `/api/register/` | Register a new user |
| GET | `/api/smart-id/` | Get authenticated user's Smart ID data |
| POST | `/api/biometric/` | Upload biometric face data |
| POST | `/api/renew-document/` | Submit document renewal |
| GET | `/api/agora/token/?channel=X` | Get Agora RTC token |
| POST | `/api/create-meeting/` | Schedule virtual meeting |

---

## Security Settings

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1800          # 30-minute session timeout
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True          # (production only)
SESSION_COOKIE_SECURE = True       # (production only)
```

---

## License

This project is for educational and demonstration purposes.

---

&copy; 2026 eDigital. All Rights Reserved.
