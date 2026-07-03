#!/usr/bin/env python3
"""Bulk-fix ESLint baseline errors SAFELY. Handles:
- Single-line `import { ... } from 'mod'` (surgical binding removal)
- `import X from 'mod'` and `import * as X from 'mod'` (whole-line drop)
- `react/no-unescaped-entities` (char -> entity replacement at line:col)

Multi-line imports are SKIPPED (logged) — handle separately with a block-aware
script to avoid regex-induced syntax breakage.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ENTITIES = {"'": "&apos;", '"': "&quot;", ">": "&gt;", "}": "&#125;"}
LINT_JSON = Path("/tmp/lint.json")
NAME_RE = re.compile(r"'([^']+)' is defined but never used")
ML_IMPORT_OPEN = re.compile(r"\bimport\b[^{]*\{")

def safe_remove_single_line(line: str, name: str) -> tuple[str, bool]:
    stripped = line.strip()
    if re.match(r"^import\s*\*\s*as\s+" + re.escape(name) + r"\s+from", stripped):
        return "", True
    if re.match(r"^import\s+" + re.escape(name) + r"\s+from", stripped):
        return "", True
    m = re.search(r"import\s*\{([^}]*)\}\s*from", line)
    if m:
        items = [it.strip() for it in m.group(1).split(",") if it.strip()]
        new_items = [it for it in items if it != name]
        if len(new_items) == len(items):
            return line, False
        if not new_items:
            return "", True
        new_inner = ", ".join(new_items)
        new_line = re.sub(r"import\s*\{[^}]*\}\s*from", f"import {{{new_inner}}} from", line, count=1)
        return new_line, False
    return line, False


def is_multiline_import_block(text: str, ln_no: int) -> bool:
    """Detect whether line ln_no is part of a multi-line `import { ... } from` block."""
    lines = text.split("\n")
    idx = ln_no - 1
    if idx >= len(lines):
        return False
    # Walk back: find line containing `import {` (no `}` on same line)
    start = idx
    while start > 0:
        ln = lines[start]
        if ML_IMPORT_OPEN.search(ln) and "}" not in ln.split("from")[0]:
            return True
        if re.search(r"\bimport\b", ln) and "{" in ln:
            # Could be opening line
            if "}" not in ln:
                return True
        start -= 1
        if start < max(0, idx - 60):
            break
    # Walk forward: find line containing `} from`
    end = idx
    while end < len(lines) - 1:
        if re.search(r"\}[^}]*\bfrom\b", lines[end]):
            return True
        end += 1
        if end > min(len(lines) - 1, idx + 60):
            break
    return False


def main() -> int:
    if not LINT_JSON.exists():
        print("missing /tmp/lint.json")
        return 2
    data = json.loads(LINT_JSON.read_text())
    edited: list[str] = []
    skipped_ml: list[tuple[str, int, str]] = []
    for entry in data:
        fp = Path(entry["filePath"])
        if not fp.is_file():
            continue
        errs = [m for m in entry["messages"] if m.get("severity") == 2]
        if not errs:
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        modified = False
        for msg in sorted(errs, key=lambda m: (m["line"], m.get("column", 0)), reverse=True):
            rule = msg.get("ruleId")
            ln = msg["line"]; col = msg.get("column", 1)
            try:
                if rule == "@typescript-eslint/no-unused-vars":
                    mm = NAME_RE.search(msg.get("message", "")) or re.search(r"'([^']+)'", msg.get("message", ""))
                    if not mm:
                        continue
                    name = mm.group(1)
                    lines = text.split("\n")
                    if ln - 1 >= len(lines):
                        continue
                    line = lines[ln - 1]
                    other = "\n".join(lines[: ln - 1] + lines[ln:])
                    if len(re.findall(r"\b" + re.escape(name) + r"\b", other)) > 5:
                        continue
                    if not re.search(r"\bimport\b", line):
                        # Not on an import line — could be multi-line import block or
                        # truly a non-import unused var.
                        if is_multiline_import_block(text, ln):
                            skipped_ml.append((str(fp), ln, name))
                            continue
                        # Otherwise leave alone (manual)
                        continue
                    new_line, removed = safe_remove_single_line(line, name)
                    if removed:
                        lines.pop(ln - 1)
                    elif new_line != line:
                        lines[ln - 1] = new_line
                    text = "\n".join(lines)
                    modified = True
                elif rule == "react/no-unescaped-entities":
                    mm = re.search(r"`([^`]+)`", msg.get("message", ""))
                    if not mm:
                        continue
                    char = mm.group(1).strip()
                    entity = ENTITIES.get(char)
                    if not entity:
                        continue
                    lines = text.split("\n")
                    line_text = lines[ln - 1]
                    idx = col - 1
                    if 0 <= idx < len(line_text) and line_text[idx] == char:
                        lines[ln - 1] = line_text[:idx] + entity + line_text[idx + 1:]
                        text = "\n".join(lines)
                        modified = True
            except Exception:
                continue
        if modified:
            fp.write_text(text, encoding="utf-8")
            edited.append(str(fp))
    print(f"Modified {len(edited)} files (single-line + entities)")
    for f in edited:
        print(f"  - {f}")
    print()
    print(f"Skipped {len(skipped_ml)} multi-line import bindings")
    for f, l, n in skipped_ml:
        print(f"  - {f}:{l}  name={n}")
    print()
    print("Files needing multi-line cleanup:")
    import collections
    files_ml = collections.Counter(f for f, _, _ in skipped_ml)
    for f, c in files_ml.most_common():
        print(f"  {c:3d} {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
