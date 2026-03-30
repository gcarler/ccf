import bcrypt
import base64
import os
from cryptography.fernet import Fernet
from backend.core.config import get_settings

settings = get_settings()

# Deterministic key from SECRET_KEY (simplified for MVP, ideally a separate ENCRYPTION_KEY)
_key = base64.urlsafe_b64encode(settings.secret_key.encode().ljust(32)[:32])
_fernet = Fernet(_key)

def encrypt_data(data: str) -> str:
    """Cifra un string para almacenamiento seguro."""
    if not data: return ""
    return _fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Descifra datos para visualización en la API."""
    if not encrypted_data: return ""
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
