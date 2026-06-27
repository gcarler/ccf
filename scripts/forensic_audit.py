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

#!/usr/bin/env python3.12
"""CCF FORENSIC AUDIT — Full-stack validation against new DB schema."""
import sys, os, re, json
from collections import defaultdict

sys.path.insert(0, '/root/ccf')
os.environ['ENV_FILE'] = '/root/ccf/backend/.env'

# ═══════════════════════════════════════════════════════════════
# 1. BACKEND ENDPOINT AUDIT
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("1. BACKEND ENDPOINTS")
print("=" * 60)

from backend.app import app
from backend.core.database import engine, Base
from sqlalchemy import inspect
import subprocess

results = defaultdict(list)
for route in app.routes:
    path = getattr(route, 'path', None)
    methods = getattr(route, 'methods', set())
    if not path or not methods: continue
    test_path = re.sub(r'\{[^}]+\}', '1', path)
    test_path = test_path.replace('00000000-0000-0000-0000-000000000001', '1')
    method = 'GET' if 'GET' in methods else next(iter(methods))
    results[test_path] = method

# Test all endpoints via curl
critical_500 = []
for path in sorted(results.keys()):
    url = f"http://localhost:8000{path}"
    try:
        r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', url],
                         capture_output=True, text=True, timeout=5)
        code = int(r.stdout.strip())
        if code >= 500:
            critical_500.append((path, code))
    except:
        critical_500.append((path, 'TIMEOUT'))

if critical_500:
    print(f"\n🔴 CRITICAL (500+): {len(critical_500)} endpoints")
    for p, c in critical_500:
        print(f"   {c} → {p}")
else:
    print(f"\n✅ All endpoints respond (no 500s)")

# ═══════════════════════════════════════════════════════════════
# 2. DB SCHEMA vs MODELS
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. DB ↔ MODELS SYNC")
print("=" * 60)

inspector = inspect(engine)
db_tables = set(inspector.get_table_names())
model_tables = set(Base.metadata.tables.keys())

# Tables in models but not in DB
missing = model_tables - db_tables
if missing:
    print(f"\n🔴 MISSING TABLES (model→DB): {len(missing)}")
    for t in sorted(missing):
        print(f"   {t}")
else:
    print("\n✅ All model tables exist in DB")

# Tables in DB but not in models (orphan)
orphan = db_tables - model_tables
if orphan:
    print(f"\n⚠️ ORPHAN TABLES (DB→model): {len(orphan)}")
    for t in sorted(orphan):
        print(f"   {t}")

# Column type mismatches for persona_id FKs
type_issues = []
for table_name in sorted(db_tables):
    try:
        cols = {c['name']: str(c['type']) for c in inspector.get_columns(table_name)}
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            if fk['referred_table'] == 'personas':
                for col in fk['constrained_columns']:
                    col_type = cols.get(col, '?')
                    if 'UUID' not in col_type.upper() and 'INTEGER' not in col_type.upper():
                        type_issues.append(f"{table_name}.{col} = {col_type} → personas.id (UUID)")
    except:
        pass

if type_issues:
    print(f"\n🔴 FK TYPE MISMATCHES: {len(type_issues)}")
    for i in type_issues:
        print(f"   {i}")
else:
    print("\n✅ All persona FK types match (UUID or Integer)")

# ═══════════════════════════════════════════════════════════════
# 3. FRONTEND ↔ BACKEND ROUTE MATCH
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. FRONTEND ↔ BACKEND ROUTES")
print("=" * 60)

# Extract frontend API calls
frontend_calls = set()
for dirpath, _, files in os.walk('/root/ccf/frontend/src'):
    for f in files:
        if not f.endswith(('.tsx', '.ts')): continue
        path = os.path.join(dirpath, f)
        content = open(path).read()
        for match in re.finditer(r"apiFetch(?:<[^>]+>)?\(\s*['\"\`](/[^'\"\`?#\s]+)", content):
            frontend_calls.add('/api' + match.group(1))

# Extract backend routes
backend_routes = set()
for route in app.routes:
    p = getattr(route, 'path', None)
    if p: backend_routes.add(p)

# Find frontend calls with no backend match
unmatched = []
for fc in sorted(frontend_calls):
    # Normalize params (handle both FastAPI {param} and JS template ${param})
    normalized = re.sub(r'\$\{[^}]+\}|\{[^}]+\}', '{}', fc).rstrip('/')
    # Check if any backend route matches
    found = False
    for br in backend_routes:
        br_norm = re.sub(r'\{[^}]+\}', '{}', br).rstrip('/')
        if br_norm == normalized:
            found = True
            break
    if not found:
        unmatched.append(fc)

if unmatched:
    print(f"\n🔴 UNMATCHED (frontend→backend): {len(unmatched)}")
    for u in unmatched:
        print(f"   {u}")
else:
    print("\n✅ All frontend API calls have matching backend routes")

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
issues = len(critical_500) + len(missing) + len(type_issues) + len(unmatched)
if issues == 0:
    print("\n✅ PLATFORM 100% CLEAN — Zero issues found")
else:
    print(f"\n⚠️ {issues} issues found — see details above")
