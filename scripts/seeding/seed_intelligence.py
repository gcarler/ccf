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

from backend.core.database import SessionLocal
from backend.services.intelligence import IntelligenceMESH


def trigger_intelligence():
    db = SessionLocal()
    try:
        print("🧠 Iniciando Motores de Inteligencia MESH...")
        count = IntelligenceMESH.run_full_analysis(db)
        print(
            f"✅ Análisis completado. Se generaron/actualizaron {count} insights para los agentes."
        )
    except Exception as e:
        print(f"❌ Error en los motores de inteligencia: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    trigger_intelligence()
