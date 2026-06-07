"""
One-shot provisioning script:
  For every Persona that has an email but no matching auth_user,
  create a Usuario with:
    - same UUID as Persona
    - username derived from email prefix
    - default password: 1234567
    - role: LECTOR (PlatformRole)
    - is_active: true

Run:  python -m backend.management.provision_all_personas
"""

import logging
import uuid as _uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import get_settings
from backend.core.permissions import hash_password
from backend.models_auth import Usuario
from backend.models_kernel import PlatformRoleDefinition, PlatformRole

log = logging.getLogger(__name__)

DEFAULT_PASSWORD = "1234567"


def provision_all(db: Session) -> int:
    """Create auth_users for every Persona with email that lacks one.
    Returns the count of newly created users.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Resolve LECTOR platform role
    lector = db.query(PlatformRoleDefinition).filter(
        PlatformRoleDefinition.role == PlatformRole.LECTOR
    ).first()
    if not lector:
        log.error("No LECTOR PlatformRoleDefinition found in DB. Run seed script first.")
        return 0

    # Find the first sede (required FK for Usuario)
    sede_id = db.execute(
        text("SELECT id FROM sedes ORDER BY nombre ASC LIMIT 1")
    ).scalar()
    if not sede_id:
        log.error("No sedes found in DB.")
        return 0

    # Find personas with email that don't have an auth_user yet
    rows = db.execute(
        text("""
            SELECT p.id, p.email, p.nombre_completo, p.first_name, p.last_name
            FROM personas p
            WHERE (p.email IS NOT NULL AND p.email != '')
              AND NOT EXISTS (SELECT 1 FROM auth_users u WHERE u.id = p.id)
            ORDER BY p.created_at ASC
        """)
    ).fetchall()

    created = 0
    skipped = 0
    for row in rows:
        pid, email, full_name, first_name, last_name = row
        # derive username from email prefix (remove dots for uniqueness)
        email_prefix = email.split("@")[0].lower().replace(".", "_").replace("-", "_")
        base_username = email_prefix[:60]  # username column limit
        username = base_username

        # Avoid username collisions — append suffix if needed
        attempt = 0
        while True:
            existing = db.execute(
                text("SELECT 1 FROM auth_users WHERE username = :u LIMIT 1"),
                {"u": username},
            ).scalar()
            if not existing:
                break
            attempt += 1
            suffix = str(attempt)
            username = f"{base_username[:60 - len(suffix) - 1]}_{suffix}"

        # Also avoid email collisions (shouldn't happen since email is unique)
        existing_email = db.execute(
            text("SELECT 1 FROM auth_users WHERE email = :e LIMIT 1"),
            {"e": email},
        ).scalar()
        if existing_email:
            log.warning("Email %s already in auth_users for persona %s — skipping", email, pid)
            skipped += 1
            continue

        display_name = full_name or f"{first_name or ''} {last_name or ''}".strip() or username

        usuario = Usuario(
            id=pid,
            sede_id=sede_id,
            username=username,
            email=email,
            password_hash=hash_password(DEFAULT_PASSWORD),
            platform_role_id=lector.id,
            is_active=True,
            is_email_verified=False,
        )
        db.add(usuario)

        try:
            db.flush()
            log.info("Created user: %s (%s) — %s", username, email, display_name)
            created += 1
        except Exception as e:
            db.rollback()
            log.error("Failed to create user for %s (%s): %s", email, pid, e)
            skipped += 1
            continue

    db.commit()
    log.info("Done. Created: %d  Skipped: %d", created, skipped)
    db.close()
    return created


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    from backend.core.database import get_db
    db = next(get_db())
    try:
        count = provision_all(db)
        print(f"\n✅ {count} usuarios creados con contraseña predeterminada '{DEFAULT_PASSWORD}'")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
