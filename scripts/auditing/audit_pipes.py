#!/usr/bin/env python
"""Audit: every apiFetch call vs every resolved backend route — robust edition."""

import re
import sys
from collections import defaultdict
from pathlib import Path

FRONTEND = Path(r"D:\ccf\frontend\src")
BACKEND = Path(r"D:\ccf\backend")


# ── 1. Extract all apiFetch calls ──────────────────────────────────────
def extract_apifetch_calls(root: Path):
    calls = []
    for f in root.rglob("*.ts*"):
        if ".bak" in f.name or "node_modules" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue

        pattern = r"apiFetch(?:<[^>]*>)?\s*\(\s*([`'\"]/[^`'\"]+[`'\"])\s*,"
        for m in re.finditer(pattern, text, re.DOTALL):
            url_raw = m.group(1).strip("`'\"").replace("${", "{").replace("}", "}")
            url_raw = re.sub(r"\$\{[^}]+\}", "{param}", url_raw)
            rest = text[m.end() :]
            method_m = re.search(r"""method\s*:\s*['\"]([A-Z]+)['\"]""", rest[:300])
            method = method_m.group(1) if method_m else "GET"
            calls.append(
                {
                    "file": str(f.relative_to(FRONTEND.parent)),
                    "line": text[: m.start()].count("\n") + 1,
                    "method": method,
                    "url": url_raw,
                }
            )
    return calls


# ── 2. Resolve all backend routes (handles include_router chains) ─────
def resolve_backend_routes():
    routes = []
    api_dir = BACKEND / "api"

    # ── Parse ROUTER_REGISTRY from app.py ──
    app_py = BACKEND / "app.py"
    mount_map = {}  # module_name -> mount_prefix
    if app_py.exists():
        text = app_py.read_text(encoding="utf-8")
        # Pattern: (module.router, "/api/prefix", ["tags"]) or (module.router, "/api", None)
        for m in re.finditer(r'\(\s*(\w+(?:\.\w+)*)\s*,\s*"([^"]+)"\s*,', text):
            module_path = m.group(1)  # e.g. "auth", "crm", "agents.analytics_router"
            prefix = m.group(2)
            # Get just the module name (first part before dot)
            mod_base = module_path.split(".")[0]
            mount_map[mod_base] = prefix

    # ── Build include_router graph ──
    # For each __init__.py, find which sub-modules it includes
    include_graph = {}  # parent_module -> [submodule_names]
    for init_file in api_dir.rglob("__init__.py"):
        try:
            text = init_file.read_text(encoding="utf-8")
        except:
            continue
        parent = str(init_file.parent.relative_to(api_dir)).replace("\\", "/")
        includes = []
        for m in re.finditer(r"from\s+backend\.api\.(\w+)\s+import\s+(\w+)", text):
            sub_pkg = m.group(1)
            sub_mod = m.group(2)
            includes.append(sub_pkg)
        # Also look for: from backend.api.crm import members, pastoral
        for m in re.finditer(r"from\s+backend\.api\.([\w.]+)\s+import\s+(\w+)", text):
            sub_pkg = m.group(1).split(".")[0]
            if sub_pkg not in includes:
                includes.append(sub_pkg)
        # And: router.include_router(x.router)
        for m in re.finditer(r"include_router\((\w+)\.router\)", text):
            mod_name = m.group(1)
            if mod_name not in includes:
                includes.append(mod_name)

        if includes and parent:
            # parent might be "crm" or "workspace" etc
            include_graph[parent] = list(set(includes))

    # Map sub-module file to parent: crm/pastoral.py -> crm
    sub_to_parent = {}
    for parent, subs in include_graph.items():
        for sub in subs:
            sub_to_parent[sub] = parent

    # ── Extract routes from all .py files ──
    for f in api_dir.rglob("*.py"):
        if f.name.startswith("__") or f.name.startswith("_"):
            # Skip shared helpers that don't define routes
            if f.name not in ("__init__.py",):
                continue
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue

        # Check if this file defines a router
        if "APIRouter" not in text and "@router." not in text:
            continue

        rel = str(f.relative_to(api_dir)).replace("\\", "/")

        # Determine mount prefix
        mount_prefix = ""

        # Is this a top-level module file like academy.py, admin.py, etc?
        parts = rel.split("/")
        if len(parts) == 1:  # e.g., "academy.py"
            mod_name = parts[0][:-3]  # strip .py
            mount_prefix = mount_map.get(mod_name, "")
        elif len(parts) >= 2:
            # Sub-directory file like crm/pastoral.py
            parent_dir = parts[0]  # "crm"
            filename = parts[-1][:-3]  # "pastoral"

            # Check if this file is included via parent's include_router
            if parent_dir in include_graph and filename in include_graph[parent_dir]:
                mount_prefix = mount_map.get(parent_dir, "")
            elif parent_dir in mount_map and filename == parent_dir:
                # __init__.py routes
                mount_prefix = mount_map.get(parent_dir, "")

        # Look for inner prefix on APIRouter
        inner_prefix = ""
        prefix_m = re.search(r'APIRouter\s*\(\s*prefix\s*=\s*"([^"]*)"', text)
        if prefix_m:
            inner_prefix = prefix_m.group(1)

        # Extract route decorators
        for rm in re.finditer(
            r'@router\.(get|post|put|patch|delete)\s*\(\s*"([^"]*)"', text
        ):
            http_method = rm.group(1).upper()
            route_path = rm.group(2)
            full_path = mount_prefix + inner_prefix + route_path
            routes.append(
                {
                    "method": http_method,
                    "path": full_path,
                    "file": str(f.relative_to(BACKEND)),
                }
            )

    return routes


