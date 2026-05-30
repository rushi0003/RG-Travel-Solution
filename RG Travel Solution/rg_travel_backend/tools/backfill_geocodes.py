"""
Backfill missing employee/driver coordinates using OpenStreetMap Nominatim.

Flow:
Address text -> Geocoding -> lat/lng save

Usage:
  python rg_travel_backend/tools/backfill_geocodes.py --dry-run
  python rg_travel_backend/tools/backfill_geocodes.py --commit --limit 500
  python rg_travel_backend/tools/backfill_geocodes.py --entity employees --commit
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = str(BACKEND_DIR / "rg_travel.db")

sys.path.insert(0, str(BACKEND_DIR))

from services.nominatim_geocoding_service import (  # type: ignore
    ensure_geocode_cache_table,
    geocode_address_nominatim,
)


def _is_valid_coord(lat: Any, lng: Any) -> bool:
    try:
        latf = float(lat)
        lngf = float(lng)
    except Exception:
        return False
    return -90.0 <= latf <= 90.0 and -180.0 <= lngf <= 180.0 and not (latf == 0.0 and lngf == 0.0)


def _fetch_employees_missing(cur: sqlite3.Cursor, limit: int) -> List[sqlite3.Row]:
    cur.execute(
        """
        SELECT id, home_address, home_lat, home_lng
        FROM employees
        WHERE TRIM(COALESCE(home_address, '')) <> ''
          AND (
            home_lat IS NULL OR home_lng IS NULL
            OR ABS(COALESCE(home_lat, 0)) < 0.000001
            OR ABS(COALESCE(home_lng, 0)) < 0.000001
          )
        ORDER BY id ASC
        LIMIT ?
        """,
        (int(limit),),
    )
    return cur.fetchall() or []


def _fetch_drivers_missing(cur: sqlite3.Cursor, limit: int) -> List[sqlite3.Row]:
    cur.execute("PRAGMA table_info(drivers)")
    dcols = {str(r[1]) for r in cur.fetchall()}

    if "hometown_lat" in dcols and "hometown_lng" in dcols:
        lat_col = "hometown_lat"
        lng_col = "hometown_lng"
    elif "home_lat" in dcols and "home_lng" in dcols:
        lat_col = "home_lat"
        lng_col = "home_lng"
    else:
        return []

    cur.execute(
        f"""
        SELECT id, COALESCE(home_town, '') AS home_town, {lat_col} AS lat_col, {lng_col} AS lng_col
        FROM drivers
        WHERE TRIM(COALESCE(home_town, '')) <> ''
          AND (
            {lat_col} IS NULL OR {lng_col} IS NULL
            OR ABS(COALESCE({lat_col}, 0)) < 0.000001
            OR ABS(COALESCE({lng_col}, 0)) < 0.000001
          )
        ORDER BY id ASC
        LIMIT ?
        """,
        (int(limit),),
    )
    return cur.fetchall() or []


def _update_driver_coords(cur: sqlite3.Cursor, driver_id: Any, lat: float, lng: float) -> None:
    cur.execute("PRAGMA table_info(drivers)")
    dcols = {str(r[1]) for r in cur.fetchall()}
    updates: List[str] = []
    params: List[Any] = []
    if "hometown_lat" in dcols:
        updates.append("hometown_lat = ?")
        params.append(lat)
    if "hometown_lng" in dcols:
        updates.append("hometown_lng = ?")
        params.append(lng)
    if "home_lat" in dcols:
        updates.append("home_lat = ?")
        params.append(lat)
    if "home_lng" in dcols:
        updates.append("home_lng = ?")
        params.append(lng)
    if not updates:
        return
    params.append(driver_id)
    cur.execute(f"UPDATE drivers SET {', '.join(updates)} WHERE id = ?", tuple(params))


def run(db_path: str, entity: str, limit: int, commit: bool, sleep_ms: int) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_geocode_cache_table(conn)
    cur = conn.cursor()

    stats: Dict[str, int] = {
        "employees_scanned": 0,
        "employees_updated": 0,
        "drivers_scanned": 0,
        "drivers_updated": 0,
        "geocode_failed": 0,
        "already_valid_skipped": 0,
    }

    try:
        if entity in ("employees", "both"):
            rows = _fetch_employees_missing(cur, limit)
            stats["employees_scanned"] = len(rows)
            for row in rows:
                emp_id = row["id"]
                addr = str(row["home_address"] or "").strip()
                if not addr:
                    continue
                if _is_valid_coord(row["home_lat"], row["home_lng"]):
                    stats["already_valid_skipped"] += 1
                    continue

                geo = geocode_address_nominatim(addr, conn=conn, use_cache=True)
                if geo.get("success") is not True:
                    stats["geocode_failed"] += 1
                    continue
                data = geo.get("data") or {}
                lat = data.get("lat")
                lng = data.get("lng")
                if not _is_valid_coord(lat, lng):
                    stats["geocode_failed"] += 1
                    continue

                cur.execute(
                    "UPDATE employees SET home_lat = ?, home_lng = ? WHERE id = ?",
                    (float(lat), float(lng), emp_id),
                )
                stats["employees_updated"] += 1
                if sleep_ms > 0 and not data.get("from_cache"):
                    time.sleep(float(sleep_ms) / 1000.0)

        if entity in ("drivers", "both"):
            rows = _fetch_drivers_missing(cur, limit)
            stats["drivers_scanned"] = len(rows)
            for row in rows:
                driver_id = row["id"]
                town = str(row["home_town"] or "").strip()
                if not town:
                    continue
                if _is_valid_coord(row["lat_col"], row["lng_col"]):
                    stats["already_valid_skipped"] += 1
                    continue

                geo = geocode_address_nominatim(town, conn=conn, use_cache=True)
                if geo.get("success") is not True:
                    stats["geocode_failed"] += 1
                    continue
                data = geo.get("data") or {}
                lat = data.get("lat")
                lng = data.get("lng")
                if not _is_valid_coord(lat, lng):
                    stats["geocode_failed"] += 1
                    continue

                _update_driver_coords(cur, driver_id, float(lat), float(lng))
                stats["drivers_updated"] += 1
                if sleep_ms > 0 and not data.get("from_cache"):
                    time.sleep(float(sleep_ms) / 1000.0)

        if commit:
            conn.commit()
            print("Mode: COMMIT")
        else:
            conn.rollback()
            print("Mode: DRY-RUN (no DB changes saved)")

        print(f"DB: {db_path}")
        print(stats)
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: {exc}")
        return 1
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=os.getenv("RG_DB_PATH", DEFAULT_DB_PATH))
    parser.add_argument("--entity", choices=["employees", "drivers", "both"], default="both")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--sleep-ms", type=int, default=1000)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    commit = bool(args.commit and not args.dry_run)
    return run(
        db_path=str(args.db_path),
        entity=str(args.entity),
        limit=max(1, int(args.limit)),
        commit=commit,
        sleep_ms=max(0, int(args.sleep_ms)),
    )


if __name__ == "__main__":
    raise SystemExit(main())

