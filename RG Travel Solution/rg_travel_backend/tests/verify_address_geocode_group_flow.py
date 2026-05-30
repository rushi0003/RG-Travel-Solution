"""
Step-5 verifier for geocode-first grouping flow.

Covers:
1) /api/health/geocoding readiness contract
2) Admin employee create (address-only) auto-geocodes and stores lat/lng
3) Group preview rejects unresolved employee coordinates
4) Group preview succeeds for resolved employees

Run:
  python rg_travel_backend/tests/verify_address_geocode_group_flow.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_PATH = BACKEND_DIR / f"test_geocode_flow_{int(time.time() * 1000)}.db"
SCHEMA_PATH = BACKEND_DIR / "db" / "schema.sql"


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(r[1] == column_name for r in cur.fetchall())


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str) -> None:
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def _prepare_db() -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    _ensure_column(conn, "drivers", "driver_id", "TEXT")
    _ensure_column(conn, "drivers", "phone", "TEXT")
    _ensure_column(conn, "drivers", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "drivers", "hometown_lat", "REAL")
    _ensure_column(conn, "drivers", "hometown_lng", "REAL")
    _ensure_column(conn, "employees", "is_assigned", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "employees", "employee_id", "TEXT")
    _ensure_column(conn, "trips", "time_slot", "TEXT")

    now = "2026-03-03T00:00:00"
    conn.execute(
        """
        INSERT INTO admins (id, name, mobile, email, office_name, office_location, office_address,
                            password_salt, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("admin_001", "Admin", "9999999999", "admin@rg.com", "RG Office", "19.0760,72.8777", "Mumbai", "salt", "hash", now, now),
    )
    conn.execute(
        """
        INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town,
                             is_approved, password_salt, password_hash, created_at, updated_at,
                             driver_id, phone, is_active, hometown_lat, hometown_lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        ("drv_001", "Driver One", "9876500001", "DL0001", "MH12AB1234", "4", "Mumbai", "salt", "hash", now, now, "drv_001", "9876500001", 19.11, 72.91),
    )
    conn.commit()
    conn.close()


class _MockNominatimResponse:
    def __init__(self, lat: float = 19.1122, lng: float = 72.9101):
        self.lat = lat
        self.lng = lng

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return [
            {
                "lat": str(self.lat),
                "lon": str(self.lng),
                "display_name": "Mocked Address, Mumbai, India",
            }
        ]


class _MockOsrmResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return {"distances": [[900.0]]}


def run() -> int:
    os.environ["RG_DB_PATH"] = str(TEST_DB_PATH)
    os.environ["HYBRID_ROUTE_PROVIDER"] = "osrm"
    os.environ["OSRM_TABLE_URL"] = "http://router.project-osrm.org/table/v1/driving"

    sys.path.insert(0, str(BACKEND_DIR))
    from app import app  # type: ignore
    import services.nominatim_geocoding_service as nominatim_service  # type: ignore
    import services.hybrid_group_planner as hybrid_service  # type: ignore

    _prepare_db()

    original_get = nominatim_service.requests.get

    def _mock_get(url: str, *args: Any, **kwargs: Any) -> Any:
        u = str(url or "").lower()
        if "nominatim" in u or "/search" in u:
            return _MockNominatimResponse()
        if "osrm" in u or "/table" in u:
            return _MockOsrmResponse()
        return _MockNominatimResponse()

    # NOTE: both services share the same imported requests module object.
    nominatim_service.requests.get = _mock_get
    hybrid_service.requests.get = _mock_get

    client = app.test_client()

    try:
        # 1) geocoding health endpoint
        h = client.get("/api/health/geocoding")
        h_body = h.get_json() or {}
        _require(h.status_code == 200 and h_body.get("success"), f"health/geocoding failed: {h_body}")

        # 2) create employees with address-only (no lat/lng)
        created_ids: List[int] = []
        for idx in range(1, 5):
            res = client.post(
                "/api/admin/employees",
                json={
                    "name": f"Emp {idx}",
                    "mobile": f"90000000{idx:02d}",
                    "login_time": "09:00",
                    "logout_time": "18:00",
                    "address": "Kalyan, Maharashtra",
                },
            )
            body = res.get_json() or {}
            _require(res.status_code == 200 and body.get("success"), f"create employee failed: {body}")
            created_ids.append(int((body.get("data") or {}).get("employee_id")))

        # validate saved coords are non-zero
        conn = sqlite3.connect(str(TEST_DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        ph = ",".join(["?"] * len(created_ids))
        cur.execute(f"SELECT id, home_lat, home_lng FROM employees WHERE id IN ({ph})", tuple(created_ids))
        rows = cur.fetchall()
        _require(len(rows) == 4, "created employees missing in DB")
        for r in rows:
            lat = float(r["home_lat"] or 0)
            lng = float(r["home_lng"] or 0)
            _require(abs(lat) > 0.000001 and abs(lng) > 0.000001, f"coords not saved for employee {r['id']}")

        # 3) add one unresolved employee and verify preview rejects
        cur.execute(
            """
            INSERT INTO employees
            (id, name, mobile, employee_id, login_time, logout_time, home_address, home_lat, home_lng, is_active, is_approved, created_at, updated_at, is_assigned)
            VALUES (?, ?, ?, ?, '09:00', '18:00', ?, NULL, NULL, 1, 1, datetime('now'), datetime('now'), 0)
            """,
            (999, "Unresolved Emp", "9111111111", "999", ""),
        )
        conn.commit()
        conn.close()

        bad_preview = client.post(
            "/api/grouping/preview",
            json={
                "admin_id": "admin_001",
                "trip_type": "pickup",
                "time_slot": "09:00",
                "vehicle_types": [4],
                "driver_ids": ["drv_001"],
                "selected_employee_ids": [999],
            },
        )
        bad_body = bad_preview.get_json() or {}
        _require(bad_preview.status_code == 400, f"expected 400 for unresolved coords, got {bad_preview.status_code}")
        _require((bad_body.get("error") or {}).get("code") == "NO_VALID_COORDINATES", f"unexpected error code: {bad_body}")

        # 4) preview with resolved employees should succeed
        ok_preview = client.post(
            "/api/grouping/preview",
            json={
                "admin_id": "admin_001",
                "trip_type": "pickup",
                "time_slot": "09:00",
                "vehicle_types": [4],
                "driver_ids": ["drv_001"],
                "selected_employee_ids": created_ids,
            },
        )
        ok_body = ok_preview.get_json() or {}
        _require(ok_preview.status_code == 200 and ok_body.get("success"), f"grouping preview failed: {ok_body}")
        groups = (ok_body.get("data") or {}).get("groups") or []
        _require(len(groups) >= 1, "resolved preview returned no groups")

        print("RESULT: PASS")
        print(
            json.dumps(
                {
                    "created_employee_ids": created_ids,
                    "groups_count": len(groups),
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(f"RESULT: FAIL - {exc}")
        return 1
    finally:
        nominatim_service.requests.get = original_get
        hybrid_service.requests.get = original_get
        os.environ.pop("RG_DB_PATH", None)
        os.environ.pop("HYBRID_ROUTE_PROVIDER", None)
        os.environ.pop("OSRM_TABLE_URL", None)
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()


if __name__ == "__main__":
    raise SystemExit(run())
