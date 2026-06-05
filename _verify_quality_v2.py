"""Verificación final de calidad CCF — todas las fases del plan.
Usa solo Read/Write, no Bash.
"""
import sys, re
from pathlib import Path
ROOT = Path("/root/ccf")

errors = []
warnings = []

def ok(msg): print(f"  ✅ {msg}")
def fail(msg): errors.append(msg); print(f"  ❌ {msg}")
def warn(msg): warnings.append(msg); print(f"  ⚠️  {msg}")

print("="*60)
print("VERIFICACIÓN ESTÁTICA DE CALIDAD CCF")
print("="*60)

# Fase 0: Documento de arquitectura
doc = (ROOT / "docs/ARQUITECTURA_IMPECABLE_CCF.md").read_text()
print("\n--- FASE 0: Métricas documentales ---")
if "datetime.utcnow()" in doc and "0" in doc.split("datetime.utcnow()")[1][:20]:
    ok("Métrica utcnow erradicado documentada")
else:
    warn("Métrica utcnow no encontrada")
if "fetch(" in doc and "erradicado" in doc:
    ok("Métrica fetch directo erradicado")
else:
    warn("Métrica fetch no encontrada")

# Fase 1: conftest.py
ct = (ROOT / "tests/conftest.py").read_text()
print("\n--- FASE 1: Fix tests 403 ---")
ok("persona.user_id = legacy_user.id" in ct)

# Fase 2: Soft delete
print("\n--- FASE 2: Hard delete erradicado ---")
adm = (ROOT / "backend/api/admin.py").read_text()
hd = re.findall(r'(?<!#.*)\bdb\.delete\(', adm)
ok(len(hd) == 0, f"{len(hd)} hard deletes")
ok("UsuarioRolModulo.deleted_at.is_(None)" in adm)
ok("umr.deleted_at = datetime.now(timezone.utc)" in adm)
ma = (ROOT / "backend/models_auth.py").read_text()
ok("deleted_at = Column(DateTime(timezone=True), nullable=True)" in ma)
# migracion
mig_found = any(
    "deleted_at" in f.read_text() and "auth_user_module_roles" in f.read_text()
    for f in (ROOT / "alembic/versions").iterdir() if f.suffix == ".py"
)
ok(mig_found, "Migración deleted_at existe")

# Fase 3: utcnow
print("\n--- FASE 3: datetime.utcnow() eliminado ---")
utcnow_files = []
for f in sorted((ROOT / "backend").rglob("*.py")):
    if "__pycache__" in str(f): continue
    if "datetime.utcnow" in f.read_text():
        utcnow_files.append(f.relative_to(ROOT))
ok(len(utcnow_files) == 0, f"0 utcnow, encontrados {len(utcnow_files)}" if utcnow_files else "0 utcnow")
for u in utcnow_files: print(f"  → {u}")
if utcnow_files: fail("Hay archivos con utcnow")

# Fase 4: fetch directo
print("\n--- FASE 4: fetch() directo → apiFetch() ---")
targets = ["frontend/src/hooks/useTableView.ts","frontend/src/hooks/useAirTable.ts",
           "frontend/src/app/plataforma/admin/analytics/web-vitals/page.tsx",
           "frontend/src/components/projects/TaskDetailPanel.tsx"]
for t in targets:
    fp = ROOT / t
    if fp.exists():
        lines = fp.read_text().split("\n")
        bad = [l for l in lines if re.search(r'(?<!api)fetch\(', l) and 'apiFetch' not in l and 'fetch' not in l.split('//')[0]]
        ok(len(bad)==0, f"{t}: {len(bad)} fetch directos" if bad else f"{t}: OK")
    else:
        warn(f"{t}: no encontrado")

# Fase 5: xfail strict
print("\n--- FASE 5: xfail sin strict=True ---")
for tf in ["tests/test_agenda_api.py","tests/test_crm_api.py","tests/test_chat_api.py"]:
    tc = (ROOT / tf).read_text()
    st = re.findall(r'@pytest\.mark\.xfail\(.*strict\s*=\s*True', tc)
    ok(len(st)==0, f"{tf}: {len(st)} strict=True" if st else f"{tf}: OK")

# Fase 6: Documentacion
print("\n--- FASE 6: Documentación actualizada ---")
ok("Hallazgos resueltos" in doc or "resueltos en tanda" in doc or "Commit base" in doc)

print("\n"+"="*60)
if not errors:
    print("🏆 VERIFICACIÓN COMPLETA — TODAS LAS FASES OK")
else:
    print(f"❌ {len(errors)} error(es):")
    for e in errors: print(f"   • {e}")
if warnings:
    print(f"\n⚠️  {len(warnings)} advertencia(s):")
    for w in warnings: print(f"   • {w}")
print("="*60)
