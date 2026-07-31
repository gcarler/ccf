#!/usr/bin/env python3
"""Canonical public content blocks — lazy single-source re-export.

This module is the historical name for the canonical ``BLOCKS`` payloads used
by the CMS seeding pipeline. After the seed-script consolidation, the single
source of truth lives in ``ensure_public_content_blocks.BLOCKS`` (plus its
``MERGE_BLOCKS``); this module re-exports that catalog so existing importers
(``seed_public_cms_v2_sections``, ``ensure_public_cms_pastors``, etc.) keep a
stable import path.

The re-export is lazy (PEP 562 ``__getattr__``): importing this module does
NOT import the backend stack. The canonical module (and with it
``backend.models`` / ``SessionLocal``) is only imported when ``BLOCKS`` is
actually accessed, so direct imports of this module stay side-effect free
until the caller really needs the data.

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


# ── Contenido de cada bloque (catálogo canónico único, carga perezosa) ───
def __getattr__(name: str):
    """Lazily resolve ``BLOCKS`` from the canonical catalog (PEP 562)."""
    if name == "BLOCKS":
        import ensure_public_content_blocks as _canonical  # noqa: E402

        return _canonical.BLOCKS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def run():
    from seed_public_cms_v2_sections import main as seed_cms_v2_main

    print("seed_public_content.py is deprecated; running CMS v2 public seeding instead.")
    raise SystemExit(seed_cms_v2_main())


if __name__ == "__main__":
    run()
