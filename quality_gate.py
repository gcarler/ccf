
import os
import sys
import subprocess
import logging
from pathlib import Path
from sqlalchemy import text
from backend.core.database import SessionLocal

REPORT_PATH = Path("test_artifacts") / "quality_report.log"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configuración de logging para reporte de calidad
# Forzar UTF-8 en stdout si es posible
stdout_encoding = getattr(sys.stdout, "encoding", None) or ""
if stdout_encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(REPORT_PATH, mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger("QualityGate")

def run_step(name, command, cwd=None):
    logger.info(f"--- INICIANDO: {name} ---")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            logger.info(f"✅ {name} PASÓ.")
            return True
        else:
            logger.error(f"❌ {name} FALLÓ.")
            logger.error(f"Salida de error:\n{result.stdout}\n{result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error crítico ejecutando {name}: {e}")
        return False

def check_db_indices():
    logger.info("--- VERIFICANDO ÍNDICES DE BASE DE DATOS ---")
    db = SessionLocal()
    expected_indices = [
        "idx_donations_status", "idx_donations_ref", 
        "idx_audit_resource", "idx_tasks_status",
        "idx_user_reminders_user_id"
    ]
    all_passed = True
    try:
        for idx in expected_indices:
            res = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{idx}'"))
            if res.fetchone():
                logger.info(f"✅ Índice {idx} verificado.")
            else:
                logger.warning(f"⚠️ Índice {idx} NO ENCONTRADO.")
                all_passed = False
        return all_passed
    finally:
        db.close()

def check_new_views():
    logger.info("--- VERIFICANDO EXISTENCIA DE NUEVAS VISTAS ---")
    critical_paths = [
        "frontend/src/app/academy/courses/[id]/page.tsx",
        "frontend/src/app/admin/donations/page.tsx",
        "frontend/src/app/crm/pipeline/[id]/page.tsx",
        "frontend/src/app/tasks/[id]/page.tsx",
        "frontend/src/app/whiteboard/[id]/page.tsx"
    ]
    all_passed = True
    for path in critical_paths:
        if os.path.exists(path):
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
        ("Backend Core Tests", "python -m pytest tests/test_smoke.py tests/test_auth.py"),
        ("Backend Domain Tests", "python -m pytest tests/test_academy_domain.py tests/test_crm_domain.py"),
        ("Frontend Typecheck", "npm run typecheck", "frontend"),
    ]
    
    overall_success = True
    
    # 1. Pruebas Automatizadas
    for name, cmd, *cwd in steps:
        work_dir = cwd[0] if cwd else None
        if not run_step(name, cmd, work_dir):
            overall_success = False

    # 2. Verificaciones Estructurales
    if not check_db_indices():
        overall_success = False
        
    if not check_new_views():
        overall_success = False

    # 3. Verificación de Motor de Automatización
    if not run_step("Automation Engine Load", 'set PYTHONPATH=. && python backend/services/automation_engine.py'):
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
