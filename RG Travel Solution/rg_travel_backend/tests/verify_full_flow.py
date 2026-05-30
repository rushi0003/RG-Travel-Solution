"""
Step 10 verifier: Group Creation & Trip Assignment full backend flow.

What this script does:
1. Creates an isolated SQLite test DB.
2. Seeds minimal admin + drivers + vehicles + employees.
3. Calls required APIs (time-slots, available employees/vehicles, grouping preview, trips create).
4. Verifies DB writes (trips, trip_groups, trip_group_members) and route_no uniqueness.
5. Prints a final report and exits non-zero on failure.

Run:
    python rg_travel_backend/tests/verify_full_flow.py
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
ROOT_DIR = BACKEND_DIR.parent
TEST_DB_PATH = BACKEND_DIR / f"test_full_flow_step10_{int(time.time() * 1000)}.db"
SCHEMA_PATH = BACKEND_DIR / "db" / "schema.sql"


def _log(msg: str) -> None:
    print(msg)


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(r[1] == column_name for r in cur.fetchall())


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str) -> None:
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def _prepare_test_db() -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)

    # Step-3 compatibility fields expected by current flow.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no TEXT NOT NULL UNIQUE,
            vehicle_type INTEGER NOT NULL CHECK(vehicle_type IN (4, 6)),
            is_available INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _ensure_column(conn, "employees", "employee_id", "TEXT")
    _ensure_column(conn, "employees", "is_assigned", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "drivers", "driver_id", "TEXT")
    _ensure_column(conn, "drivers", "phone", "TEXT")
    _ensure_column(conn, "drivers", "is_active", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "drivers", "vehicle_id", "INTEGER")
    _ensure_column(conn, "drivers", "hometown_lat", "REAL")
    _ensure_column(conn, "drivers", "hometown_lng", "REAL")
    _ensure_column(conn, "trips", "time_slot", "TEXT")
    _ensure_column(conn, "trips", "vehicle_id", "INTEGER")
    _ensure_column(conn, "trips", "route_polyline", "TEXT")
    _ensure_column(conn, "trip_groups", "group_id", "TEXT")
    _ensure_column(conn, "trip_groups", "route_no", "TEXT")
    _ensure_column(conn, "trip_groups", "capacity", "INTEGER")
    _ensure_column(conn, "trip_groups", "vehicle_id", "INTEGER")
    _ensure_column(conn, "trip_groups", "driver_id", "TEXT")
    _ensure_column(conn, "trip_group_members", "sequence_no", "INTEGER")
    _ensure_column(conn, "trip_group_members", "pickup_drop_status", "TEXT")

    conn.commit()
    conn.close()


def _seed_minimal_data() -> None:
    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    now = "2026-02-24T00:00:00"

    cur.execute(
        """
        INSERT INTO admins (id, name, mobile, email, office_name, office_location, office_address,
                            password_salt, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "admin_001",
            "Admin One",
            "9999999999",
            "admin@rg.com",
            "RG Office",
            "19.0760,72.8777",
            "Mumbai",
            "salt",
            "hash",
            now,
            now,
        ),
    )

    # Vehicles first (drivers can map using vehicle_id).
    cur.execute(
        "INSERT INTO vehicles (vehicle_no, vehicle_type, is_available, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
        ("MH12AB1234", 6, now, now),
    )
    v1_id = cur.lastrowid
    cur.execute(
        "INSERT INTO vehicles (vehicle_no, vehicle_type, is_available, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
        ("MH12AB5678", 4, now, now),
    )
    v2_id = cur.lastrowid

    cur.execute(
        """
        INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town,
                             is_approved, password_salt, password_hash, created_at, updated_at,
                             driver_id, phone, is_active, vehicle_id, hometown_lat, hometown_lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            "drv_001",
            "Driver One",
            "9876500001",
            "DL0001",
            "MH12AB1234",
            "6",
            "Mumbai",
            "salt",
            "hash",
            now,
            now,
            "drv_001",
            "9876500001",
            v1_id,
            19.10,
            72.90,
        ),
    )
    cur.execute(
        """
        INSERT INTO drivers (id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town,
                             is_approved, password_salt, password_hash, created_at, updated_at,
                             driver_id, phone, is_active, vehicle_id, hometown_lat, hometown_lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            "drv_002",
            "Driver Two",
            "9876500002",
            "DL0002",
            "MH12AB5678",
            "4",
            "Mumbai",
            "salt",
            "hash",
            now,
            now,
            "drv_002",
            "9876500002",
            v2_id,
            19.05,
            72.86,
        ),
    )

    # Six employees in same pickup slot to form one 6-seater group.
    employees = [
        (31, "Emp 1", "9000000001", "19.1001", "72.9001"),
        (32, "Emp 2", "9000000002", "19.1002", "72.9002"),
        (33, "Emp 3", "9000000003", "19.1003", "72.9003"),
        (34, "Emp 4", "9000000004", "19.1004", "72.9004"),
        (35, "Emp 5", "9000000005", "19.1005", "72.9005"),
        (36, "Emp 6", "9000000006", "19.1006", "72.9006"),
    ]
    for emp_id, name, mobile, lat, lng in employees:
        cur.execute(
            """
            INSERT INTO employees (
                id, name, mobile, login_time, logout_time,
                home_address, home_lat, home_lng,
                pickup_address, pickup_lat, pickup_lng,
                is_active, is_approved, created_at, updated_at,
                employee_id, is_assigned
            ) VALUES (?, ?, ?, '09:00', '18:00',
                      'Mumbai', ?, ?, 'Mumbai', ?, ?,
                      1, 1, ?, ?, ?, 0)
            """,
            (emp_id, name, mobile, float(lat), float(lng), float(lat), float(lng), now, now, str(emp_id)),
        )

    conn.commit()
    conn.close()


