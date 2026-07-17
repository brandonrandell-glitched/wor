#!/usr/bin/env python3
"""Initialize gitignored real-data fixture files from templates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.data_sources import init_real_data_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Create fixtures/real_*.json from templates")
    parser.add_argument("--force", action="store_true", help="Overwrite existing real files")
    args = parser.parse_args()
    created = init_real_data_files(force=args.force)
    if not created:
        print("Real data files already exist. Use --force to overwrite.")
        return 0
    print("Created:")
    for path in created:
        print(f"  {path}")
    print("\nNext: edit fixtures/real_customers.json with your accounts.")
    print("Set GTM_DATA_MODE=real (or leave auto) and restart the web app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
