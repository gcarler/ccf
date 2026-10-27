#!/usr/bin/env python3
"""Validate the measured coverage summary; missing or malformed data fails closed."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def line_coverage(path: Path) -> float:
    data = json.loads(path.read_text())
    value = data["total"]["lines"]["pct"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Coverage percentage must be numeric")
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("Coverage percentage must be finite and between 0 and 100")
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--format", choices=["vitest"], default="vitest")
    parser.add_argument("--threshold", type=float, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 100:
        parser.error("Threshold must be between 0 and 100")
    try:
        percentage = line_coverage(args.report)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Invalid coverage report: {exc}")
        return 1
    print(f"Line coverage: {percentage:.2f}% (required: {args.threshold:g}%)")
    return 0 if percentage >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
