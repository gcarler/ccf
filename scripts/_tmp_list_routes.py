"""Temporal helper: lista rutas de la API para mapear paths de tests rotos."""
from backend.app import app
import collections

groups = collections.defaultdict(list)
for route in app.routes:
    path = getattr(route, "path", "")
    methods = " ".join(sorted(getattr(route, "methods", []) or ["???"]))
    if not path:
        continue
    parts = path.split("/")
    if path.startswith("/api/") and len(parts) >= 3:
        prefix = parts[2]
    else:
        prefix = "(root)"
    if prefix in {
        "evangelism", "evangelism-grupos", "evangelism-events",
        "evangelism-main", "evangelism-multiplication", "evangelism-rankings",
        "evangelism-analytics", "crm", "cms", "kernel", "messaging",
        "spiritual-life", "public",
    }:
        groups[prefix].append((methods, path))

for k in sorted(groups):
    print(f"\n=== /api/{k}  (n={len(groups[k])}) ===")
    for m, p in sorted(groups[k]):
        print(f"  {m:12s}  {p}")
