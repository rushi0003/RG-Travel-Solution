"""
Backfill employee pickup/drop location fields from home location fields.

Why:
- Group creation/assignment reads pickup/home/drop coordinates.
- Older employee rows may only have home_lat/home_lng populated.
- This utility synchronizes missing pickup/drop fields from home coordinates.

Usage:
  # Dry-run (default)
  python tools/backfill_employee_location_fields.py

  # Commit updates
  python tools/backfill_employee_location_fields.py --commit

  # Custom DB path
  python tools/backfill_employee_location_fields.py --db-path .\\rg_travel.db --commit
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = str(BACKEND_DIR / "rg_travel.db")


def _is_valid_coord(lat: Any, lng: Any) -> bool:
    try:
        latf = float(lat)
        lngf = float(lng)
    except Exception:
        return False
    return -90.0 <= latf <= 90.0 and -180.0 <= lngf <= 180.0 and not (latf == 0.0 and lngf == 0.0)


def _has_columns(cur: sqlite3.Cursor, table: str, needed: List[str]) -> Tuple[bool, List[str]]:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [str(r[1]) for r in cur.fetchall()]
    missing = [c for c in needed if c not in cols]
    return len(missing) == 0, missing


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def backfill(db_path: str, commit: bool = False) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    ok, missing = _has_columns(
        cur,
        "employees",
        [
            "id",
            "home_address",
            "home_lat",
            "home_lng",
            "pickup_address",
            "pickup_lat",
            "pickup_lng",
            "drop_location",
            "drop_lat",
            "drop_lng",
        ],
    )
    if not ok:
        raise RuntimeError(f"employees table missing required columns: {missing}")

    cur.execute(
        """
        SELECT id, home_address, home_lat, home_lng,
               pickup_address, pickup_lat, pickup_lng,
               drop_location, drop_lat, drop_lng
        FROM employees
        ORDER BY id ASC
        """
    )
    rows = [_row_to_dict(r) for r in cur.fetchall()]

    updates = 0
    skipped = 0
    for r in rows:
        emp_id = int(r["id"])
        h_lat = r.get("home_lat")
        h_lng = r.get("home_lng")
        h_addr = (r.get("home_address") or "").strip()

        if not _is_valid_coord(h_lat, h_lng):
            skipped += 1
            continue

        # keep existing non-empty values; fill only missing/invalid fields
        pickup_lat = r.get("pickup_lat")
        pickup_lng = r.get("pickup_lng")
        drop_lat = r.get("drop_lat")
        drop_lng = r.get("drop_lng")
        pickup_address = (r.get("pickup_address") or "").strip()
        drop_location = (r.get("drop_location") or "").strip()

        new_pickup_lat = float(h_lat) if not _is_valid_coord(pickup_lat, pickup_lng) else pickup_lat
        new_pickup_lng = float(h_lng) if not _is_valid_coord(pickup_lat, pickup_lng) else pickup_lng
        new_drop_lat = float(h_lat) if not _is_valid_coord(drop_lat, drop_lng) else drop_lat
        new_drop_lng = float(h_lng) if not _is_valid_coord(drop_lat, drop_lng) else drop_lng
        new_pickup_address = h_addr if (not pickup_address and h_addr) else pickup_address
        new_drop_location = h_addr if (not drop_location and h_addr) else drop_location

        changed = (
            new_pickup_lat != pickup_lat
            or new_pickup_lng != pickup_lng
            or new_drop_lat != drop_lat
            or new_drop_lng != drop_lng
            or new_pickup_address != pickup_address
            or new_drop_location != drop_location
        )
        if not changed:
            continue

        updates += 1
        print(
            f"EMP#{emp_id}: pickup({pickup_lat},{pickup_lng})->({new_pickup_lat},{new_pickup_lng}), "
            f"drop({drop_lat},{drop_lng})->({new_drop_lat},{new_drop_lng})"
        )

        if commit:
            cur.execute(
                """
                UPDATE employees
                SET pickup_address = ?, pickup_lat = ?, pickup_lng = ?,
                    drop_location = ?, drop_lat = ?, drop_lng = ?
                WHERE id = ?
                """,
                (
                    new_pickup_address or None,
                    new_pickup_lat,
                    new_pickup_lng,
                    new_drop_location or None,
                    new_drop_lat,
                    new_drop_lng,
                    emp_id,
                ),
            )

    if commit:
        conn.commit()
    conn.close()

    mode = "COMMIT" if commit else "DRY-RUN"
    print(f"\n[{mode}] total={len(rows)}, updated={updates}, skipped_invalid_home={skipped}")
    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill employee pickup/drop coordinates from home coordinates")
    parser.add_argument("--db-path", default=os.getenv("RG_DB_PATH", DEFAULT_DB_PATH))
    parser.add_argument("--commit", action="store_true", help="Persist updates. Default is dry-run.")
    args = parser.parse_args()

    db_path = str(args.db_path)
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found: {db_path}")

    backfill(db_path=db_path, commit=bool(args.commit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

