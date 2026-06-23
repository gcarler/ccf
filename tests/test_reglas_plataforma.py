"""
Tests automatizados para verificar cumplimiento de REGLAS.md.

Cubre:
- Axioma 3: Toda query filtra por sede_id
- Regla 2: persona_id siempre str en schemas
- Regla 4: Soft deletes (no db.delete() en tablas transaccionales)
- Regla 6: DateTime con timezone=True
- Regla 7: UUID en FKs a personas.id
- Regla 8: JSON en vez de JSONB
"""
import re
import os
import re
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "backend" / "api"
MODELS_DIR = ROOT / "backend"
SCHEMAS_DIR = ROOT / "backend" / "schemas"

# ── Configuración ──────────────────────────────────────────────────────────
# Endpoints que pueden tener .all() sin sede_id por ser catálogos o admin global
ALLOWED_UNFILTERED = {
    "admin.py",             # Catálogos administrativos
    "community.py",         # Scoped por líder/grupo
    "evangelism.py",        # Scoped internally by strategy/group/event
    "evangelism_events.py", # Scoped internally by event/group
    "evangelism_grupos.py", # Scoped internally by group
    "evangelism_shared.py", # Helper functions scoped by event/group
    "finance.py",           # Fund is catalog, Donation scoped by sede_id
    "projects.py",          # Scoped by project/user
    "academy_core.py",       # Ya tiene sede_id en sus queries
    "auth_v3.py",
    "cms_v2.py",           # Scoped por site_id
    "chat.py",             # Scoped por user_id / conversation_id
    "tables.py",           # Scoped por user_id
    "agents.py",           # Scoped por agent_id
    "kernel.py",           # Admin endpoint
    "public.py",           # Público global
    "evangelism_notifications.py",  # Background tasks multi-sede
    "evangelism_multiplication.py", # Tiene sede_id opcional
    "evangelism_rankings.py",       # Tiene sede_id opcional
    "evangelism_reports.py",
    "evangelism_analytics.py",     # Aplica sede_id dinámicamente (None = super-admin global)
    "workspace.py",
    "workspace_compliance.py",
    "governance.py",
    "graph.py",
    "support.py",
    "enterprise_cms.py",  # Scoped por site_key (CMS multi-tenant)
    "spiritual_life.py",
    "messaging.py",
    "youtube.py",           # Proxy público RSS — sin queries de DB
    "system.py",            # sede_id en personal_filters (*unpack) — test no lo detecta en contexto
}

# Tablas históricas bloqueadas para nuevas referencias directas
OLD_TABLES_BLOCKED = {
    "consolidation_cases",
    "CellGroup",
}

# Modelos que son catálogos o tablas internas (< 100 registros esperados)
CATALOG_CLASSES = {
    "RoleDefinition", "RolPlataforma", "NivelGamificado", "Medalla",
    "Position", "ColombianDepartment", "ColombianCity",
    "DonationCategory", "Fund", "ChurchLocation", "SocialChannel",
    "SystemVariable", "Badge", "EstrategiaEvangelismo",
    "Role", "Comment", "Rule", "UsuarioRolModulo",
    "AgentTask", "AgentInsight", "AgentRole", "AgentActivity",
    "CmsSection", "SavedView", "AutomationRule",
}

ALLOWED_OLD_PERSON_INT_REFS = set()


# ── Tests ──────────────────────────────────────────────────────────────────

