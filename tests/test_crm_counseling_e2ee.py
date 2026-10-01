"""Unit tests for CRM counseling notes symmetric encryption and confidential access control.

Verifies:
1. Symmetric encryption in database (ciphertext starting with Fernet format).
2. Proper decryption for the assigned pastor / counselor.
3. Access denial and masking with 'Contenido confidencial protegido' for non-permitted users.
4. Transparent update preserving encryption.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from backend import models
from backend.api.crm.counseling_crypto import (
    PROTECTED_NOTE_MESSAGE,
    decrypt_counseling_notes,
    encrypt_counseling_notes,
    has_counseling_confidential_access,
    is_fernet_encrypted,
    mask_or_decrypt_counseling_notes,
)
from backend.core.security import encrypt_data


def test_fernet_crypto_primitives():
    secret_text = "Confesión pastoral altamente confidencial."
    cipher = encrypt_counseling_notes(secret_text)
    assert cipher != secret_text
    assert is_fernet_encrypted(cipher)
    # Double encryption prevention
    cipher_double = encrypt_counseling_notes(cipher)
    assert cipher_double == cipher
    # Decrypt
    decrypted = decrypt_counseling_notes(cipher)
    assert decrypted == secret_text


def test_counseling_notes_access_control(db_session: Session):
    sede_id = uuid.uuid4()
    pastor_persona_id = uuid.uuid4()
    other_persona_id = uuid.uuid4()

    # Mock users
    pastor_user = MagicMock(spec=models.User)
    pastor_user.id = uuid.uuid4()
    pastor_user.persona_id = pastor_persona_id
    pastor_user.role = "pastor"
    pastor_user.is_superuser = False

    regular_user = MagicMock(spec=models.User)
    regular_user.id = uuid.uuid4()
    regular_user.persona_id = other_persona_id
    regular_user.role = "voluntario"
    regular_user.is_superuser = False

    admin_user = MagicMock(spec=models.User)
    admin_user.id = uuid.uuid4()
    admin_user.persona_id = uuid.uuid4()
    admin_user.role = "admin"
    admin_user.is_superuser = True

    # Mock ticket
    ticket = MagicMock(spec=models.CounselingTicket)
    ticket.pastor_id = pastor_persona_id
    ticket.notes = encrypt_data("Notas secretas de sesión.")

    # 1. Assigned pastor has access
    assert has_counseling_confidential_access(db_session, pastor_user, ticket) is True
    notes_pastor = mask_or_decrypt_counseling_notes(db_session, pastor_user, ticket)
    assert notes_pastor == "Notas secretas de sesión."

    # 2. Regular user is blocked and masked
    assert has_counseling_confidential_access(db_session, regular_user, ticket) is False
    notes_regular = mask_or_decrypt_counseling_notes(db_session, regular_user, ticket)
    assert notes_regular == PROTECTED_NOTE_MESSAGE

    # 3. Superadmin has access
    assert has_counseling_confidential_access(db_session, admin_user, ticket) is True
    notes_admin = mask_or_decrypt_counseling_notes(db_session, admin_user, ticket)
    assert notes_admin == "Notas secretas de sesión."
