#!/usr/bin/env python3
"""Detect new `any` usage in frontend test files.

By default the script compares the staged diff (pre-commit mode) and fails if a
frontend test file introduces new uses of `any` (e.g. `as any`, `: any`,
`any[]`, `Record<..., any>`). Common false positives such as `expect.any(...)`
and `// comments` are ignored.

In CI mode pass ``--base-branch <ref>`` to check the diff between the current
HEAD and that ref (typically the target branch of the PR).

Usage:
    python3 scripts/check-frontend-test-any.py
    python3 scripts/check-frontend-test-any.py --base-branch origin/main
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Unit/integration tests (.test.ts/.test.tsx) and e2e specs (.spec.ts/.spec.tsx).
TEST_FILE_RE = re.compile(r"^frontend/.*\.(test|spec)\.(ts|tsx)$")

# Patterns that indicate an explicit `any` usage we want to flag.
ANY_PATTERNS = [
    re.compile(r"\bas\s+any\b"),
    re.compile(r":\s*any\b"),
    re.compile(r"<\s*any\s*>"),
    re.compile(r"\bany\[\]"),
    re.compile(r"Record<[^>]*,\s*any\b"),
    re.compile(r"\btype\s+\w+\s*=\s*any\b"),
]

# Patterns that should be ignored even if they contain the word "any".
# These strip out obvious comment lines so legitimate explanations don't trip the hook.
_IGNORE_ANY = r"(?:\bas\s+any\b|:\s*any\b|<\s*any\s*>|\bany\[\]|Record<[^>]*,\s*any\b|\btype\s+\w+\s*=\s*any\b)"
IGNORE_PATTERNS = [
    re.compile(r"expect\.any\("),
    re.compile(rf"//.*{_IGNORE_ANY}"),
]


def remove_block_comments(text: str) -> str:
    """Strip /* ... */ blocks from the diff so commented-out `any` is ignored.

    Note: This is a heuristic. String literals containing `/* ... */` could be
    over-stripped, but that is uncommon in test diffs.
    """
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _git_diff_cmd(base_ref: str | None, *args: str) -> list[str]:
    cmd = ["git", "diff"]
    if base_ref is None:
        cmd.extend(["--cached"])
    cmd.extend(args)
    return cmd


def _resolve_base_ref(base_ref: str) -> str:
    """Resolve CI's remote ref, tolerating checkout refspec differences."""
    candidates = [base_ref]
    if base_ref.startswith("origin/"):
        candidates.append(base_ref.removeprefix("origin/"))
    for candidate in candidates:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{candidate}^{{commit}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    raise subprocess.CalledProcessError(128, ["git", "rev-parse", base_ref])


def _range_spec(base_ref: str | None) -> str:
    if base_ref is None:
        return "--cached"
    return f"{_resolve_base_ref(base_ref)}...HEAD"


def get_changed_files(base_ref: str | None) -> list[str]:
    range_spec = _range_spec(base_ref)
    result = subprocess.run(
        ["git", "diff", range_spec, "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.splitlines() if TEST_FILE_RE.match(f)]


def get_file_diff(path: str, base_ref: str | None) -> str:
    range_spec = _range_spec(base_ref)
    return subprocess.run(
        ["git", "diff", range_spec, "-U0", "--", path],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def line_introduces_any(line: str) -> bool:
    if not line.startswith("+") or line.startswith("+++"):
        return False
    content = line[1:]
    if any(p.search(content) for p in IGNORE_PATTERNS):
        return False
    return any(p.search(content) for p in ANY_PATTERNS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect new explicit `any` usage in frontend test files.")
    parser.add_argument(
        "--base-branch",
        dest="base_branch",
        default=None,
        help="Git ref of the base branch to diff against (e.g. origin/main). "
        "If omitted, the script checks the staged diff.",
    )
    args = parser.parse_args()

    try:
        files = get_changed_files(args.base_branch)
    except subprocess.CalledProcessError as exc:
        mode = f"base branch {args.base_branch}" if args.base_branch else "staged diff"
        print(f"Failed to compute diff for {mode}: {exc}")
        return 2

    if not files:
        mode = f"diff against {args.base_branch}" if args.base_branch else "staged diff"
        print(f"No frontend test files in {mode}; skipping any-check.")
        return 0

    violations: list[tuple[str, str]] = []
    for f in files:
        try:
            diff = get_file_diff(f, args.base_branch)
        except subprocess.CalledProcessError as exc:
            print(f"Failed to read diff for {f}: {exc}")
            return 2
        for line in remove_block_comments(diff).splitlines():
            if line_introduces_any(line):
                violations.append((f, line[1:].strip()))

    if not violations:
        mode = f"diff against {args.base_branch}" if args.base_branch else "staged diff"
        print(f"No new `any` usage detected in {mode}.")
        return 0

    print("New `any` usage detected in frontend test files:\n")
    for path, content in violations:
        print(f"  {path}: {content}")
    print("\nConsider using a typed factory or a more precise type instead.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