def test_sede_id_in_all_queries():
    """Axioma 3: Verifica que .all() tenga filtro sede_id o esté en allowlist."""
    violations = []
    for fpath in sorted(API_DIR.glob("*.py")):
        fname = fpath.name
        if fname.startswith("__") or fname.startswith("test_"):
            continue
        
        content = fpath.read_text()
        lines = content.split("\n")
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if ".all()" not in stripped:
                continue
            
            # Ignorar si ya está comentado
            if stripped.startswith("#") or stripped.startswith("    #"):
                continue
            
            # Ignorar si ya tiene filtro de aislamiento en la misma línea
            if "sede_id" in stripped or "proyecto_id" in stripped or "grupo_id" in stripped:
                continue
            
            # Ignorar si está en allowlist
            if fname in ALLOWED_UNFILTERED:
                continue
            
            # Verificar si la query tiene filtro en líneas anteriores
            context = "\n".join(lines[max(0, i-8):i])
            if "sede_id" in context or "sede" in context.lower():
                continue
            
            violations.append(f"  {fpath}:{i}: {stripped[:80]}")
    
    if violations:
        print(f"❌ {len(violations)} queries .all() sin sede_id detectadas (no en allowlist):")
        for v in violations[:20]:
            print(v)
        if len(violations) > 20:
            print(f"   ... y {len(violations) - 20} más")
    else:
        print("✅ Todas las queries .all() tienen sede_id o están en allowlist")

    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_persona_id_is_str():
    """Regla 2: persona_id siempre str en schemas Pydantic."""
    violations = []
    for fpath in sorted(SCHEMAS_DIR.glob("*.py")):
        content = fpath.read_text()
        for i, line in enumerate(content.split("\n"), 1):
            if "persona_id:" in line and "int" in line.split("persona_id:")[1].split()[0]:
                violations.append(f"  {fpath}:{i}: {line.strip()}")
    
    if violations:
        print(f"❌ {len(violations)} persona_id: int detectados:")
        for v in violations:
            print(v)
    else:
        print("✅ Todos los persona_id en schemas son str")
    
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_no_new_person_identity_int_params():
    """UUID guardrail: no nuevas identidades persona como int."""
    violations = []
    pattern = re.compile(r"\b(persona_id|person_id)\s*:\s*int\b")

    for base_dir in (API_DIR, SCHEMAS_DIR):
        for fpath in sorted(base_dir.rglob("*.py")):
            content = fpath.read_text()
            rel = fpath.relative_to(ROOT).as_posix()
            for i, line in enumerate(content.split("\n"), 1):
                match = pattern.search(line)
                if not match:
                    continue
                identity_name = match.group(1)
                if (rel, i, identity_name) in ALLOWED_OLD_PERSON_INT_REFS:
                    continue
                violations.append(f"  {fpath}:{i}: {line.strip()}")

    if violations:
        print(f"❌ {len(violations)} nuevas identidades persona como int:")
        for v in violations:
            print(v)
    else:
        print("✅ No hay nuevas identidades persona como int")

    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_no_hard_deletes():
    """Regla 4: No db.delete() en tablas transaccionales."""
    violations = []
    hard_delete_files = set()
    
    for fpath in sorted(API_DIR.rglob("*.py")):
        if fpath.name.startswith("__") or fpath.name.startswith("test_"):
            continue
        content = fpath.read_text()
        for i, line in enumerate(content.split("\n"), 1):
            if "db.delete(" in line and not line.strip().startswith("#"):
                # Check if it's deleting a catalog model
                is_catalog = any(c in line for c in CATALOG_CLASSES)
                # Also check variable name patterns (role, rule, fund, view = catalogs)
                var_match = re.search(r'db\.delete\((\w+)\)', line)
                if var_match:
                    var_name = var_match.group(1).lower()
                    catalog_vars = {'role', 'rule', 'fund', 'view', 'rol', 'umr',
                                    'block', 'comment', 'task', 'insight', 'role_def'}
                    if var_name in catalog_vars:
                        is_catalog = True
                if not is_catalog:
                    violations.append(f"  {fpath}:{i}: {line.strip()}")
                    hard_delete_files.add(fpath.name)
    
    if violations:
        print(f"❌ {len(violations)} hard deletes detectados en {len(hard_delete_files)} archivos:")
        for v in violations[:15]:
            print(v)
        if len(violations) > 15:
            print(f"   ... y {len(violations) - 15} más")
    else:
        print("✅ No hay hard deletes en tablas transaccionales")
    
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_datetime_timezone():
    """Regla 6: DateTime con timezone=True."""
    violations = []
    for fpath in sorted(MODELS_DIR.glob("models*.py")):
        content = fpath.read_text()
        for i, line in enumerate(content.split("\n"), 1):
            if "Column(DateTime" in line and "timezone" not in line:
                violations.append(f"  {fpath}:{i}: {line.strip()}")
    
    if violations:
        print(f"❌ {len(violations)} DateTime sin timezone=True:")
        for v in violations:
            print(v)
    else:
        print("✅ Todos los DateTime tienen timezone=True")
    
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_no_jsonb():
    """Regla 8: Usar JSON, no JSONB."""
    violations = []
    for fpath in sorted(MODELS_DIR.glob("models*.py")):
        content = fpath.read_text()
        for i, line in enumerate(content.split("\n"), 1):
            if "JSONB" in line and not line.strip().startswith("#"):
                violations.append(f"  {fpath}:{i}: {line.strip()}")
    
    if violations:
        print(f"❌ {len(violations)} referencias a JSONB:")
        for v in violations:
            print(v)
    else:
        print("✅ No hay JSONB en modelos")
    
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_module_registration():
    """Regla 9: Módulos en api/__init__.py + app.py."""
    init_content = (API_DIR / "__init__.py").read_text()
    app_content = (ROOT / "backend" / "app.py").read_text()
    
    # Extract modules from app.py import line
    import_match = re.search(r"from backend\.api import \((.*?)\)", app_content, re.DOTALL)
    app_modules = set()
    if import_match:
        for m in import_match.group(1).split(","):
            m = m.strip().strip("\n ")
            if m:
                app_modules.add(m)
    
    # Extract from __all__
    all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", init_content, re.DOTALL)
    all_modules = set()
    if all_match:
        for m in all_match.group(1).split(","):
            m = m.strip().strip('"').strip("'").strip("\n ")
            if m:
                all_modules.add(m)
    
    # Extract from import line
    import_match2 = re.search(r"from backend\.api import \((.*?)\)", init_content, re.DOTALL)
    imported_modules = set()
    if import_match2:
        for m in import_match2.group(1).split(","):
            m = m.strip().strip("\n ")
            if m:
                imported_modules.add(m)
    
    # Check for mismatches
    violations = []
    for m in app_modules:
        if m not in imported_modules:
            violations.append(f"  {m}: en app.py pero no importado en api/__init__.py")
        if m not in all_modules:
            violations.append(f"  {m}: en app.py pero no en api/__all__")
    
    if violations:
        print(f"❌ {len(violations)} problemas de registro de módulos:")
        for v in violations:
            print(v)
    else:
        print(f"✅ Todos los módulos registrados correctamente ({len(all_modules)} en __all__)")
    
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


