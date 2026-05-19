from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.management.schema import print_schema_drift_report


if __name__ == "__main__":
    print_schema_drift_report()
