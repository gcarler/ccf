import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import os
import sys

# Add parent directory to sys.path to allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import models
from backend.core.database import SessionLocal


def seed_missing_data():
    db = SessionLocal()
    try:
        # 1. Verify Admin User
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if admin:
            print(f"Verifying user: {admin.username}")
            admin.is_email_verified = True
            db.commit()
        else:
            print("Admin user not found.")

        # 2. Seed Academy Content Blocks
        academy_hero = (
            db.query(models.PageContent)
            .filter(models.PageContent.page_key == "academy_hero")
            .first()
        )
        if not academy_hero:
            print("Creating academy_hero content...")
            academy_hero = models.PageContent(
                page_key="academy_hero",
                title="Continúa tu Formación",
                content="Bienvenido al portal académico. Aquí podrás avanzar en tu crecimiento espiritual y ministerial con nuestros cursos diseñados para ti.",
            )
            db.add(academy_hero)

        academy_welcome = (
            db.query(models.PageContent)
            .filter(models.PageContent.page_key == "academy_welcome_sub")
            .first()
        )
        if not academy_welcome:
            print("Creating academy_welcome_sub content...")
            academy_welcome = models.PageContent(
                page_key="academy_welcome_sub", title="Tu Ruta de Discipulado"
            )
            db.add(academy_welcome)

        # 3. Seed Support Categories if they don't exist as content (already in support/page.tsx defaults, but good to have in DB)
        support_page = (
            db.query(models.PageContent)
            .filter(models.PageContent.page_key == "support_page")
            .first()
        )
        if not support_page:
            print("Creating support_page content...")
            support_page = models.PageContent(
                page_key="support_page",
                title="Centro de Ayuda",
                content="Estamos aquí para asistirte en cada paso de tu formación.",
            )
            db.add(support_page)

        db.commit()
        print("Seeding completed successfully.")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_missing_data()
