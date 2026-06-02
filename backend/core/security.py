import base64
import hashlib
import logging as _logging

import bcrypt
from cryptography.fernet import Fernet

from backend.core.config import get_settings

_security_log = _logging.getLogger(__name__)
settings = get_settings()

# Prefer ENCRYPTION_KEY if set; fall back to SECRET_KEY with a warning.
if settings.encryption_key:
    raw_key = settings.encryption_key
else:
    _security_log.warning(
        "ENCRYPTION_KEY not set — falling back to SECRET_KEY for data encryption. "
        "This is insecure in production. Set the ENCRYPTION_KEY environment variable."
    )
    raw_key = settings.secret_key

_key = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode()).digest())
_fernet = Fernet(_key)


def encrypt_data(data: str) -> str:
    """Cifra un string para almacenamiento seguro."""
    if not data:
        return ""
    return _fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Descifra datos para visualización en la API."""
    if not encrypted_data:
        return ""
    try:
        return _fernet.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return "[Error de descifrado - Datos posiblemente corruptos o clave incorrecta]"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")
