#!/usr/bin/env python3
"""SAFE handler for no-unused-vars inside MULTI-LINE import blocks.

Uses a block-parse algorithm: locate the brace block, extract ALL names, drop
the flagged name, re-emit preserving indentation and trailing-comma style.

This avoids the brittle-pattern approach that previously broke syntax by
mismatching comma separators.
"""
from __future__ import annotations
import json, re
from pathlib import Path

LINT_JSON = Path("/tmp/lint.json")
NAME_RE = re.compile(r"'([^']+)' is defined but never used")
ML_OPEN = re.compile(r"\bimport\b[^{]*\{(?![^{}]*\})")  # import { without closing } on same line
ML_CLOSE = re.compile(r"\}\s*[A-Za-z]*\s*from\b")      # } from


def find_block_bounds(lines: list[str], idx: int) -> tuple[int, int] | None:
    """Walk backward to find import { opener, forward to find } from closer."""
    start = idx
    while start > 0:
        if ML_OPEN.search(lines[start]):
            break
        start -= 1
    else:
        return None
    if not ML_OPEN.search(lines[start]):
        return None
    end = idx
    while end < len(lines):
        if ML_CLOSE.search(lines[end]):
            break
        end += 1
    if end >= len(lines) or not ML_CLOSE.search(lines[end]):
        return None
    return start, end


def parse_names(inner: str) -> list[str]:
    """Split braces content into a list of identifier names."""
    parts = re.split(r"[,\n]", inner)
    return [p.strip().rstrip(",").strip() for p in parts if p.strip()]


def detect_indent_and_trailing(inner_text: str, names: list[str]) -> tuple[str, bool]:
    """Return (indent_string, has_trailing_comma)."""
    has_tc = "," in inner_text
    if not names:
        return "  ", has_tc
    # Find first name and its surrounding indentation
    first = names[0]
    m = re.search(r"(\n[ \t]*|^[ \t]*)" + re.escape(first), inner_text)
    indent = "  "
    if m:
        captured = m.group(1)
        if captured.startswith("\n"):
            indent = captured[1:]
        else:
            indent = captured
    return indent, has_tc


def remove_from_block(text: str, name: str, ln_no: int) -> tuple[str, bool]:
    lines = text.split("\n")
    idx = ln_no - 1
    if idx >= len(lines):
        return text, False
    bounds = find_block_bounds(lines, idx)
    if bounds is None:
        return text, False
    start, end = bounds
    block_text = "\n".join(lines[start:end + 1])

    # Extract inner braces content
    m = re.search(r"import\s*\{(.*?)\}\s*([A-Za-z]*)\s*from\s*(['\"][^'\"]+['\"])", block_text, re.DOTALL)
    if not m:
        return text, False
    inner = m.group(1)
    names = parse_names(inner)
    if name not in names:
        return text, False
    new_names = [n for n in names if n != name]
    if len(new_names) == len(names):
        return text, False

    if not new_names:
        # Drop the entire import line
        return "\n".join(lines[:start] + lines[end + 1:]), True

    indent, has_tc = detect_indent_and_trailing(inner, names)
    sep = ",\n" + indent
    new_inner = sep.join(new_names) + ("," if has_tc else "")

    # Assemble: keep opening on start line, content with indent, closer on end line
    open_match = re.match(r"^([^\n]*?import\s*\{)", block_text)
    closer_match = re.search(r"\}\s*([A-Za-z]*)\s*from\s*(['\"][^'\"]+['\"])", block_text)
    if not open_match or not closer_match:
        return text, False
    opener = open_match.group(1)
    closer = "}" + ((" " + closer_match.group(1)) if closer_match.group(1) else "") + " from " + closer_match.group(2)
    # Preserve trailing newline of the block
    tail = ""
    if block_text.endswith("\n"):
        tail = "\n"
    new_block = opener + "\n" + indent + new_inner + "\n" + closer + tail

    lines[start:end + 1] = new_block.split("\n")
    return "\n".join(lines), True


def main() -> int:
    data = json.loads(LINT_JSON.read_text())
    edited: list[str] = []

    for entry in data:
        fp = Path(entry["filePath"])
        if not fp.is_file():
            continue
        errs = [
            m for m in entry["messages"]
            if m.get("severity") == 2
            and m.get("ruleId") == "@typescript-eslint/no-unused-vars"
        ]
        if not errs:
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        modified = False
        for msg in sorted(errs, key=lambda m: (m["line"], m.get("column", 0)), reverse=True):
            mm = NAME_RE.search(msg.get("message", ""))
            if not mm:
                continue
            name = mm.group(1)
            new_text, was = remove_from_block(text, name, msg["line"])
            if was:
                text = new_text
                modified = True
        if modified:
            fp.write_text(text, encoding="utf-8")
            edited.append(str(fp))

    print(f"Modified {len(edited)} files (multi-line)")
    for f in edited:
        print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
