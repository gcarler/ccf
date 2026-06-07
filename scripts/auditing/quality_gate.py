import logging
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

REPORT_PATH = Path("test_artifacts") / "quality_report.log"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
PYTHON = sys.executable or "python3"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.database import SessionLocal  # noqa: E402

# Configuración de logging para reporte de calidad
# Forzar UTF-8 en stdout si es posible
stdout_encoding = getattr(sys.stdout, "encoding", None) or ""
if stdout_encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(REPORT_PATH, mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("QualityGate")

DEFAULT_STEP_TIMEOUT_SECONDS = int(os.getenv("QUALITY_GATE_STEP_TIMEOUT", "120"))
FRONTEND_STEP_TIMEOUT_SECONDS = int(os.getenv("QUALITY_GATE_FRONTEND_TIMEOUT", "240"))


def run_step(name, command, cwd=None, timeout_seconds=None):
    logger.info(f"--- INICIANDO: {name} ---")
    timeout = timeout_seconds or DEFAULT_STEP_TIMEOUT_SECONDS
    try:
        result = subprocess.run(
            command,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode == 0:
            logger.info(f"✅ {name} PASÓ.")
            return True
        else:
            logger.error(f"❌ {name} FALLÓ.")
            logger.error(f"Salida de error:\n{result.stdout}\n{result.stderr}")
            return False
    except subprocess.TimeoutExpired as e:
        logger.error(f"❌ {name} AGOTÓ TIEMPO ({timeout}s).")
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        logger.error(f"Salida parcial:\n{stdout}\n{stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Error crítico ejecutando {name}: {e}")
        return False


def check_db_indices():
    logger.info("--- VERIFICANDO ÍNDICES DE BASE DE DATOS ---")
    db = SessionLocal()
    expected_index_groups = {
        "donations_status": {"ix_donations_status", "idx_donations_status"},
        "donations_sede": {"ix_donations_sede_id"},
        "audit_resource": {
            "ix_admin_audit_logs_resource_type",
            "idx_audit_resource",
        },
        "crm_tasks_status": {
            "ix_crm_tasks_status",
            "ix_consolidation_tasks_status",
            "ix_project_tasks_status",
            "idx_tasks_status",
        },
        "user_reminders_user": {
            "ix_user_reminders_user_id",
            "idx_auth_reminders_user",
            "idx_user_reminders_user_id",
        },
    }
    all_passed = True
    try:
        dialect_name = db.bind.dialect.name
        if dialect_name == "postgresql":
            rows = db.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"
                )
            )
        else:
            rows = db.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))

        existing_indices = {row[0] for row in rows}

        for logical_name, allowed_names in expected_index_groups.items():
            found = sorted(existing_indices & allowed_names)
            if found:
                logger.info(
                    "✅ Índice lógico %s verificado vía %s.",
                    logical_name,
                    ", ".join(found),
                )
            else:
                logger.warning(
                    "⚠️ Índice lógico %s NO ENCONTRADO. Esperado uno de: %s",
                    logical_name,
                    ", ".join(sorted(allowed_names)),
                )
                all_passed = False
        return all_passed
    except Exception as exc:
        logger.error("❌ No se pudieron verificar índices de DB: %s", exc)
        return False
    finally:
        db.close()


def check_new_views():
    logger.info("--- VERIFICANDO EXISTENCIA DE NUEVAS VISTAS ---")
    critical_paths = [
        "frontend/src/app/plataforma/academy/courses/[id]/page.tsx",
        "frontend/src/app/plataforma/admin/donations/page.tsx",
        "frontend/src/app/plataforma/crm/pipeline/[id]/page.tsx",
        "frontend/src/app/plataforma/tasks/[id]/page.tsx",
        "frontend/src/app/plataforma/whiteboard/[id]/page.tsx",
    ]
    all_passed = True
    for path in critical_paths:
        if (ROOT / path).exists():
            logger.info(f"✅ Vista {path} existe.")
        else:
            logger.error(f"❌ Vista {path} NO ENCONTRADA.")
            all_passed = False
    return all_passed


def main():
    logger.info("====================================================")
    logger.info("   CCF PLATFORM - QUALITY GATE v1.0")
    logger.info("====================================================")

    steps = [
        (
            "Backend Core Tests",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_smoke.py",
                "tests/test_auth.py",
            ],
        ),
        (
            "Backend Domain Tests",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_academy_domain.py",
                "tests/test_crm_domain.py",
            ],
        ),
        (
            "Architecture Rule Tests",
            [
                PYTHON,
                "-m",
                "pytest",
                "-q",
                "-o",
                "addopts=",
                "tests/test_structural_contracts.py",
                "tests/test_reglas_plataforma.py",
            ],
        ),
        (
            "Frontend Typecheck",
            ["npm", "run", "typecheck"],
            ROOT / "frontend",
            FRONTEND_STEP_TIMEOUT_SECONDS,
        ),
    ]

    overall_success = True

    # 1. Pruebas Automatizadas
    for name, cmd, *extra in steps:
        work_dir = extra[0] if extra else None
        timeout = extra[1] if len(extra) > 1 else None
        if not run_step(name, cmd, work_dir, timeout):
            overall_success = False

    # 2. Verificaciones Estructurales
    if not check_db_indices():
        overall_success = False

    if not check_new_views():
        overall_success = False

    # 3. Verificación de Motor de Automatización
    if not run_step(
        "Automation Engine Load",
        [PYTHON, "-m", "py_compile", "backend/services/automation_engine.py"],
    ):
        overall_success = False

    logger.info("====================================================")
    if overall_success:
        logger.info("🏆 RESULTADO FINAL: CALIDAD TOTAL ALCANZADA")
        logger.info("La plataforma está lista para el despliegue.")
    else:
        logger.info("⚠️ RESULTADO FINAL: SE REQUIEREN CORRECCIONES")
        logger.info(f"Revisa los errores en {REPORT_PATH.as_posix()}")
    logger.info("====================================================")

    if not overall_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
