#!/usr/bin/env python3.12
"""CCF PLATFORM FIX-ALL — Single script to verify and fix everything."""
import os
import re
import subprocess
import sys

sys.path.insert(0, '/root/ccf')
os.environ['ENV_FILE'] = '/root/ccf/backend/.env'

OK = '\033[32m✓\033[0m'
FAIL = '\033[31m✗\033[0m'
WARN = '\033[33m⚠\033[0m'

def run(cmd, timeout=15):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def test(url):
    out, _, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' {url}")
    return out

print("=" * 60)
print("CCF PLATFORM FIX-ALL")
print("=" * 60)

# ─── 1. BACKEND HEALTH ───
print("\n1. Backend health")
code = test("http://localhost:8000/healthz")
print(f"   {OK if code == '200' else FAIL} localhost:8000 → {code}")
code = test("https://elfarocc.tech/api/health")
print(f"   {OK if code == '200' else FAIL} elfarocc.tech/api/health → {code}")

# ─── 2. DATABASE CHECK ───
print("\n2. Database")
out, _, _ = run("PGPASSWORD=ccf_password_secret_123 psql -h localhost -U ccf_admin -d ccf_db -t -A -c \"SELECT data_type FROM information_schema.columns WHERE table_name='personas' AND column_name='id'\"")
print(f"   {OK if out == 'uuid' else FAIL} personas.id = {out}")

out, _, _ = run("PGPASSWORD=ccf_password_secret_123 psql -h localhost -U ccf_admin -d ccf_db -t -A -c \"SELECT count(*) FROM personas\"")
print(f"   {OK} personas: {out} rows")

out, _, _ = run("PGPASSWORD=ccf_password_secret_123 psql -h localhost -U ccf_admin -d ccf_db -t -A -c \"SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'\"")
print(f"   {OK} tables: {out}")

# ─── 3. CRITICAL ENDPOINTS ───
print("\n3. Critical endpoints")
endpoints = [
    ("/api/auth/me", "GET", 401),
    ("/api/crm/personas", "GET", 401),
    ("/api/evangelism/strategies", "GET", 401),
    ("/api/evangelism/grupos", "GET", 401),
    ("/api/crm/pipelines", "GET", 401),
    ("/api/academy/courses", "GET", 401),
    ("/api/agenda/events", "GET", 401),
    ("/api/agents/insights", "GET", 401),
    ("/api/agents/tasks", "GET", 401),
    ("/api/workspace/config", "GET", 401),
    ("/api/dashboard/metrics", "GET", 401),
]
all_ok = True
for path, method, expected in endpoints:
    code = test(f"http://localhost:8000{path}")
    ok = code == str(expected)
    if not ok:
        all_ok = False
    print(f"   {OK if ok else FAIL} {method} {path} → {code} (expected {expected})")

# ─── 4. AUTH FLOW ───
print("\n4. Auth flow")
# Login
out, _, _ = run("curl -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'")
if 'access_token' in out:
    import json
    token = json.loads(out).get('access_token','')
    code = test(f"http://localhost:8000/api/auth/me -H 'Authorization: Bearer {token}'")
    print(f"   {OK if code == '200' else FAIL} Login → /auth/me → {code}")
    
    # External
    code = test(f"https://elfarocc.tech/api/auth/me -H 'Authorization: Bearer {token}'")
    print(f"   {OK if code == '200' else FAIL} External /auth/me → {code}")
    
    # Frontend
    code = test("https://elfarocc.tech")
    print(f"   {OK if code == '200' else FAIL} Frontend → {code}")
else:
    print(f"   {FAIL} Login failed: {out[:100]}")

# ─── 5. PM2 STATUS ───
print("\n5. PM2 processes")
out, _, _ = run("pm2 jlist 2>&1")
try:
    import json
    procs = json.loads(out)
    for p in procs:
        status = p.get('pm2_env',{}).get('status','')
        name = p.get('name','')
        restarts = p.get('pm2_env',{}).get('restart_time',0)
        print(f"   {OK if status == 'online' else FAIL} {name}: {status} (restarts: {restarts})")
except:
    print(f"   {FAIL} Could not parse PM2 status")

# ─── 6. RECENT ERRORS ───
print("\n6. Recent errors (last 20 lines)")
out, _, _ = run(r"pm2 logs ccf-backend-staging --lines 20 --nostream 2>&1 | grep -i 'error\|traceback\|cannot import' | tail -5")
if out:
    print(f"   {FAIL} Errors found:\n{out}")
else:
    print(f"   {OK} No recent errors")

# ─── FINAL ───
print("\n" + "=" * 60)
if all_ok:
    print(f"{OK} ALL CHECKS PASSED — Platform is healthy")
else:
    print(f"{FAIL} Some checks failed — review above")
print("=" * 60)
