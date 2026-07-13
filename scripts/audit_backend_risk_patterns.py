#!/usr/bin/env python3
"""Report backend patterns that deserve manual API review.

The script is read-only and intentionally conservative: it does not decide
whether a hit is a bug, it only groups common causes of production 500s.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

PATTERNS: dict[str, re.Pattern[str]] = {
    "response_model_dict": re.compile(r"response_model\s*=\s*(?:dict|Dict\[|List\[dict\]|list\[dict\])"),
    "schema_list_any": re.compile(r":\s*(?:List|list)\[Any\]"),
    "raw_model_dict_mutation": re.compile(r"\.__dict__\s*\["),
    "orm_all_return": re.compile(r"return\s+[^\\n]*(?:query|select|db)\([^\\n]*\.all\("),
    "hard_delete": re.compile(r"\b(?:db|session)\.delete\(|\.delete\("),
    "users_fk": re.compile(r"ForeignKey\([\"']users\.id[\"']"),
}

EXCLUDED_DIRS = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "migrations",
}


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for path in BACKEND.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def scan_file(path: Path) -> dict[str, list[dict[str, object]]]:
    text = path.read_text(encoding="utf-8")
    hits: dict[str, list[dict[str, object]]] = {}
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[line_no - 1].strip()
            hits.setdefault(name, []).append({"line": line_no, "text": line[:240]})
    return hits


def main() -> int:
    findings: dict[str, dict[str, list[dict[str, object]]]] = {}
    counts = {name: 0 for name in PATTERNS}

    for path in iter_python_files():
        hits = scan_file(path)
        if not hits:
            continue
        rel_path = str(path.relative_to(ROOT))
        findings[rel_path] = hits
        for name, entries in hits.items():
            counts[name] += len(entries)

    payload = {
        "scanned_root": str(BACKEND.relative_to(ROOT)),
        "file_count": len(iter_python_files()),
        "pattern_counts": counts,
        "findings": findings,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