# ── 3. Normalize and match ───────────────────────────────────────────
def normalize_path(p):
    p = re.sub(r"\{[^}]+\}", "{param}", p)
    p = p.split("?")[0]
    p = p.rstrip("/")
    if not p.startswith("/"):
        p = "/" + p
    return p


def main():
    print("=" * 70)
    print("API PIPE AUDIT v2")
    print("=" * 70)

    print("\n[1/3] Extracting frontend apiFetch calls...")
    fe_calls = extract_apifetch_calls(FRONTEND)
    print(f"  Found {len(fe_calls)} apiFetch calls")

    print("\n[2/3] Resolving backend routes...")
    be_routes = resolve_backend_routes()
    print(f"  Found {len(be_routes)} backend routes")

    be_lookup = defaultdict(list)
    for r in be_routes:
        key = (r["method"].upper(), normalize_path(r["path"]))
        be_lookup[key].append(r["file"])

    print("\n[3/3] Cross-referencing...")
    print("=" * 70)

    matches = 0
    mismatches = []
    no_api_count = 0

    for call in fe_calls:
        url = call["url"]
        method = call["method"].upper()
        actual_path = normalize_path("/api" + url)

        key_actual = (method, actual_path)
        key_direct = (method, normalize_path(url))

        if key_actual in be_lookup:
            matches += 1
        elif key_direct in be_lookup:
            matches += 1
            no_api_count += 1
        else:
            candidates = []
            for (bm, bp), files in be_lookup.items():
                if bm == method:
                    bp_segs = set(bp.split("/"))
                    ap_segs = set(actual_path.split("/"))
                    common = bp_segs & ap_segs
                    if len(common) >= 3:
                        candidates.append((bp, files[:2]))

            mismatches.append(
                {
                    "call": call,
                    "actual_path": actual_path,
                    "candidates": sorted(
                        candidates, key=lambda x: -len(x[0].split("/"))
                    )[:3],
                }
            )

    print(f"\n  MATCHED:  {matches}/{len(fe_calls)}")
    print(f"  (of which {no_api_count} matched via direct prefix)")
    print(f"  MISMATCH: {len(mismatches)}")

    if mismatches:
        print("\n-- MISMATCHES --")
        for i, m in enumerate(mismatches, 1):
            c = m["call"]
            print(f"\n  [{i}] {c['method']} {c['url']}")
            print(f"      File: {c['file']}:{c['line']}")
            print(f"      Resolves to: {m['actual_path']}")
            if m["candidates"]:
                print(f"      Candidates:")
                for cand_path, files in m["candidates"]:
                    print(f"        {cand_path} ({', '.join(files)})")
            else:
                print(f"      NO candidates found")

    print("\n" + "=" * 70)
    if mismatches:
        print(f"AUDIT RESULT: {len(mismatches)} mismatches - NOT 100%")
    else:
        print(f"AUDIT RESULT: 100% MATCH ({matches}/{len(fe_calls)})")
    print("=" * 70)

    method_counts = defaultdict(int)
    for c in fe_calls:
        method_counts[c["method"].upper()] += 1
    print("\nBy method:", dict(sorted(method_counts.items())))

    return 0 if not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