def _verify_db_integrity() -> Dict[str, Any]:
    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(1) AS c FROM trips")
    trips_count = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(1) AS c FROM trip_groups")
    groups_count = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(1) AS c FROM trip_group_members")
    members_count = int(cur.fetchone()["c"])

    cur.execute("SELECT COUNT(route_no) AS total, COUNT(DISTINCT route_no) AS unique_count FROM trips")
    row = cur.fetchone()
    route_total = int(row["total"])
    route_unique = int(row["unique_count"])

    conn.close()
    return {
        "trips_count": trips_count,
        "groups_count": groups_count,
        "members_count": members_count,
        "route_total": route_total,
        "route_unique": route_unique,
        "route_no_unique_ok": route_total == route_unique,
    }


class _MockOsrmResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        # OSRM table shape used by HybridDistance._road_km_osrm
        return {"distances": [[1200.0]]}


def run() -> int:
    os.environ["RG_DB_PATH"] = str(TEST_DB_PATH)
    # Mandatory hybrid planner config for upgraded flow.
    os.environ["HYBRID_ROUTE_PROVIDER"] = os.environ.get("HYBRID_ROUTE_PROVIDER", "osrm")
    os.environ["OSRM_TABLE_URL"] = os.environ.get(
        "OSRM_TABLE_URL", "http://router.project-osrm.org/table/v1/driving"
    )

    # Add backend dir to import path and import app lazily after DB env setup.
    sys.path.insert(0, str(BACKEND_DIR))
    from app import app  # type: ignore
    import services.hybrid_group_planner as hybrid_group_planner  # type: ignore

    _log("=== Step 10 Full Flow Verification ===")
    _prepare_test_db()
    _seed_minimal_data()

    # Seed one approved go-home request so priority path is exercised.
    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.execute(
        """
        INSERT INTO driver_hometown_requests
        (driver_id, requested_home_town, status, created_at, updated_at)
        VALUES (?, ?, 'approved', datetime('now'), datetime('now'))
        """,
        ("drv_001", "Mumbai"),
    )
    conn.commit()
    conn.close()

    client = app.test_client()
    report: Dict[str, Any] = {"checks": {}, "errors": []}
    original_osrm_get = hybrid_group_planner.requests.get
    hybrid_group_planner.requests.get = lambda *args, **kwargs: _MockOsrmResponse()

    try:
        # 0) Health
        res = client.get("/api/health")
        _require(res.status_code == 200, f"/api/health failed: {res.status_code}")
        report["checks"]["health"] = True

        # 0.1) Hybrid provider health
        res = client.get("/api/health/hybrid")
        body = res.get_json() or {}
        _require(res.status_code == 200 and body.get("success"), f"/api/health/hybrid failed: {body}")
        report["checks"]["hybrid_health"] = True

        # 1) Time slots
        res = client.get("/api/admin/time-slots?trip_type=pickup")
        body = res.get_json() or {}
        _require(res.status_code == 200 and body.get("success"), "time-slots endpoint failed")
        slots = body.get("data", {}).get("slots", [])
        _require("09:00" in slots, "09:00 missing in time-slots")
        report["checks"]["time_slots"] = True

        # 2) Available employees
        res = client.get("/api/admin/available-employees?trip_type=pickup&time_slot=09:00")
        body = res.get_json() or {}
        _require(res.status_code == 200 and body.get("success"), "available-employees failed")
        employees = body.get("data", {}).get("employees", [])
        _require(len(employees) >= 6, "available-employees expected >= 6")
        selected_employee_ids = [e["id"] for e in employees[:6]]
        report["checks"]["available_employees"] = True

        # 3) Available vehicles
        res = client.get("/api/admin/available-vehicles?vehicle_type=6")
        body = res.get_json() or {}
        _require(res.status_code == 200 and body.get("success"), "available-vehicles failed")
        vehicles = body.get("data", {}).get("vehicles", [])
        _require(len(vehicles) >= 1, "available-vehicles expected >= 1")
        selected_vehicle_id = vehicles[0].get("vehicle_id")
        selected_driver_id = (vehicles[0].get("driver") or {}).get("driver_id")
        _require(selected_driver_id is not None, "vehicle driver_id missing")
        report["checks"]["available_vehicles"] = True

        # 4) Group preview
        preview_payload = {
            "trip_type": "pickup",
            "time_slot": "09:00",
            "vehicle_types": [6, 4],
            "selected_vehicle_ids": [selected_vehicle_id] if selected_vehicle_id else [],
            "selected_employee_ids": selected_employee_ids,
            "allow_partial_group": False,
            "admin_id": "admin_001",
        }
        res = client.post("/api/grouping/preview", json=preview_payload)
        body = res.get_json() or {}
        _require(res.status_code == 200 and body.get("success"), f"grouping preview failed: {body}")
        data_block = body.get("data", {})
        _require(bool(data_block.get("hybrid_strict")), "grouping preview hybrid_strict must be true")
        _require(
            str(data_block.get("hybrid_provider", "")).lower() in ("osrm", "ors"),
            "grouping preview hybrid_provider missing/invalid",
        )
        _require("hybrid_degraded_edges" in data_block, "grouping preview missing hybrid_degraded_edges")
        groups = body.get("data", {}).get("groups", [])
        _require(len(groups) >= 1, "grouping preview returned no groups")
        _require("unassigned_vehicles" in data_block, "grouping preview missing unassigned_vehicles")
        report["checks"]["grouping_preview"] = True

        # 5) Trips create
        create_groups = []
        for g in groups:
            create_groups.append(
                {
                    "capacity": g.get("capacity", 6),
                    "employee_ids": [m["id"] for m in g.get("employees", [])],
                    "vehicle_id": selected_vehicle_id,
                    "driver_id": selected_driver_id,
                }
            )

        create_payload = {
            "trip_type": "pickup",
            "time_slot": "09:00",
            "groups": create_groups,
            "admin_id": "admin_001",
        }
        res = client.post("/api/trips/create", json=create_payload)
        body = res.get_json() or {}
        _require(res.status_code == 201 and body.get("success"), f"trips/create failed: {body}")

        data = body.get("data", {})
        _require("routeNo" in data, "routeNo missing in create response")
        _require("timeSlot" in data and data["timeSlot"] == "09:00", "timeSlot missing or invalid")
        _require("tripType" in data and data["tripType"] == "pickup", "tripType missing or invalid")
        _require("trips" in data and len(data["trips"]) >= 1, "trips payload missing")
        report["checks"]["trips_create"] = True

        # 6) DB verification
        db_verify = _verify_db_integrity()
        _require(db_verify["trips_count"] >= 1, "DB verify failed: no trips inserted")
        _require(db_verify["groups_count"] >= 1, "DB verify failed: no trip_groups inserted")
        _require(db_verify["members_count"] >= 1, "DB verify failed: no trip_group_members inserted")
        _require(db_verify["route_no_unique_ok"], "DB verify failed: route_no is not unique")
        report["checks"]["db_verification"] = True
        report["db"] = db_verify

        _log("\n=== FINAL REPORT ===")
        _log(json.dumps(report, indent=2))
        _log("RESULT: PASS")
        return 0

    except Exception as exc:
        report["errors"].append(str(exc))
        _log("\n=== FINAL REPORT ===")
        _log(json.dumps(report, indent=2))
        _log("RESULT: FAIL")
        return 1
    finally:
        hybrid_group_planner.requests.get = original_osrm_get
        os.environ.pop("RG_DB_PATH", None)
        os.environ.pop("HYBRID_ROUTE_PROVIDER", None)
        os.environ.pop("OSRM_TABLE_URL", None)
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()


if __name__ == "__main__":
    raise SystemExit(run())
