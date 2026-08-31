#!/usr/bin/env python3
"""Detect direct imports that cross CCF module ownership boundaries.

The checker starts in report mode so existing debt can be inventoried without
breaking current builds. ``--strict`` is the CI mode and fails on findings
that are not explicitly recorded in the boundary exception file.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCEPTIONS = ROOT / "docs" / "modular_boundary_exceptions.json"

MODULE_PREFIXES = {
    "crm": ("api/crm", "crud/crm_"),
    "academy": ("api/academy", "crud/academy"),
    "cms": ("api/cms", "api/cms_v2", "crud/cms"),
    "evangelism": ("api/evangelism", "api/evangelism_events", "api/evangelism_grupos", "api/evangelism_main"),
    "messaging": ("api/messaging", "api/chat", "crud/messaging"),
    "agenda": ("api/agenda", "crud/agenda"),
    "projects": ("api/projects", "crud/projects"),
    "finance": ("api/finance", "api/finance_suite", "crud/finance"),
    "spiritual_life": ("api/spiritual_life", "crud/spiritual_life"),
}

SERVICE_OWNERS = {
    "evangelism_crm_bridge": "evangelism",
    "event_registration_service": "evangelism",
    "messaging": "messaging",
    "messaging_outcomes": "messaging",
    "crm_resource_bank": "crm",
    "automation_engine": "crm",
}


@dataclass(frozen=True)
class Finding:
    source: str
    source_module: str
    imported: str
    target_module: str
    line: int


def module_for_path(path: Path) -> str | None:
    relative = path.relative_to(ROOT).as_posix()
    for module, prefixes in MODULE_PREFIXES.items():
        if any(relative.startswith(f"backend/{prefix}/") or relative == f"backend/{prefix}.py" for prefix in prefixes):
            return module
    return None


def module_for_import(imported: str) -> str | None:
    parts = imported.split(".")
    if len(parts) >= 3 and parts[0:2] == ["backend", "api"]:
        candidate = parts[2]
        for module, prefixes in MODULE_PREFIXES.items():
            if any(prefix.startswith(f"api/{candidate}") for prefix in prefixes):
                return module
    if len(parts) >= 3 and parts[0:2] == ["backend", "crud"]:
        candidate = parts[2]
        for module, prefixes in MODULE_PREFIXES.items():
            if any(prefix.startswith(f"crud/{candidate}") for prefix in prefixes):
                return module
    if len(parts) >= 3 and parts[0:2] == ["backend", "services"]:
        return SERVICE_OWNERS.get(parts[2])
    return None


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in (ROOT / "backend", ROOT / "scripts"):
        files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return files


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_python_files():
        source_module = module_for_path(path)
        if source_module is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            imports: list[str] = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports = [node.module]
            for imported in imports:
                target_module = module_for_import(imported)
                if target_module and target_module != source_module:
                    findings.append(
                        Finding(
                            source=path.relative_to(ROOT).as_posix(),
                            source_module=source_module,
                            imported=imported,
                            target_module=target_module,
                            line=node.lineno,
                        )
                    )
    return sorted(findings, key=lambda item: (item.source, item.line, item.imported))


def load_exceptions(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(str(item["source"]), str(item["imported"])) for item in data.get("exceptions", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="fail when non-exempt boundaries are found")
    parser.add_argument("--exceptions", type=Path, default=DEFAULT_EXCEPTIONS)
    args = parser.parse_args()

    findings = scan()
    exceptions = load_exceptions(args.exceptions)
    active = [item for item in findings if (item.source, item.imported) not in exceptions]
    for item in findings:
        marker = "EXEMPT" if (item.source, item.imported) in exceptions else "NEW"
        print(f"[{marker}] {item.source}:{item.line} ({item.source_module}) -> {item.imported} ({item.target_module})")
    print(f"Boundary scan: {len(findings)} findings, {len(active)} non-exempt")
    if args.strict and active:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
