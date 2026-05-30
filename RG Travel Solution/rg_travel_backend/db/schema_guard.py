from __future__ import annotations

from typing import Any, Iterable


def _table_exists(cur: Any, table_name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _column_names(cur: Any, table_name: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table_name})")
    return {str(r[1]) for r in cur.fetchall()}


def _add_missing_columns(cur: Any, table_name: str, columns: Iterable[tuple[str, str]]) -> None:
    existing = _column_names(cur, table_name)
    for col_name, col_type in columns:
        if col_name in existing:
            continue
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")


def _ensure_groups_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_index INTEGER,
            assigned_driver_id TEXT,
            assigned_cab_type INTEGER,
            members TEXT,
            members_json TEXT,
            distance_km_estimate REAL,
            eta_min_estimate INTEGER,
            admin_id TEXT NOT NULL,
            trip_day TEXT NOT NULL,
            trip_type TEXT NOT NULL,
            schedule_time TEXT NOT NULL,
            vehicle_type INTEGER,
            assigned_cab_no TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        )
        """
    )
    _add_missing_columns(
        cur,
        "groups",
        [
            ("group_index", "INTEGER"),
            ("assigned_driver_id", "TEXT"),
            ("assigned_cab_type", "INTEGER"),
            ("members", "TEXT"),
            ("members_json", "TEXT"),
            ("distance_km_estimate", "REAL"),
            ("eta_min_estimate", "INTEGER"),
            ("admin_id", "TEXT"),
            ("trip_day", "TEXT"),
            ("trip_type", "TEXT"),
            ("schedule_time", "TEXT"),
            ("vehicle_type", "INTEGER"),
            ("assigned_cab_no", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'pending'"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
            ("deleted_at", "TEXT"),
        ],
    )

    cur.execute(
        """
        UPDATE groups
        SET members_json = members
        WHERE (members_json IS NULL OR members_json = '')
          AND members IS NOT NULL
          AND members != ''
        """
    )
    cur.execute(
        """
        UPDATE groups
        SET members = members_json
        WHERE (members IS NULL OR members = '')
          AND members_json IS NOT NULL
          AND members_json != ''
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_groups_trip_day ON groups(trip_day, schedule_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_groups_admin ON groups(admin_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_groups_status ON groups(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_groups_deleted_at ON groups(deleted_at)")


def _ensure_trip_columns(cur: Any) -> None:
    if not _table_exists(cur, "trips"):
        return
    _add_missing_columns(
        cur,
        "trips",
        [
            ("time_slot", "TEXT"),
            ("vehicle_id", "INTEGER"),
            ("route_polyline", "TEXT"),
        ],
    )

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_trips_day_slot_status ON trips(trip_day, schedule_time, status)"
    )
    # Optional index used when routes/services prefer time_slot over schedule_time.
    cols = _column_names(cur, "trips")
    if "time_slot" in cols:
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_trips_day_time_slot_status ON trips(trip_day, time_slot, status)"
        )


def _ensure_driver_hometown_requests(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS driver_hometown_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id TEXT NOT NULL,
            requested_home_town TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _add_missing_columns(
        cur,
        "driver_hometown_requests",
        [
            ("requested_home_town", "TEXT"),
            ("home_town", "TEXT"),
            ("travel_date", "TEXT"),
            ("admin_reason", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    )

    # Keep both column variants in sync for old/new route compatibility.
    cur.execute(
        """
        UPDATE driver_hometown_requests
        SET requested_home_town = home_town
        WHERE (requested_home_town IS NULL OR requested_home_town = '')
          AND home_town IS NOT NULL
          AND home_town != ''
        """
    )
    cur.execute(
        """
        UPDATE driver_hometown_requests
        SET home_town = requested_home_town
        WHERE (home_town IS NULL OR home_town = '')
          AND requested_home_town IS NOT NULL
          AND requested_home_town != ''
        """
    )
    cur.execute(
        """
        UPDATE driver_hometown_requests
        SET travel_date = date('now')
        WHERE travel_date IS NULL OR travel_date = ''
        """
    )

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_dhr_driver_status_date ON driver_hometown_requests(driver_id, status, travel_date)"
    )


def _ensure_employee_trip_requests(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_trip_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            request_type TEXT NOT NULL,
            request_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_trip_req
        ON employee_trip_requests(employee_id, request_type, request_date)
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_employee_trip_req_status_date ON employee_trip_requests(status, request_date)"
    )

    # Backfill from legacy table names if they exist.
    if _table_exists(cur, "employee_no_trip_requests"):
        cur.execute(
            """
            INSERT OR IGNORE INTO employee_trip_requests
                (employee_id, request_type, request_date, status, reason, created_at, updated_at)
            SELECT
                employee_id,
                'no_trip',
                COALESCE(request_date, date('now')),
                COALESCE(status, 'approved'),
                reason,
                COALESCE(created_at, CURRENT_TIMESTAMP),
                COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM employee_no_trip_requests
            """
        )

    if _table_exists(cur, "emp_no_trip_requests"):
        cur.execute(
            """
            INSERT OR IGNORE INTO employee_trip_requests
                (employee_id, request_type, request_date, status, reason, created_at, updated_at)
            SELECT
                employee_id,
                'no_trip',
                COALESCE(request_date, date('now')),
                COALESCE(status, 'approved'),
                reason,
                COALESCE(created_at, CURRENT_TIMESTAMP),
                COALESCE(updated_at, CURRENT_TIMESTAMP)
            FROM emp_no_trip_requests
            """
        )


def _table_row_count(cur: Any, table_name: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    row = cur.fetchone()
    if not row:
        return 0
    try:
        return int(row[0])
    except Exception:
        return 0


def _ensure_multi_admin_transport_schema(cur: Any) -> None:
    if _table_exists(cur, "employees"):
        _add_missing_columns(
            cur,
            "employees",
            [
                ("admin_id", "TEXT"),
            ],
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_admin_id ON employees(admin_id)"
        )

    if _table_exists(cur, "drivers"):
        _add_missing_columns(
            cur,
            "drivers",
            [
                ("primary_admin_id", "TEXT"),
                ("current_admin_id", "TEXT"),
            ],
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_drivers_primary_admin_id ON drivers(primary_admin_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_drivers_current_admin_id ON drivers(current_admin_id)"
        )

    if _table_exists(cur, "driver_requests"):
        _add_missing_columns(
            cur,
            "driver_requests",
            [
                ("admin_id", "TEXT"),
            ],
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_driver_requests_admin_id ON driver_requests(admin_id, status)"
        )

    if _table_exists(cur, "employee_requests"):
        _add_missing_columns(
            cur,
            "employee_requests",
            [
                ("admin_id", "TEXT"),
            ],
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_employee_requests_admin_id ON employee_requests(admin_id, status)"
        )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS driver_admin_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id TEXT NOT NULL,
            admin_id TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(driver_id, admin_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_driver_admin_assignments_driver ON driver_admin_assignments(driver_id, is_active)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_driver_admin_assignments_admin ON driver_admin_assignments(admin_id, is_active)"
    )

    if _table_exists(cur, "trips") and _table_exists(cur, "driver_admin_assignments"):
        cur.execute(
            """
            INSERT OR IGNORE INTO driver_admin_assignments (driver_id, admin_id, is_active)
            SELECT DISTINCT CAST(driver_id AS TEXT), CAST(admin_id AS TEXT), 1
            FROM trips
            WHERE driver_id IS NOT NULL
              AND CAST(driver_id AS TEXT) != ''
              AND admin_id IS NOT NULL
              AND CAST(admin_id AS TEXT) != ''
            """
        )

    if _table_exists(cur, "drivers") and _table_exists(cur, "driver_admin_assignments"):
        cur.execute(
            """
            UPDATE drivers
            SET primary_admin_id = (
                SELECT daa.admin_id
                FROM driver_admin_assignments daa
                WHERE daa.driver_id = drivers.id
                  AND daa.is_active = 1
                ORDER BY daa.id ASC
                LIMIT 1
            )
            WHERE (primary_admin_id IS NULL OR primary_admin_id = '')
            """
        )

    if _table_exists(cur, "employees") and _table_exists(cur, "trip_employees") and _table_exists(cur, "trips"):
        cur.execute(
            """
            WITH employee_admin_source AS (
                SELECT
                    te.employee_id AS employee_id,
                    t.admin_id AS admin_id,
                    COUNT(*) AS use_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY te.employee_id
                        ORDER BY COUNT(*) DESC, t.admin_id ASC
                    ) AS rn
                FROM trip_employees te
                JOIN trips t ON t.id = te.trip_id
                WHERE t.admin_id IS NOT NULL
                  AND CAST(t.admin_id AS TEXT) != ''
                GROUP BY te.employee_id, t.admin_id
            )
            UPDATE employees
            SET admin_id = (
                SELECT admin_id
                FROM employee_admin_source eas
                WHERE eas.employee_id = employees.id
                  AND eas.rn = 1
            )
            WHERE (admin_id IS NULL OR admin_id = '')
              AND EXISTS (
                SELECT 1
                FROM employee_admin_source eas
                WHERE eas.employee_id = employees.id
                  AND eas.rn = 1
              )
            """
        )

    if _table_exists(cur, "admins"):
        cur.execute("SELECT id FROM admins ORDER BY created_at ASC, id ASC")
        admin_rows = cur.fetchall() or []
        if len(admin_rows) == 1:
            default_admin_id = str(admin_rows[0][0])
            if _table_exists(cur, "employees"):
                cur.execute(
                    """
                    UPDATE employees
                    SET admin_id = ?
                    WHERE admin_id IS NULL OR admin_id = ''
                    """,
                    (default_admin_id,),
                )
            if _table_exists(cur, "drivers"):
                cur.execute(
                    """
                    UPDATE drivers
                    SET primary_admin_id = ?
                    WHERE primary_admin_id IS NULL OR primary_admin_id = ''
                    """,
                    (default_admin_id,),
                )
                cur.execute(
                    """
                    UPDATE drivers
                    SET current_admin_id = COALESCE(NULLIF(current_admin_id, ''), ?)
                    WHERE current_admin_id IS NULL OR current_admin_id = ''
                    """,
                    (default_admin_id,),
                )
                cur.execute(
                    """
                    INSERT OR IGNORE INTO driver_admin_assignments (driver_id, admin_id, is_active)
                    SELECT id, ?, 1
                    FROM drivers
                    """,
                    (default_admin_id,),
                )
            if _table_exists(cur, "driver_requests"):
                cur.execute(
                    """
                    UPDATE driver_requests
                    SET admin_id = ?
                    WHERE admin_id IS NULL OR admin_id = ''
                    """,
                    (default_admin_id,),
                )
            if _table_exists(cur, "employee_requests"):
                cur.execute(
                    """
                    UPDATE employee_requests
                    SET admin_id = ?
                    WHERE admin_id IS NULL OR admin_id = ''
                    """,
                    (default_admin_id,),
                )

    if _table_exists(cur, "drivers"):
        cur.execute(
            """
            UPDATE drivers
            SET current_admin_id = COALESCE(NULLIF(current_admin_id, ''), primary_admin_id)
            WHERE current_admin_id IS NULL OR current_admin_id = ''
            """
        )


def _ensure_billing_records_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS billing_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id TEXT NOT NULL,
            driver_id TEXT NOT NULL,
            driver_name TEXT,
            vehicle_no TEXT NOT NULL,
            vehicle_type TEXT,
            billing_mode TEXT NOT NULL,
            from_date TEXT,
            to_date TEXT,
            selected_trip_id INTEGER,
            trip_ids_json TEXT NOT NULL DEFAULT '[]',
            total_trips INTEGER NOT NULL DEFAULT 0,
            excluded_cancelled_trips INTEGER NOT NULL DEFAULT 0,
            total_km REAL NOT NULL DEFAULT 0,
            per_km_amount REAL NOT NULL DEFAULT 0,
            advance_paid REAL NOT NULL DEFAULT 0,
            gst_percent REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            gst_amount REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            payable_amount REAL NOT NULL DEFAULT 0,
            pdf_file_name TEXT,
            pdf_saved_path TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("PRAGMA table_info(billing_records)")
    existing_cols = {str(row[1]) for row in (cur.fetchall() or [])}
    if 'invoice_meta_json' not in existing_cols:
        cur.execute(
            "ALTER TABLE billing_records ADD COLUMN invoice_meta_json TEXT NOT NULL DEFAULT '{}'"
        )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_billing_records_admin_created ON billing_records(admin_id, created_at DESC)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_billing_records_driver_vehicle ON billing_records(driver_id, vehicle_no, created_at DESC)"
    )


def _ensure_billing_settings_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS billing_settings (
            admin_id TEXT PRIMARY KEY,
            service_type TEXT,
            rg_gst_no TEXT,
            bank_name TEXT,
            account_number TEXT,
            ifsc_code TEXT,
            upi_id TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def ensure_group_flow_schema(conn: Any) -> None:
    """
    Step 2 canonical schema guard for group creation flow.
    Safe and idempotent: can run on every startup.
    """
    cur = conn.cursor()
    _ensure_groups_schema(cur)
    _ensure_trip_columns(cur)
    _ensure_driver_hometown_requests(cur)
    _ensure_employee_trip_requests(cur)
    _ensure_multi_admin_transport_schema(cur)
    _ensure_billing_records_schema(cur)
    _ensure_billing_settings_schema(cur)
    conn.commit()
