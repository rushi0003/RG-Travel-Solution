# rg_travel_backend/db/migrate.py
"""
Idempotent Database Migration Script
STEP 2: Safely upgrade existing RG Travel Solution database to new schema

This script:
1. Checks for existing columns and tables
2. Adds missing columns using ALTER TABLE
3. Creates missing tables
4. Creates missing indexes
5. Safe to run multiple times (idempotent)

Usage:
    python -m rg_travel_backend.db.migrate
    or
    python migrate.py  (from db/ directory)
"""

import builtins
import sqlite3
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from db import get_db, get_db_path
    from db.schema_guard import ensure_group_flow_schema
except ImportError:
    # Fallback if running as standalone script
    def get_db_path():
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "rg_travel.db")
    
    def get_db():
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def ensure_group_flow_schema(conn):
        return None


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def print(*args, **kwargs):
    """
    Keep migration output readable on Windows consoles that still use cp1252.
    Falls back to a replacement-safe write instead of crashing on emoji.
    """
    try:
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        file = kwargs.get("file", sys.stdout)
        text = sep.join(str(arg) for arg in args) + end
        encoding = getattr(file, "encoding", None) or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        file.write(safe)


def table_exists(conn, table_name):
    """Check if table exists."""
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cur.fetchone() is not None


def column_exists(conn, table_name, column_name):
    """Check if column exists in table."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cur.fetchall()]
    return column_name in columns


def index_exists(conn, index_name):
    """Check if index exists."""
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name=?
    """, (index_name,))
    return cur.fetchone() is not None


def migrate_employees_table(conn):
    """Add location fields to employees table."""
    print("📍 Migrating employees table...")
    
    columns_to_add = [
        ("home_address", "TEXT"),
        ("home_lat", "REAL"),
        ("home_lng", "REAL"),
        ("pickup_address", "TEXT"),
        ("pickup_lat", "REAL"),
        ("pickup_lng", "REAL"),
    ]
    
    for col_name, col_type in columns_to_add:
        if not column_exists(conn, "employees", col_name):
            print(f"  ✅ Adding column: {col_name}")
            conn.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  ⏭️  Column already exists: {col_name}")
    
    # Add indexes
    indexes = [
        ("idx_employees_home_coords", "employees(home_lat, home_lng)"),
        ("idx_employees_pickup_coords", "employees(pickup_lat, pickup_lng)"),
        ("idx_employees_drop_coords", "employees(drop_lat, drop_lng)"),
    ]
    
    for idx_name, idx_def in indexes:
        if not index_exists(conn, idx_name):
            print(f"  ✅ Creating index: {idx_name}")
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
        else:
            print(f"  ⏭️  Index already exists: {idx_name}")


def migrate_drivers_table(conn):
    """Add tracking fields to drivers table."""
    print("🚗 Migrating drivers table...")
    
    columns_to_add = [
        ("is_online", "INTEGER DEFAULT 0"),
        ("last_seen", "TEXT"),
    ]
    
    for col_name, col_type in columns_to_add:
        if not column_exists(conn, "drivers", col_name):
            print(f"  ✅ Adding column: {col_name}")
            conn.execute(f"ALTER TABLE drivers ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  ⏭️  Column already exists: {col_name}")
    
    # Add index
    if not index_exists(conn, "idx_drivers_online"):
        print(f"  ✅ Creating index: idx_drivers_online")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_drivers_online ON drivers(is_online, last_seen)")
    else:
        print(f"  ⏭️  Index already exists: idx_drivers_online")


