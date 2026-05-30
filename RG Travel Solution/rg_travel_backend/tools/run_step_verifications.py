"""
Run core backend verification steps with one command.

Run:
  python rg_travel_backend/tools/run_step_verifications.py

Optional:
  python rg_travel_backend/tools/run_step_verifications.py --base-url http://127.0.0.1:5000
  python rg_travel_backend/tools/run_step_verifications.py --skip-live
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, List, Tuple

import requests


CheckFn = Callable[[], int]


def _health_ok(base_url: str) -> bool:
    try:
        res = requests.get(f"{base_url.rstrip('/')}/api/health", timeout=4)
        return res.status_code == 200
    except Exception:
        return False


def _run_step1_to_5() -> int:
    from verify_step1_to_5_rules import main as verify_main  # type: ignore

    return int(verify_main())


def _run_preassign_e2e(base_url: str) -> int:
    os.environ["RG_BASE_URL"] = base_url
    from verify_preassign_start_gate_flow import main as verify_main  # type: ignore

    return int(verify_main())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run consolidated step verifications.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5000",
        help="Backend base URL for live API verifications.",
    )
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="Skip API/live verifications that require running backend.",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    tests_dir = backend_dir / "tests"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))

    checks: List[Tuple[str, CheckFn]] = [
        ("Step1-5 rules", _run_step1_to_5),
    ]

    live_ok = _health_ok(args.base_url)
    if not args.skip_live and live_ok:
        checks.append(
            (
                "Preassign start-gate E2E",
                lambda: _run_preassign_e2e(args.base_url),
            )
        )
    elif not args.skip_live and not live_ok:
        print(
            f"[WARN] Live backend not reachable at {args.base_url}. "
            "Skipping preassign E2E (use --skip-live to silence)."
        )

    print("=== run_step_verifications ===")
    failures = 0
    for label, fn in checks:
        try:
            rc = int(fn())
            if rc == 0:
                print(f"{label}: PASS")
            else:
                failures += 1
                print(f"{label}: FAIL (rc={rc})")
        except Exception as exc:
            failures += 1
            print(f"{label}: FAIL ({exc})")

    if failures == 0:
        print("RESULT: PASS")
        return 0
    print(f"RESULT: FAIL ({failures} failed check(s))")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