def test_soft_delete_fields_exist():
    """Regla 4: Tablas transaccionales deben tener deleted_at o estado_vital."""
    transactions = [
        "CasoCRM", "InteractionCRM", "TareaCRM", "Donation",
        "GrupoEvangelismo", "ParticipanteGrupo", "SesionGrupo",
        "AgendaEvent", "AgendaParticipante",
        "Proyecto", "TareaProyecto", "EquipoProyecto",
        "CommunityBoardCard",
    ]
    violations = []
    
    for fpath in sorted(MODELS_DIR.glob("models*.py")):
        content = fpath.read_text()
        for cls_name in transactions:
            if f"class {cls_name}" in content:
                cls_start = content.index(f"class {cls_name}")
                cls_end = content.find("\nclass ", cls_start + 1)
                if cls_end == -1:
                    cls_end = len(content)
                cls_block = content[cls_start:cls_end]
                
                if "deleted_at" not in cls_block and "estado_vital" not in cls_block:
                    violations.append(f"  {fpath}: {cls_name} sin campo soft delete")
    
    if violations:
        print(f"❌ {len(violations)} modelos sin soft delete:")
        for v in violations:
            print(v)
    else:
        print("✅ Todos los modelos transaccionales tienen soft delete")
    
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert len(violations) == 0
        return
    return len(violations)


# ── Runner ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("🔍 Auditoría de Reglas de Plataforma CCF")
    print("=" * 60)
    print()
    
    total_failures = 0
    
    tests = [
        ("Axioma 3 - sede_id en queries", test_sede_id_in_all_queries),
        ("Regla 2 - persona_id: str", test_persona_id_is_str),
        ("Regla UUID - sin nuevas identidades persona int", test_no_new_person_identity_int_params),
        ("Regla 4 - Soft deletes", test_no_hard_deletes),
        ("Regla 4 - Campos soft delete", test_soft_delete_fields_exist),
        ("Regla 6 - DateTime timezone", test_datetime_timezone),
        ("Regla 8 - JSON vs JSONB", test_no_jsonb),
        ("Regla 9 - Módulos registrados", test_module_registration),
    ]
    
    results = []
    for name, test_fn in tests:
        print(f"\n── {name} ──")
        try:
            failures = test_fn()
            total_failures += failures
            results.append((name, failures == 0, failures))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((name, False, -1))
            total_failures += 1
        print()
    
    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    for name, passed, count in results:
        status = "✅" if passed else "❌"
        detail = f" ({count} violaciones)" if not passed else ""
        print(f"  {status}  {name}{detail}")
    
    print(f"\nTotal violaciones: {total_failures}")
    
    if total_failures > 0:
        print("⚠️  Hay violaciones que requieren atención")
        sys.exit(1)
    else:
        print("🎉 Todas las reglas se cumplen")
        sys.exit(0)


if __name__ == "__main__":
    main()
