#!/usr/bin/env python3
"""Canonical public content blocks — single source re-export.

This module is the historical name for the canonical ``BLOCKS`` payloads used
by the CMS seeding pipeline. After the seed-script consolidation, the single
source of truth lives in ``ensure_public_content_blocks.BLOCKS`` (plus its
``MERGE_BLOCKS``); this module re-exports that catalog so existing importers
(``seed_public_cms_v2_sections``, ``ensure_public_cms_pastors``, etc.) keep a
stable import path.

Usage:
    cd /root/ccf && source venv/bin/activate && python scripts/seed_public_content.py
"""

from __future__ import annotations

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
if str(_PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

# ── Contenido de cada bloque (catálogo canónico único) ─────────────────────
import ensure_public_content_blocks as _canonical  # noqa: E402

BLOCKS = _canonical.BLOCKS


def run():
    from seed_public_cms_v2_sections import main as seed_cms_v2_main

    print("seed_public_content.py is deprecated; running CMS v2 public seeding instead.")
    raise SystemExit(seed_cms_v2_main())


if __name__ == "__main__":
    run()
