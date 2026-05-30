"""
Safe, idempotent apply script for Step 3 migration.

Usage:
  python apply_migration_008_group_creation.py
"""

import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "rg_travel.db"
MIGRATION_PATH = ROOT / "db" / "migrations" / "008_group_creation_flow.sql"

REQUIRED_TABLES = [
    "employees",
    "drivers",
    "vehicles",
    "trips",
    "trip_groups",
    "trip_group_members",
]

REQUIRED_COLUMNS = {
    "employees": ["employee_id", "login_time", "logout_time", "home_address", "home_lat", "home_lng", "is_active", "is_assigned"],
    "drivers": ["driver_id", "phone", "is_approved", "is_active", "hometown_lat", "hometown_lng", "vehicle_id"],
    "vehicles": ["vehicle_id", "vehicle_no", "vehicle_type", "is_available"],
    "trips": ["route_no", "trip_type", "time_slot", "driver_id", "vehicle_id", "status", "total_km", "route_polyline"],
    "trip_groups": ["group_id", "route_no", "capacity", "vehicle_id", "driver_id"],
    "trip_group_members": ["group_id", "employee_id", "sequence_no", "pickup_drop_status"],
}

REQUIRED_INDEXES = [
    "idx_employees_login_logout",
    "idx_trips_time_slot_status",
    "idx_trip_group_members_group",
]


def table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def column_exists(cur: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cur.fetchall())


def index_exists(cur: sqlite3.Cursor, index_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cur.fetchone() is not None


def ensure_column(cur: sqlite3.Cursor, table: str, column: str, column_def: str) -> None:
    if not column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")


def ensure_index(cur: sqlite3.Cursor, name: str, sql: str) -> None:
    if not index_exists(cur, name):
        cur.execute(sql)


def verify_schema(cur: sqlite3.Cursor) -> list[str]:
    missing: list[str] = []

    for table in REQUIRED_TABLES:
        if not table_exists(cur, table):
            missing.append(f"table:{table}")

    for table, cols in REQUIRED_COLUMNS.items():
        if not table_exists(cur, table):
            continue
        for col in cols:
            if not column_exists(cur, table, col):
                missing.append(f"column:{table}.{col}")

    for idx in REQUIRED_INDEXES:
        if not index_exists(cur, idx):
            missing.append(f"index:{idx}")

    return missing


def apply_migration(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # 1) vehicles table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no      TEXT NOT NULL UNIQUE,
            vehicle_type    INTEGER NOT NULL CHECK(vehicle_type IN (4, 6)),
            is_available    INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0,1)),
            created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_index(
        cur,
        "idx_vehicles_type_available",
        "CREATE INDEX idx_vehicles_type_available ON vehicles(vehicle_type, is_available)",
    )

    # 2) employees
    ensure_column(cur, "employees", "employee_id", "TEXT")
    ensure_column(cur, "employees", "is_assigned", "INTEGER NOT NULL DEFAULT 0 CHECK(is_assigned IN (0,1))")

    cur.execute("UPDATE employees SET employee_id = CAST(id AS TEXT) WHERE employee_id IS NULL")

    ensure_index(
        cur,
        "uq_employees_employee_id",
        "CREATE UNIQUE INDEX uq_employees_employee_id ON employees(employee_id)",
    )
    ensure_index(
        cur,
        "idx_employees_login_logout",
        "CREATE INDEX idx_employees_login_logout ON employees(login_time, logout_time)",
    )

    # 3) drivers
    ensure_column(cur, "drivers", "driver_id", "TEXT")
    ensure_column(cur, "drivers", "phone", "TEXT")
    ensure_column(cur, "drivers", "is_active", "INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))")
    ensure_column(cur, "drivers", "hometown_lat", "REAL")
    ensure_column(cur, "drivers", "hometown_lng", "REAL")
    ensure_column(cur, "drivers", "vehicle_id", "INTEGER")

    cur.execute("UPDATE drivers SET driver_id = id WHERE driver_id IS NULL")
    cur.execute("UPDATE drivers SET phone = mobile WHERE phone IS NULL")

    ensure_index(
        cur,
        "uq_drivers_driver_id",
        "CREATE UNIQUE INDEX uq_drivers_driver_id ON drivers(driver_id)",
    )
    ensure_index(
        cur,
        "idx_drivers_active_approved",
        "CREATE INDEX idx_drivers_active_approved ON drivers(is_active, is_approved)",
    )
    ensure_index(
        cur,
        "idx_drivers_vehicle_id",
        "CREATE INDEX idx_drivers_vehicle_id ON drivers(vehicle_id)",
    )

    # 4) trips
    ensure_column(cur, "trips", "time_slot", "TEXT")
    ensure_column(cur, "trips", "vehicle_id", "INTEGER")
    ensure_column(cur, "trips", "route_polyline", "TEXT")

    cur.execute("UPDATE trips SET time_slot = schedule_time WHERE time_slot IS NULL")
    cur.execute("UPDATE trips SET route_polyline = polyline WHERE route_polyline IS NULL")

    ensure_index(
        cur,
        "idx_trips_time_slot_status",
        "CREATE INDEX idx_trips_time_slot_status ON trips(time_slot, status)",
    )

    # 5) trip_groups
    ensure_column(cur, "trip_groups", "group_id", "TEXT")
    ensure_column(cur, "trip_groups", "route_no", "TEXT")
    ensure_column(cur, "trip_groups", "capacity", "INTEGER CHECK(capacity IN (4,6))")
    ensure_column(cur, "trip_groups", "vehicle_id", "INTEGER")
    ensure_column(cur, "trip_groups", "driver_id", "TEXT")

    cur.execute("UPDATE trip_groups SET group_id = 'GRP-' || id WHERE group_id IS NULL")

    ensure_index(
        cur,
        "uq_trip_groups_group_id",
        "CREATE UNIQUE INDEX uq_trip_groups_group_id ON trip_groups(group_id)",
    )
    ensure_index(
        cur,
        "idx_trip_groups_route_no",
        "CREATE INDEX idx_trip_groups_route_no ON trip_groups(route_no)",
    )

    # 6) trip_group_members
    ensure_column(cur, "trip_group_members", "sequence_no", "INTEGER")
    ensure_column(cur, "trip_group_members", "pickup_drop_status", "TEXT")

    cur.execute("UPDATE trip_group_members SET sequence_no = pickup_order WHERE sequence_no IS NULL")
    cur.execute("UPDATE trip_group_members SET pickup_drop_status = status WHERE pickup_drop_status IS NULL")

    ensure_index(
        cur,
        "idx_trip_group_members_group",
        "CREATE INDEX idx_trip_group_members_group ON trip_group_members(group_id)",
    )


def main() -> int:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        return 1

    if not MIGRATION_PATH.exists():
        print(f"ERROR: Migration SQL missing: {MIGRATION_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("BEGIN")
        apply_migration(conn)
        conn.commit()

        cur = conn.cursor()
        missing = verify_schema(cur)
        if missing:
            print("ERROR: Verification failed.")
            for item in missing:
                print(f" - missing {item}")
            return 1

        print("SUCCESS: Step 3 migration applied and verified.")
        print(f"DB: {DB_PATH}")
        print(f"Migration SQL: {MIGRATION_PATH}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: Migration failed and rolled back: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