def migrate_trips_table(conn):
    """Add new fields to trips table."""
    print("🚌 Migrating trips table...")
    
    columns_to_add = [
        ("operation", "TEXT CHECK(operation IN ('pickup','drop'))"),
        ("polyline", "TEXT"),
        ("route_json", "TEXT"),
        ("cancel_reason", "TEXT"),
        ("cancelled_by", "TEXT"),
        ("cancelled_at", "TEXT"),
        ("trip_date", "TEXT"),
        ("office_lat", "REAL"),
        ("office_lng", "REAL"),
        ("route_revision", "INTEGER DEFAULT 1"),
    ]
    
    for col_name, col_type in columns_to_add:
        if not column_exists(conn, "trips", col_name):
            print(f"  ✅ Adding column: {col_name}")
            conn.execute(f"ALTER TABLE trips ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  ⏭️  Column already exists: {col_name}")

    # Populate trip_date if missing
    if column_exists(conn, "trips", "trip_date") and column_exists(conn, "trips", "created_at"):
         print("  🔄 Populating trip_date from created_at...")
         conn.execute("UPDATE trips SET trip_date = SUBSTR(created_at, 1, 10) WHERE trip_date IS NULL")
    
    # Sync operation field with trip_type if needed
    if column_exists(conn, "trips", "operation") and column_exists(conn, "trips", "trip_type"):
        print("  🔄 Syncing operation field with trip_type...")
        conn.execute("UPDATE trips SET operation = trip_type WHERE operation IS NULL")
    
    # Add global route_no uniqueness index
    if not index_exists(conn, "uq_trips_route_no"):
        print(f"  ✅ Creating global uniqueness index: uq_trips_route_no")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_trips_route_no ON trips(route_no)")
    else:
        print(f"  ⏭️  Index already exists: uq_trips_route_no")
    
    # Add operation index
    if not index_exists(conn, "idx_trips_operation_time"):
        print(f"  ✅ Creating index: idx_trips_operation_time")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trips_operation_time ON trips(operation, schedule_time)")
    else:
        print(f"  ⏭️  Index already exists: idx_trips_operation_time")


def migrate_route_numbers_table(conn):
    """Ensure route_numbers has global uniqueness."""
    print("🔢 Migrating route_numbers table...")
    
    if not index_exists(conn, "uq_route_no_global"):
        print(f"  ✅ Creating global uniqueness index: uq_route_no_global")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_route_no_global ON route_numbers(route_no)")
    else:
        print(f"  ⏭️  Index already exists: uq_route_no_global")


def migrate_swap_requests_table(conn):
    """Add new fields to swap_requests table."""
    print("🔄 Migrating swap_requests table...")
    
    # Rename requested_by_driver_id to old_driver_id if needed
    if column_exists(conn, "swap_requests", "requested_by_driver_id") and not column_exists(conn, "swap_requests", "old_driver_id"):
        print("  🔄 Renaming requested_by_driver_id to old_driver_id...")
        # SQLite doesn't support ALTER TABLE RENAME COLUMN directly in old versions
        # We'll add new column and copy data
        conn.execute("ALTER TABLE swap_requests ADD COLUMN old_driver_id TEXT")
        conn.execute("UPDATE swap_requests SET old_driver_id = requested_by_driver_id")
    
    columns_to_add = [
        ("old_driver_id", "TEXT"),
        ("new_driver_name", "TEXT"),
        ("new_driver_mobile", "TEXT"),
        ("new_cab_no", "TEXT"),
        ("admin_notes", "TEXT"),
        ("reviewed_by", "TEXT"),
        ("reviewed_at", "TEXT"),
    ]
    
    for col_name, col_type in columns_to_add:
        if not column_exists(conn, "swap_requests", col_name):
            print(f"  ✅ Adding column: {col_name}")
            conn.execute(f"ALTER TABLE swap_requests ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  ⏭️  Column already exists: {col_name}")
    
    # Add index
    if not index_exists(conn, "idx_swap_old_driver"):
        print(f"  ✅ Creating index: idx_swap_old_driver")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_swap_old_driver ON swap_requests(old_driver_id)")
    else:
        print(f"  ⏭️  Index already exists: idx_swap_old_driver")


def migrate_driver_location_history_table(conn):
    """Add new fields to driver_location_history table."""
    print("📍 Migrating driver_location_history table...")
    
    columns_to_add = [
        ("route_no", "TEXT"),
        ("speed", "REAL"),
    ]
    
    for col_name, col_type in columns_to_add:
        if not column_exists(conn, "driver_location_history", col_name):
            print(f"  ✅ Adding column: {col_name}")
            conn.execute(f"ALTER TABLE driver_location_history ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  ⏭️  Column already exists: {col_name}")
    
    # Add index
    if not index_exists(conn, "idx_driver_location_route"):
        print(f"  ✅ Creating index: idx_driver_location_route")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_driver_location_route ON driver_location_history(route_no)")
    else:
        print(f"  ⏭️  Index already exists: idx_driver_location_route")


