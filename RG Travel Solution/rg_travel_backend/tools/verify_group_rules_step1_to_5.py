"""
Tool wrapper to run Step 1-5 group-creation rule verification.

Run:
  python rg_travel_backend/tools/verify_group_rules_step1_to_5.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    tests_dir = backend_dir / "tests"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))

    from verify_step1_to_5_rules import main as verify_main  # type: ignore

    print("Running Step 1-5 rule verification...")
    rc = int(verify_main())
    if rc == 0:
        print("Wrapper result: PASS")
    else:
        print("Wrapper result: FAIL")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

