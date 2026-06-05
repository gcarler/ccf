"""Quality Gate - versión directa sin subprocess.
Ejecuta pytest inline e importa los módulos para verificación estructural.
"""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_PATH = ROOT / "test_artifacts" / "quality_report.log"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(REPORT_PATH, mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("QualityGate")


def run_pytest(test_files: list[str]) -> bool:
    """Ejecuta pytest directamente importando el módulo."""
    import pytest
    logger.info(f"Ejecutando pytest con: {test_files}")
    args = ["-q", "-o", "addopts=", "--tb=short"] + test_files
    rc = pytest.main(args)
    ok = rc == 0 or rc == pytest.ExitCode.OK
    if ok:
        logger.info(f"✅ {test_files} PASÓ.")
    else:
        logger.error(f"❌ {test_files} FALLÓ (código {rc}).")
    return ok


def check_db_indices():
    from sqlalchemy import text
    from backend.core.database import SessionLocal
    logger.info("--- VERIFICANDO ÍNDICES DE BASE DE DATOS ---")
    db = SessionLocal()
    expected_index_groups = {
        "donations_status": {"ix_donations_status", "idx_donations_status"},
        "donations_sede": {"ix_donations_sede_id"},
        "audit_resource": {"ix_admin_audit_logs_resource_type", "idx_audit_resource"},
        "crm_tasks_status": {
            "ix_crm_tasks_status", "ix_consolidation_tasks_status",
            "ix_project_tasks_status", "idx_tasks_status",
        },
        "user_reminders_user": {
            "ix_user_reminders_user_id", "idx_auth_reminders_user", "idx_user_reminders_user_id",
        },
    }
    all_passed = True
    try:
        rows = db.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
        existing_indices = {row[0] for row in rows}
        for logical_name, allowed_names in expected_index_groups.items():
            found = sorted(existing_indices & allowed_names)
            if found:
                logger.info(f"✅ Índice lógico {logical_name} verificado vía {', '.join(found)}.")
            else:
                logger.warning(f"⚠️ Índice lógico {logical_name} NO ENCONTRADO. Esperado uno de: {', '.join(sorted(allowed_names))}")
                all_passed = False
    finally:
        db.close()
    return all_passed


def check_new_views():
    logger.info("--- VERIFICANDO EXISTENCIA DE VISTAS ---")
    critical_paths = [
        "frontend/src/app/plataforma/academy/courses/[id]/page.tsx",
        "frontend/src/app/plataforma/admin/donations/page.tsx",
        "frontend/src/app/plataforma/crm/pipeline/[id]/page.tsx",
        "frontend/src/app/plataforma/tasks/[id]/page.tsx",
        "frontend/src/app/plataforma/whiteboard/[id]/page.tsx",
    ]
    all_passed = True
    for p in critical_paths:
        if (ROOT / p).exists():
            logger.info(f"✅ Vista {p} existe.")
        else:
            logger.error(f"❌ Vista {p} NO ENCONTRADA.")
            all_passed = False
    return all_passed


def check_automation_engine():
    logger.info("--- VERIFICANDO MOTOR DE AUTOMATIZACIÓN ---")
    try:
        import py_compile
        py_compile.compile(str(ROOT / "backend/services/automation_engine.py"), doraise=True)
        logger.info("✅ Automation Engine compila correctamente.")
        return True
    except py_compile.PyCompileError as e:
        logger.error(f"❌ Automation Engine NO compila: {e}")
        return False


def check_rules_violations():
    """Verifica reglas CCF: 0 utcnow, soft deletes ok."""
    logger.info("--- VERIFICANDO REGLAS CCF ---")
    ok = True

    # 0 utcnow
    matches = list(ROOT.rglob("*.py"))
    utcnow = []
    for m in matches:
        if "node_modules" in str(m) or "__pycache__" in str(m) or "venv" in str(m):
            continue
        content = m.read_text()
        if "datetime.utcnow" in content or "datetime.datetime.utcnow" in content:
            utcnow.append(m)

    if utcnow:
        logger.error(f"❌ {len(utcnow)} archivos con datetime.utcnow(): {[str(p.relative_to(ROOT)) for p in utcnow]}")
        ok = False
    else:
        logger.info("✅ 0 usos de datetime.utcnow() en backend.")

    # Verificar que admin.py usa soft delete
    admin_py = ROOT / "backend/api/admin.py"
    if admin_py.exists():
        content = admin_py.read_text()
        if "deleted_at" in content and "db.delete" not in content:
            logger.info("✅ admin.py: soft delete implementado, sin hard deletes.")
        elif "db.delete" in content:
            logger.warning("⚠️ admin.py aún contiene db.delete() — revisar.")
        else:
            logger.info("✅ admin.py sin hard deletes detectados.")

    return ok


def main():
    logger.info("====================================================")
    logger.info("   CCF PLATFORM - QUALITY GATE v1.0 (direct)")
    logger.info("====================================================")

    overall = True

    # 1. Tests
    if not run_pytest(["tests/test_smoke.py", "tests/test_auth.py"]):
        overall = False
    if not run_pytest(["tests/test_academy_domain.py", "tests/test_crm_domain.py"]):
        overall = False
    if not run_pytest(["tests/test_structural_contracts.py", "tests/test_reglas_plataforma.py"]):
        overall = False

    # 2. Verificaciones estructurales
    if not check_db_indices():
        overall = False
    if not check_new_views():
        overall = False
    if not check_automation_engine():
        overall = False

    # 3. Reglas CCF adicionales
    if not check_rules_violations():
        overall = False

    logger.info("====================================================")
    if overall:
        logger.info("🏆 RESULTADO FINAL: CALIDAD TOTAL ALCANZADA")
    else:
        logger.info("⚠️ RESULTADO FINAL: SE REQUIEREN CORRECCIONES")
    logger.info("====================================================")
    return overall


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