def migrate_trip_otps_table(conn):
    """Add new fields to trip_otps table."""
    print("🔐 Migrating trip_otps table...")

    if not table_exists(conn, "trip_otps"):
        print("  ✅ Creating table: trip_otps")
        conn.execute("""
            CREATE TABLE trip_otps (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id         INTEGER NOT NULL,
                otp_type        TEXT NOT NULL CHECK(otp_type IN ('start', 'end')),
                otp_hash        TEXT NOT NULL,
                expires_at      TEXT NOT NULL,
                is_used         INTEGER DEFAULT 0,
                used_at         TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                employee_id     TEXT,
                verified_by     TEXT,
                
                FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY(verified_by) REFERENCES drivers(id) ON DELETE SET NULL
            )
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_otp_type ON trip_otps(trip_id, otp_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trip_otp_employee ON trip_otps(employee_id)")
        return
    
    columns_to_add = [
        ("employee_id", "TEXT"),
        ("verified_by", "TEXT"),
    ]
    
    for col_name, col_type in columns_to_add:
        if not column_exists(conn, "trip_otps", col_name):
            print(f"  ✅ Adding column: {col_name}")
            conn.execute(f"ALTER TABLE trip_otps ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  ⏭️  Column already exists: {col_name}")
    
    # Add index
    if not index_exists(conn, "idx_trip_otp_employee"):
        print(f"  ✅ Creating index: idx_trip_otp_employee")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trip_otp_employee ON trip_otps(employee_id)")
    else:
        print(f"  ⏭️  Index already exists: idx_trip_otp_employee")


def migrate_otp_audit_log_table(conn):
    """Add new fields to otp_audit_log table."""
    print("📝 Migrating otp_audit_log table...")
    
    if not column_exists(conn, "otp_audit_log", "employee_id"):
        print(f"  ✅ Adding column: employee_id")
        conn.execute("ALTER TABLE otp_audit_log ADD COLUMN employee_id TEXT")
    else:
        print(f"  ⏭️  Column already exists: employee_id")


def create_new_tables(conn):
    """Create new tables that don't exist yet."""
    print("🆕 Creating new tables...")
    
    # employee_absences table
    if not table_exists(conn, "employee_absences"):
        print("  ✅ Creating table: employee_absences")
        conn.execute("""
            CREATE TABLE employee_absences (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              employee_id     TEXT NOT NULL,
              absence_date    TEXT NOT NULL,
              reason          TEXT,
              status          TEXT NOT NULL DEFAULT 'pending'
                              CHECK(status IN ('pending','approved','rejected')),
              requested_at    TEXT NOT NULL,
              reviewed_at     TEXT,
              reviewed_by     TEXT,
              created_at      TEXT NOT NULL,
              updated_at      TEXT NOT NULL,
              
              FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
              FOREIGN KEY(reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
            )
        """)
        conn.execute("CREATE UNIQUE INDEX uq_employee_absence_date ON employee_absences(employee_id, absence_date)")
        conn.execute("CREATE INDEX idx_absence_date ON employee_absences(absence_date)")
        conn.execute("CREATE INDEX idx_absence_status ON employee_absences(status)")
    else:
        print(f"  ⏭️  Table already exists: employee_absences")
    
    # legacy-compatible employee_absence_requests table
    if not table_exists(conn, "employee_absence_requests"):
        print("  âœ… Creating table: employee_absence_requests")
        conn.execute("""
            CREATE TABLE employee_absence_requests (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              employee_id     TEXT NOT NULL,
              absent_date     TEXT NOT NULL,
              reason          TEXT,
              status          TEXT NOT NULL DEFAULT 'pending'
                              CHECK(status IN ('pending','approved','rejected')),
              created_at      TEXT NOT NULL,
              updated_at      TEXT,

              FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_employee_absence_requests_date ON employee_absence_requests(absent_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_employee_absence_requests_status ON employee_absence_requests(status)")
    else:
        print(f"  â­ï¸  Table already exists: employee_absence_requests")

    # grouped absence / cancel-request flow tables
    if not table_exists(conn, "absence_request_batches"):
        print("  âœ… Creating table: absence_request_batches")
        conn.execute("""
            CREATE TABLE absence_request_batches (
              id                INTEGER PRIMARY KEY AUTOINCREMENT,
              employee_id       TEXT NOT NULL,
              request_kind      TEXT NOT NULL
                                CHECK(request_kind IN ('absence', 'cancel')),
              original_request_id INTEGER,
              from_date         TEXT NOT NULL,
              to_date           TEXT NOT NULL,
              total_days        INTEGER NOT NULL DEFAULT 1,
              reason            TEXT,
              status            TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending', 'approved', 'rejected')),
              admin_reason      TEXT,
              reviewed_by       TEXT,
              reviewed_at       TEXT,
              created_at        TEXT NOT NULL,
              updated_at        TEXT NOT NULL,

              FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE,
              FOREIGN KEY(original_request_id) REFERENCES absence_request_batches(id) ON DELETE SET NULL,
              FOREIGN KEY(reviewed_by) REFERENCES admins(id) ON DELETE SET NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_absence_batch_employee_status ON absence_request_batches(employee_id, status, request_kind)")
    else:
        print(f"  â­ï¸  Table already exists: absence_request_batches")

    if not table_exists(conn, "absence_request_batch_dates"):
        print("  âœ… Creating table: absence_request_batch_dates")
        conn.execute("""
            CREATE TABLE absence_request_batch_dates (
              id                INTEGER PRIMARY KEY AUTOINCREMENT,
              request_id        INTEGER NOT NULL,
              absence_date      TEXT NOT NULL,
              created_at        TEXT NOT NULL,

              UNIQUE(request_id, absence_date),
              FOREIGN KEY(request_id) REFERENCES absence_request_batches(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_absence_batch_dates_date ON absence_request_batch_dates(absence_date)")
    else:
        print(f"  â­ï¸  Table already exists: absence_request_batch_dates")

    # driver_locations table
    if not table_exists(conn, "driver_locations"):
        print("  ✅ Creating table: driver_locations")
        conn.execute("""
            CREATE TABLE driver_locations (
              id            INTEGER PRIMARY KEY AUTOINCREMENT,
              driver_id     TEXT NOT NULL UNIQUE,
              trip_id       INTEGER,
              route_no      TEXT,
              
              latitude      REAL NOT NULL,
              longitude     REAL NOT NULL,
              accuracy      REAL,
              speed         REAL,
              
              updated_at    TEXT NOT NULL,
              
              FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE,
              FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE SET NULL
            )
        """)
        conn.execute("CREATE INDEX idx_driver_locations_route ON driver_locations(route_no)")
        conn.execute("CREATE INDEX idx_driver_locations_trip ON driver_locations(trip_id)")
    else:
        print(f"  ⏭️  Table already exists: driver_locations")
    
    # cab_rotation_state table
    if not table_exists(conn, "cab_rotation_state"):
        print("  ✅ Creating table: cab_rotation_state")
        conn.execute("""
            CREATE TABLE cab_rotation_state (
              cab_no          TEXT PRIMARY KEY,
              last_bucket     TEXT,
              last_trip_day   TEXT,
              trip_count      INTEGER DEFAULT 0,
              total_km        REAL DEFAULT 0,
              updated_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_cab_rotation_day ON cab_rotation_state(last_trip_day)")
        conn.execute("CREATE INDEX idx_cab_rotation_bucket ON cab_rotation_state(last_bucket)")
    else:
        print(f"  ⏭️  Table already exists: cab_rotation_state")
    
    # trip_cab_history table
    if not table_exists(conn, "trip_cab_history"):
        print("  ✅ Creating table: trip_cab_history")
        conn.execute("""
            CREATE TABLE trip_cab_history (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              trip_id         INTEGER NOT NULL,
              cab_no          TEXT NOT NULL,
              driver_id       TEXT,
              trip_day        TEXT NOT NULL,
              total_km        REAL DEFAULT 0,
              bucket          TEXT,
              operation       TEXT,
              created_at      TEXT NOT NULL,
              
              FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE,
              FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE SET NULL
            )
        """)
        conn.execute("CREATE INDEX idx_cab_history_cab ON trip_cab_history(cab_no, trip_day)")
        conn.execute("CREATE INDEX idx_cab_history_day ON trip_cab_history(trip_day)")
        conn.execute("CREATE INDEX idx_cab_history_bucket ON trip_cab_history(bucket)")
    else:
        print(f"  ⏭️  Table already exists: trip_cab_history")

    # groups table to persist admin-created groups prior to trip assignment
    if not table_exists(conn, "groups"):
        print("  ✅ Creating table: groups")
        conn.execute("""
            CREATE TABLE groups (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              admin_id        TEXT NOT NULL,
              trip_day        TEXT NOT NULL,
              trip_type       TEXT NOT NULL CHECK(trip_type IN ('pickup','drop')),
              schedule_time   TEXT NOT NULL,
              vehicle_type    INTEGER NOT NULL,
              assigned_driver_id TEXT,
              assigned_cab_no TEXT,
              members_json    TEXT NOT NULL, -- JSON array of employee ids and metadata
              status          TEXT NOT NULL DEFAULT 'pending', -- pending, assigned, cancelled
              created_at      TEXT NOT NULL,
              updated_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_trip_day ON groups(trip_day, schedule_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_admin ON groups(admin_id)")
    else:
        print(f"  ⏭️  Table already exists: groups")

    # normalized group_members table for quick joins
    if not table_exists(conn, "group_members"):
        print("  ✅ Creating table: group_members")
        conn.execute("""
            CREATE TABLE group_members (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              group_id        INTEGER NOT NULL,
              employee_id     INTEGER NOT NULL,
              sequence_no     INTEGER DEFAULT 0,
              created_at      TEXT NOT NULL,
              FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
              FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_group_members_employee ON group_members(employee_id)")
    else:
        print(f"  ⏭️  Table already exists: group_members")


def ensure_groups_delete_support(conn):
    """Add optional columns/indexes for preview-group delete flow."""
    print("🧹 Ensuring groups delete support...")

    if not table_exists(conn, "groups"):
        print("  ⏭️  Skipping (groups table does not exist)")
        return

    if not column_exists(conn, "groups", "deleted_at"):
        print("  ✅ Adding column: groups.deleted_at")
        conn.execute("ALTER TABLE groups ADD COLUMN deleted_at TEXT")
    else:
        print("  ⏭️  Column already exists: groups.deleted_at")

    if not index_exists(conn, "idx_groups_status"):
        print("  ✅ Creating index: idx_groups_status")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_status ON groups(status)")
    else:
        print("  ⏭️  Index already exists: idx_groups_status")

    if not index_exists(conn, "idx_groups_deleted_at"):
        print("  ✅ Creating index: idx_groups_deleted_at")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_deleted_at ON groups(deleted_at)")
    else:
        print("  ⏭️  Index already exists: idx_groups_deleted_at")


def run_migration():
    """Run all migrations."""
    print("=" * 60)
    print("🚀 RG Travel Solution - Database Migration (STEP 2)")
    print("=" * 60)
    print(f"📅 Date: {_now_iso()}")
    print(f"📂 Database: {get_db_path()}")
    print("")
    
    conn = get_db()
    
    try:
        # Migrate existing tables
        migrate_employees_table(conn)
        migrate_drivers_table(conn)
        migrate_trips_table(conn)
        migrate_route_numbers_table(conn)
        migrate_swap_requests_table(conn)
        migrate_driver_location_history_table(conn)
        migrate_trip_otps_table(conn)
        migrate_otp_audit_log_table(conn)
        
        # Create new tables
        create_new_tables(conn)
        ensure_groups_delete_support(conn)
        ensure_group_flow_schema(conn)
        
        # Commit all changes
        conn.commit()
        
        print("")
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("")
        print("Summary:")
        print("  - All table schema updates applied")
        print("  - All indexes created")
        print("  - Foreign key constraints enabled")
        print("  - Database ready for STEP 2 backend")
        print("")
        
    except Exception as e:
        conn.rollback()
        print("")
        print("=" * 60)
        print(f"❌ Migration failed: {str(e)}")
        print("=" * 60)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
