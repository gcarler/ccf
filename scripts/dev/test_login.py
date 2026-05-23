import logging
import sys

from backend import crud
from backend.auth import (create_access_token, create_refresh_token,
                          verify_password)
from backend.core.config import get_settings
from backend.core.database import SessionLocal

logging.basicConfig(level=logging.DEBUG)

settings = get_settings()

try:
    db = SessionLocal()
    print("DB connection established.")

    user = crud.get_user_by_username(db, "test")
    if not user:
        user = crud.get_user_by_email(db, "test")
    print("User:", user)

    if user:
        print("Verifying password...")
        pw_ok = verify_password("foo", user.password_hash)
        print("verify_password:", pw_ok)

        print("Creating access token...")
        from datetime import timedelta

        payload = {"sub": str(user.id), "role": str(user.role)}
        access_token = create_access_token(
            data=payload,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )
        print("Access token created.")

        print("Creating refresh token...")
        rt = create_refresh_token(db, int(user.id))
        print("Refresh token created.")

except Exception as e:
    import traceback

    traceback.print_exc()
