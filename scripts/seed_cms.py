#!/usr/bin/env python3
"""Deprecated legacy wrapper for the old `page_contents -> CMS` migration.

The canonical public CMS bootstrap now lives in
``scripts/seed_public_cms_v2_sections.py`` and no longer depends on the legacy
``page_contents`` tables.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def run() -> int:
    from seed_public_cms_v2_sections import main as seed_public_cms_v2_main

    print("seed_cms.py is deprecated; running CMS v2 public seeding instead.")
    return int(seed_public_cms_v2_main())


if __name__ == "__main__":
    raise SystemExit(run())
