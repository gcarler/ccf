#!/usr/bin/env python3
"""Bootstrap the canonical public CMS content for the CCF site.

This orchestrator keeps the public content recovery path repeatable:

1. Seed/normalize the canonical CMS v2 sections for ``ccf``.
2. Seed the main/mobile menus and the footer page.
3. Ensure the public route contracts still exist as published pages.

The script is intentionally idempotent and can be rerun after content drift.
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
if str(_PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))


def main() -> int:
    from seed_public_cms_v2_sections import run as seed_public_sections
    from seed_public_menus_and_footer import main as seed_menus_and_footer
    from ensure_public_cms_pages import main as ensure_public_pages

    print("=== Public CMS content bootstrap (ccf) ===")
    rc = seed_public_sections("ccf")
    if rc != 0:
        return rc

    print("=== Public menus and footer ===")
    rc = seed_menus_and_footer()
    if rc != 0:
        return rc

    print("=== Public page contracts ===")
    rc = ensure_public_pages()
    if rc != 0:
        return rc

    print("=== Bootstrap complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
