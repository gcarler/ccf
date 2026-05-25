"""
One-time migration: assign default UserPermission records for any existing users who lack one.

Usage:
    cd /root/ccf
    PYTHONPATH=/root/ccf python backend/management/seed_user_permissions.py
"""

import logging
import sys

sys.path.insert(0, "/root/ccf")

# Import all models to resolve cross-references (User → Enrollment)
import backend.models  # noqa: F401

from backend.core.database import SessionLocal
from backend.core.permissions import DEFAULT_ROLES, normalize_role
from backend.models_identity import User, UserPermission

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed_user_permissions")


def main() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).all()
        total = len(users)
        updated = 0
        skipped = 0

        for user in users:
            existing = (
                db.query(UserPermission)
                .filter(UserPermission.user_id == user.id)
                .first()
            )
            if existing:
                skipped += 1
                continue

            role = normalize_role(str(getattr(user, "role", "")))
            default_perms = {}

            for role_def in DEFAULT_ROLES:
                if role_def["name"].lower() == role:
                    for p in role_def["permissions"]:
                        default_perms[p] = "allow"
                    break

            if not default_perms:
                default_perms = {"profile:manage": "allow"}

            up = UserPermission(user_id=user.id, permissions=default_perms)
            db.add(up)
            updated += 1

        db.commit()
        log.info(
            "Migration complete: %d users total, %d updated, %d skipped (already have permissions)",
            total,
            updated,
            skipped,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
