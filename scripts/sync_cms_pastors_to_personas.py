#!/usr/bin/env python3
"""Sync pastoral Persona records from the CMS pastors section.

This script is the one-time/admin bridge that seeds the pastoral profile
records from the existing CMS ``pastors`` section. After this runs, the
publish workflow for the ``pastors`` page will keep the section in sync
with the pastoral profiles automatically.

Usage:
    cd /root/ccf && source venv/bin/activate && python scripts/sync_cms_pastors_to_personas.py
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

from backend.core.database import SessionLocal  # noqa: E402
from backend.crud.cms_pastors_sync import sync_pastoral_profiles_from_cms_section  # noqa: E402


def main() -> int:
    with SessionLocal() as db:
        result = sync_pastoral_profiles_from_cms_section(db)
        print("Sync complete:")
        print(f"  Matched existing personas: {result['matched']}")
        print(f"  Created new personas:      {result['created']}")
        print(f"  Total pastors in CMS:      {result['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
