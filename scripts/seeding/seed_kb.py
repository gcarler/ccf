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

from backend import crud, models, schemas
from backend.core.database import SessionLocal


def seed_kb():
    db = SessionLocal()
    try:
        entries = [
            {
                "title": "Doctrina de la Biblia",
                "content": "Creemos que la Biblia es la palabra de Dios, inspirada e infalible. Es nuestra única regla de fe y conducta.",
                "category": "Doctrine",
            },
            {
                "title": "Manual de Líderes de Casa de Bendición",
                "content": "Un líder de Casa de Bendición debe velar por el crecimiento espiritual de sus miembros, reportar asistencia semanalmente y fomentar la comunión.",
                "category": "Manual",
            },
            {
                "title": "Política de Privacidad de Datos",
                "content": "En CCF protegemos tus datos personales según la ley vigente. Nunca compartimos información sensible con terceros sin consentimiento.",
                "category": "Policy",
            },
        ]
        for e in entries:
            crud.create_kb_entry(db, **e)
        print("Knowledge Base seeded!")
    except Exception as e:
        print(f"Error seeding KB: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_kb()
