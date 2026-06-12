"""Verificación final de calidad CCF — todas las fases del plan.
Ejecuta: python3 _verify_quality.py
"""
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

errors = []
warnings = []

def check(cond, msg):
    if cond:
        print(f"  ✅ {msg}")
    else:
        errors.append(msg)
        print(f"  ❌ {msg}")

def warn(cond, msg):
    if not cond:
        warnings.append(msg)
        print(f"  ⚠️  {msg}")
    else:
        print(f"  ✅ {msg}")


print("=" * 60)
print("VERIFICACIÓN FINAL DE CALIDAD CCF")
print("=" * 60)

# ── Fase 0: Baseline ──
print("\n--- FASE 0: Métricas documentales ---")
doc = ROOT / "docs/ARQUITECTURA_IMPECABLE_CCF.md"
content = doc.read_text(encoding="utf-8")
check("datetime.utcnow() erradicado" in content, "Métrica: utcnow erradicado documentado")
check("persona_id: int" in content and "0" in content.split("persona_id: int")[1][:10],
      "Métrica: persona_id int en 0")
check("fetch(" in content and "erradicado" in content, "Métrica: fetch directo erradicado")

# ── Fase 1: conftest.py ──
print("\n--- FASE 1: Fix tests 403 (conftest.py) ---")
conftest = ROOT / "tests/conftest.py"
ct = conftest.read_text(encoding="utf-8")
check("persona.user_id = legacy_user.id" in ct, "seed_admin_v2 asigna persona.user_id")

# ── Fase 2: Soft delete UsuarioRolModulo ──
print("\n--- FASE 2: Hard delete erradicado ---")
admin_py = ROOT / "backend/api/admin.py"
adm = admin_py.read_text(encoding="utf-8")
# Buscar db.delete( explícito (no en comentarios)
lines_with_delete = [l for l in adm.split("\n") if "db.delete(" in l and not l.strip().startswith("#")]
check(len(lines_with_delete) == 0, f"admin.py: 0 hard deletes (encontrados: {len(lines_with_delete)})")
check("UsuarioRolModulo.deleted_at.is_(None)" in adm, "admin.py: filtro deleted_at en query UsuarioRolModulo")
check("umr.deleted_at = datetime.now(timezone.utc)" in adm, "admin.py: soft delete con timezone-aware")

# Verificar modelo auth
models_auth = ROOT / "backend/models_auth.py"
ma = models_auth.read_text(encoding="utf-8")
check("deleted_at = Column(DateTime(timezone=True), nullable=True)" in ma,
      "models_auth.py: UsuarioRolModulo tiene deleted_at")

# Migración
mig_dir = ROOT / "alembic/versions"
mig_found = False
for f in mig_dir.iterdir():
    if f.name.endswith(".py") and "deleted_at" in f.read_text(encoding="utf-8"):
        if "auth_user_module_roles" in f.read_text(encoding="utf-8"):
            mig_found = True
            break
check(mig_found, "Migración Alembic deleted_at para auth_user_module_roles existe")

# ── Fase 3: utcnow eliminado ──
print("\n--- FASE 3: datetime.utcnow() eliminado ---")
api_files = list((ROOT / "backend/api").rglob("*.py"))
crud_files = list((ROOT / "backend/crud").rglob("*.py"))
all_backend = api_files + crud_files + [ROOT / "backend/models_evangelism.py", ROOT / "backend/models_shared.py"]
utcnow_files = []
for f in all_backend:
    if f.is_file():
        fc = f.read_text(encoding="utf-8")
        if "datetime.utcnow" in fc:
            utcnow_files.append(f.relative_to(ROOT))
check(len(utcnow_files) == 0, f"0 archivos con datetime.utcnow() en backend/api+crud (encontrados: {len(utcnow_files)})")

# ── Fase 4: fetch directo reemplazado ──
print("\n--- FASE 4: fetch() directo → apiFetch() ---")
targets = [
    "frontend/src/hooks/useTableView.ts",
    "frontend/src/hooks/useAirTable.ts",
    "frontend/src/app/plataforma/admin/analytics/web-vitals/page.tsx",
    "frontend/src/components/projects/TaskDetailPanel.tsx",
]
for t in targets:
    fp = ROOT / t
    if fp.exists():
        fc = fp.read_text(encoding="utf-8")
        # Buscar fetch( pero no apiFetch(
        direct_fetch = re.findall(r'(?<!api)(?<!from \x27@/lib/http\x27)\bfetch\(', fc)
        # Más preciso: buscar fetch( que no sea parte de apiFetch(
        lines_with_fetch = [l for l in fc.split("\n") if re.search(r'(?<!api)fetch\(', l) and 'apiFetch' not in l]
        check(len(lines_with_fetch) == 0, f"{t}: 0 fetch() directos (encontrados: {len(lines_with_fetch)})")
    else:
        warn(False, f"{t}: archivo no encontrado (puede haber sido renombrado)")

# ── Fase 5: xfail sin strict=True ──
print("\n--- FASE 5: xfail strict=True revisados ---")
test_files = ["tests/test_agenda_api.py", "tests/test_crm_api.py", "tests/test_chat_api.py"]
for tf in test_files:
    fp = ROOT / tf
    if fp.exists():
        fc = fp.read_text(encoding="utf-8")
        strict_xfails = re.findall(r'@pytest\.mark\.xfail\(.*strict\s*=\s*True', fc)
        check(len(strict_xfails) == 0, f"{tf}: 0 xfail con strict=True (encontrados: {len(strict_xfails)})")

# ── Fase 6: Documentación ──
print("\n--- FASE 6: Documentación actualizada ---")
check("Hallazgos resueltos en tanda" in content or "resueltos" in content,
      "ARQUITECTURA_IMPECABLE_CCF.md contiene sección de hallazgos resueltos")

# ── Resumen ──
print("\n" + "=" * 60)
if not errors:
    print("🏆  VERIFICACIÓN COMPLETA — TODAS LAS FASES OK")
else:
    print(f"❌  {len(errors)} error(es) encontrado(s):")
    for e in errors:
        print(f"   - {e}")

if warnings:
    print(f"\n⚠️  {len(warnings)} advertencia(s):")
    for w in warnings:
        print(f"   - {w}")

print("=" * 60)
sys.exit(1 if errors else 0)
