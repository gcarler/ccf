"""
Admin user setup/reset utility.
Reads credentials from environment variables with secure defaults.

Required env vars:
  CCF_ADMIN_EMAIL - admin email (default: admin.demo@ccf.local)
  CCF_ADMIN_PASSWORD - admin password (will prompt if not set)
"""

import os
import sys

from backend import models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.management.schema import upgrade_with_optional_bootstrap


def reset_admin():
    admin_email = os.getenv("CCF_ADMIN_EMAIL", "admin.demo@ccf.local")
    admin_password = os.getenv("CCF_ADMIN_PASSWORD")

    if not admin_password:
        print("ERROR: Set CCF_ADMIN_PASSWORD environment variable.", file=sys.stderr)
        print("  Example: set CCF_ADMIN_PASSWORD=your-secure-password", file=sys.stderr)
        sys.exit(1)

    if admin_password == "admin1234":
        print(
            "WARNING: You are using the default insecure password. Please change it.",
            file=sys.stderr,
        )

    upgrade_with_optional_bootstrap()
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.email == admin_email).first()
    if admin:
        print(f"Updating existing admin: {admin.email}")
        admin.password_hash = get_password_hash(admin_password)
        admin.role = "admin"
    else:
        print("Creating new admin...")
        admin = models.User(
            username="Admin CCF",
            email=admin_email,
            password_hash=get_password_hash(admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)

    db.commit()
    print(f"Admin user is ready: {admin_email}")
    db.close()


if __name__ == "__main__":
    reset_admin()
