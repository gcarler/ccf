"""Cifrado simétrico y control de acceso confidencial para notas de consejería pastoral.

Protección de datos bajo estándares CCF:
- Cifrado simétrico Fernet / AES-256 en reposo usando la ENCRYPTION_KEY del backend.
- Desencriptación transparente exclusivamente para el pastor asignado o usuarios
  con permiso 'counseling:read_confidential' (o rol pastor/admin) en su sede.
- Retorno de 'Contenido confidencial protegido' para usuarios sin autorización.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.core.permissions import get_user_effective_permissions, normalize_role
from backend.core.security import decrypt_data, encrypt_data
from backend.core.tenant import get_user_sede_id

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from backend import models

logger = logging.getLogger(__name__)

PROTECTED_NOTE_MESSAGE = "Contenido confidencial protegido"


def is_fernet_encrypted(value: str | None) -> bool:
    """Verifica si una cadena tiene el formato de un token cifrado con Fernet."""
    if not value or not isinstance(value, str):
        return False
    # Los tokens Fernet son base64 urlsafe y comienzan con 'gAAAAA'
    if not value.startswith("gAAAAA"):
        return False
    decrypted = decrypt_data(value)
    return not decrypted.startswith("[Error de descifrado")


def encrypt_counseling_notes(notes: str | None) -> str | None:
    """Cifra notas confidenciales usando Fernet. Evita cifrado doble si ya está encriptado."""
    if notes is None or notes == "":
        return notes
    if is_fernet_encrypted(notes):
        return notes
    return encrypt_data(notes)


def decrypt_counseling_notes(notes: str | None) -> str | None:
    """Desencripta notas de consejería si están cifradas; si es texto plano sin cifrar, lo retorna tal cual."""
    if notes is None or notes == "":
        return notes
    if is_fernet_encrypted(notes):
        decrypted = decrypt_data(notes)
        if not decrypted.startswith("[Error de descifrado"):
            return decrypted
    return notes


def has_counseling_confidential_access(
    db: Session,
    user: models.User,
    ticket: models.CounselingTicket,
) -> bool:
    """Evalúa si el usuario autenticado tiene autorización para ver notas confidenciales de un ticket.

    Reglas de acceso canónicas:
    1. El usuario es el pastor o consejero asignado al ticket (pastor_id == user.persona_id o user.id).
    2. El usuario tiene rol 'admin' / 'super administrador' / is_superuser.
    3. El usuario tiene rol 'pastor' en la misma sede del ticket.
    4. El usuario tiene rol con permiso 'counseling:read_confidential' en la sede del ticket.
    """
    if not user:
        return False

    # 1. ¿Es el pastor/consejero asignado directamente al ticket?
    user_id = getattr(user, "id", None)
    user_persona_id = getattr(user, "persona_id", None) or user_id
    ticket_pastor_id = getattr(ticket, "pastor_id", None)

    if ticket_pastor_id is not None:
        if str(ticket_pastor_id) == str(user_id) or str(ticket_pastor_id) == str(user_persona_id):
            return True

    # 2. Rol administrativo bypass (Axioma 2)
    role = normalize_role(getattr(user, "role", ""))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)

    if role in {"admin", "administrador", "super administrador"} or getattr(user, "is_superuser", False):
        return True

    # Sede de la persona del ticket para validación multi-tenant
    user_sede = get_user_sede_id(db, user.id)
    persona = getattr(ticket, "persona", None)
    if not persona and getattr(ticket, "persona_id", None):
        from backend.models_crm import Persona

        persona = db.query(Persona).filter(Persona.id == ticket.persona_id).first()
    persona_sede = getattr(persona, "sede_id", None) if persona else None

    # Si hay sede específica en el ticket, el usuario debe pertenecer a ella
    if persona_sede is not None and user_sede is not None and str(persona_sede) != str(user_sede):
        return False

    # 3. Rol Pastor en la misma sede
    if role == "pastor":
        return True

    # 4. Permiso explícito 'counseling:read_confidential'
    effective_perms = get_user_effective_permissions(db, user)
    if effective_perms.get("counseling:read_confidential") == "allow":
        return True

    return False


def mask_or_decrypt_counseling_notes(
    db: Session,
    user: models.User,
    ticket: models.CounselingTicket,
) -> str | None:
    """Devuelve las notas desencriptadas si el usuario tiene acceso, o 'Contenido confidencial protegido'."""
    if not ticket:
        return None
    raw_notes = getattr(ticket, "notes", None)
    if raw_notes is None or raw_notes == "":
        return raw_notes

    if has_counseling_confidential_access(db, user, ticket):
        return decrypt_counseling_notes(raw_notes)

    return PROTECTED_NOTE_MESSAGE
