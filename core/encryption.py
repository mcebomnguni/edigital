import hmac
import hashlib
import base64

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    key = settings.FERNET_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string. Returns a URL-safe base64 token."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by encrypt(). Raises InvalidToken on failure."""
    return _fernet().decrypt(token.encode()).decode()


def sign_document(doc_id: int, content: str) -> str:
    """Return a hex HMAC-SHA256 digest over doc_id + content."""
    key = settings.SECRET_KEY.encode()
    msg = f"{doc_id}:{content}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_document(doc_id: int, content: str, expected_hash: str) -> bool:
    """Constant-time comparison of a stored hash against a freshly computed one."""
    fresh = sign_document(doc_id, content)
    return hmac.compare_digest(fresh, expected_hash)


def hash_document_fields(document) -> str:
    """
    Produce a canonical HMAC over the document's immutable identifying fields.
    Used to detect tampering with the database row.
    """
    payload = (
        f"{document.pk}"
        f"|{document.user_id}"
        f"|{document.document_type}"
        f"|{document.name}"
        f"|{document.issue_date}"
    )
    return sign_document(document.pk, payload)
