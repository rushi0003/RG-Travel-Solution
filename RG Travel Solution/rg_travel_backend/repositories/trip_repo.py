# backend/repositories/trip_repo.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import RepoError, RowDict


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row(row: Any) -> Dict[str, Any]:
    return dict(row) if row else {}


@dataclass
class TripRepo:
    """
    Trip Repository (DB Access Layer)

    Requires:
      - sqlite connection from get_db()
      - connection.row_factory = sqlite3.Row

    Core tables expected (minimum):
      - trips
      - trip_members

    Recommended tables (optional but aligns with your features):
      - otp_logs (audit)
      - trip_events (audit)
      - vehicle_swap_requests (or handled in driver_repo)

    Assumed columns (recommended in trips):
      trips(
        id INTEGER PK,
        route_no TEXT UNIQUE,
        trip_type TEXT,                  -- 'pickup' | 'drop'
        trip_date TEXT,                  -- YYYY-MM-DD
        trip_time TEXT,                  -- HH:MM (selected time)
        status TEXT,                     -- 'draft'|'assigned'|'in_progress'|'completed'|'cancelled'
        driver_id INTEGER,
        vehicle_no TEXT,
        vehicle_type TEXT,               -- '4'|'6' or '4_seater'|'6_seater'
        route_polyline TEXT,             -- encoded polyline
        stops_json TEXT,                 -- JSON stops list (office + employee stops + return to office)
        total_km REAL,
        km_detail_json TEXT,             -- JSON legs detail (optional)
        cancel_reason TEXT,
        created_at TEXT,
        updated_at TEXT
      )

    trip_members(
      trip_id INTEGER,
      employee_id INTEGER,
      pickup_order INTEGER,
      status TEXT               -- 'active'|'no_show'|'absent' etc.
    )
    """
    conn: Any

    # =========================================================
    # CREATE TRIP (admin assigns)
    # =========================================================
    def create_trip(
        self,
        route_no: str,
        trip_type: str,
        trip_date: str,
        trip_time: str,
        driver_id: Optional[int],
        vehicle_no: str,
        vehicle_type: str,
        status: str = "assigned",
        route_polyline: str = "",
        stops_json: str = "",
        total_km: Optional[float] = None,
        km_detail_json: str = "",
        office_lat: Optional[float] = None,
        office_lng: Optional[float] = None,
    ) -> int:
        """
        Create a trip for a generated route_no.
        """
        cur = self.conn.cursor()

        # Check uniqueness of route_no
        cur.execute("SELECT id FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
        if cur.fetchone():
            raise RepoError("route_no already exists.")

        cur.execute(
            """
            INSERT INTO trips
            (route_no, operation, trip_type, trip_day, schedule_time, status, 
             driver_id, vehicle_type,
             polyline, route_json, total_km,
             office_lat, office_lng,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                route_no, trip_type, trip_type, trip_date, trip_time, status,
                driver_id, vehicle_type,
                route_polyline, stops_json, total_km or 0,
                office_lat, office_lng,
                _now(), _now()
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_trip_members(self, trip_id: int, employee_ids_in_order: List[int]) -> None:
        """
        Adds employees in pickup_order.
        Default member status = 'active'
        """
        if not employee_ids_in_order:
            raise RepoError("No employees to add.")

        cur = self.conn.cursor()

        # remove existing (if admin overrides)
        cur.execute("DELETE FROM trip_employees WHERE trip_id = ?", (trip_id,))

        for idx, emp_id in enumerate(employee_ids_in_order, start=1):
            cur.execute(
                """
                INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (trip_id, emp_id, idx, _now()),
            )

        self.conn.commit()

    # =========================================================
    # FETCH TRIP
    # =========================================================
    def get_trip_by_id(self, trip_id: int) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.id, t.route_no, t.operation as trip_type, t.trip_day as trip_date, t.schedule_time as trip_time, t.status,
                   t.driver_id, d.vehicle_no, t.vehicle_type,
                   t.polyline as route_polyline, t.route_json as stops_json, t.total_km,
                   t.office_lat, t.office_lng, t.route_revision,
                   t.created_at, t.updated_at
            FROM trips t
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE t.id = ?
            """,
            (trip_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_trip_by_route_no(self, route_no: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.id, t.route_no, t.operation as trip_type, t.trip_day as trip_date, t.schedule_time as trip_time, t.status,
                   t.driver_id, d.vehicle_no, t.vehicle_type,
                   t.polyline as route_polyline, t.route_json as stops_json, t.total_km,
                   t.office_lat, t.office_lng, t.route_revision,
                   t.created_at, t.updated_at
            FROM trips t
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE t.route_no = ?
            LIMIT 1
            """,
            (route_no,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def list_trip_members(self, trip_id: int) -> List[RowDict]:
        """
        Includes employee details.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT tm.employee_id, tm.sequence_no as pickup_order, tm.is_no_show,
                   e.name, e.mobile, e.employee_code,
                   e.login_time, e.logout_time,
                   e.home_address, e.home_lat, e.home_lng
            FROM trip_employees tm
            JOIN employees e ON e.id = tm.employee_id
            WHERE tm.trip_id = ?
            ORDER BY tm.sequence_no ASC, e.name ASC
            """,
            (trip_id,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # LIVE TRIPS / HISTORY
    # =========================================================
    def list_live_trips(self) -> List[RowDict]:
        """
        Live trips = assigned or in_progress
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.id, t.route_no, t.operation as trip_type, t.trip_day as trip_date, t.schedule_time as trip_time,
                   t.status, d.vehicle_no, t.vehicle_type, t.total_km,
                   d.name AS driver_name, d.mobile AS driver_mobile
            FROM trips t
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE t.status IN ('assigned','in_progress')
            ORDER BY t.trip_day DESC, t.schedule_time DESC, t.id DESC
            """
        )
        return [dict(x) for x in cur.fetchall()]

    def list_trip_history(
        self,
        limit: int = 200,
        offset: int = 0,
        driver_id: Optional[int] = None,
        trip_date: Optional[str] = None,
        route_no: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[RowDict]:
        """
        Admin trip history with optional filters.
        """
        limit = max(1, min(int(limit), 1000))
        offset = max(0, int(offset))

        where = ["1=1"]
        params: List[Any] = []

        if driver_id is not None:
            where.append("t.driver_id = ?")
            params.append(driver_id)
        if trip_date:
            where.append("t.trip_date = ?")
            params.append(trip_date)
        if route_no:
            where.append("t.route_no = ?")
            params.append(route_no)
        if status:
            where.append("t.status = ?")
            params.append(status)

        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT t.id, t.route_no, t.operation as trip_type, t.trip_day as trip_date, t.schedule_time as trip_time,
                   t.status, d.vehicle_no, t.vehicle_type, t.total_km,
                   d.name AS driver_name, d.mobile AS driver_mobile
            FROM trips t
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE {' AND '.join(where)}
            ORDER BY t.trip_day DESC, t.schedule_time DESC, t.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # UPDATE / ADMIN OVERRIDE
    # =========================================================
    def update_trip_assignment(
        self,
        trip_id: int,
        driver_id: Optional[int] = None,
        vehicle_no: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        trip_time: Optional[str] = None,
        trip_date: Optional[str] = None,
    ) -> None:
        """
        Admin changes: driver/vehicle/time/date override.
        """
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(trips)")
        cols = {row[1] for row in cur.fetchall()}
        set_clauses = [
            "driver_id = COALESCE(?, driver_id)",
            "vehicle_type = COALESCE(?, vehicle_type)",
            "schedule_time = COALESCE(?, schedule_time)",
            "trip_day = COALESCE(?, trip_day)",
            "updated_at = ?",
        ]
        params: List[Any] = [driver_id, vehicle_type, trip_time, trip_date, _now()]
        if "vehicle_no" in cols:
            set_clauses.insert(1, "vehicle_no = COALESCE(?, vehicle_no)")
            params.insert(1, vehicle_no)

        cur.execute(
            f"""
            UPDATE trips
            SET {', '.join(set_clauses)}
            WHERE id = ?
            """,
            (*params, trip_id),
        )
        self.conn.commit()

    def update_route_data(
        self,
        trip_id: int,
        route_polyline: Optional[str] = None,
        stops_json: Optional[str] = None,
        total_km: Optional[float] = None,
    ) -> None:
        """
        Save Google route response.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trips
            SET
                polyline = COALESCE(?, polyline),
                route_json = COALESCE(?, route_json),
                total_km = COALESCE(?, total_km),
                updated_at = ?
            WHERE id = ?
            """,
            (route_polyline, stops_json, total_km, _now(), trip_id),
        )
        self.conn.commit()

    def set_trip_status(self, trip_id: int, status: str) -> None:
        """
        assigned -> in_progress -> completed
        or cancelled
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trips
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, _now(), trip_id),
        )
        self.conn.commit()

    def cancel_trip(self, trip_id: int, reason: str) -> None:
        """
        Cancel trip with mandatory reason.
        """
        reason = (reason or "").strip()
        if len(reason) < 3:
            raise RepoError("Cancel reason required.")

        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trips
            SET status = 'cancelled',
                cancel_reason = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (reason, _now(), trip_id),
        )
        self.conn.commit()

    # =========================================================
    # MEMBER STATUS (no_show / absent)
    # =========================================================
    def mark_member_status(self, trip_id: int, employee_id: int, status: str) -> None:
        """
        status: 'active' | 'no_show' | 'absent'
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trip_employees
            SET is_no_show = ?
            WHERE trip_id = ? AND employee_id = ?
            """,
            (1 if status == 'no_show' else 0, trip_id, employee_id),
        )
        self.conn.commit()

    def list_no_show_members(self, trip_id: int) -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT tm.employee_id, e.name, e.mobile, tm.is_no_show
            FROM trip_employees tm
            JOIN employees e ON e.id = tm.employee_id
            WHERE tm.trip_id = ? AND tm.is_no_show = 1
            ORDER BY tm.sequence_no ASC
            """,
            (trip_id,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # OPTIONAL: OTP AUDIT LOGS (recommended)
    # =========================================================
    def log_otp_event(
        self,
        trip_id: int,
        route_no: str,
        otp_type: str,      # 'start'|'end'
        actor_role: str,    # 'driver'|'employee'|'admin'
        actor_id: int,
        ok: int,
        message: str = "",
    ) -> None:
        """
        If you create otp_logs table, you can store audit logs.
        otp_logs(
          id, trip_id, route_no, otp_type,
          actor_role, actor_id,
          ok, message, created_at
        )
        """
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO otp_logs
                (trip_id, route_no, otp_type, actor_role, actor_id, ok, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trip_id, route_no, otp_type, actor_role, actor_id, int(ok), message, _now()),
            )
            self.conn.commit()
        except Exception:
            # If table not present, ignore safely
            self.conn.rollback()

    # =========================================================
    # OPTIONAL: TRIP EVENTS (recommended)
    # =========================================================
    def log_trip_event(
        self,
        trip_id: int,
        route_no: str,
        event_type: str,  # 'created'|'assigned'|'started'|'completed'|'cancelled'|'override' etc.
        actor_role: str,
        actor_id: int,
        payload_json: str = "",
    ) -> None:
        """
        trip_events(
          id, trip_id, route_no, event_type, actor_role, actor_id, payload_json, created_at
        )
        """
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO trip_events
                (trip_id, route_no, event_type, actor_role, actor_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trip_id, route_no, event_type, actor_role, actor_id, payload_json, _now()),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()

    # =========================================================
    # STEP 10: ADMIN OVERRIDE HELPERS
    # =========================================================
    def increment_route_revision(self, trip_id: int) -> int:
        """
        Increments route_revision counter for a trip.
        Returns the new revision number.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trips
            SET route_revision = COALESCE(route_revision, 1) + 1,
                updated_at = ?
            WHERE id = ?
            RETURNING route_revision
            """,
            (_now(), trip_id),
        )
        row = cur.fetchone()
        self.conn.commit()
        if row:
            return int(row[0])
        return 0

    def get_trip_capacity_info(self, trip_id: int) -> Optional[Dict[str, Any]]:
        """
        Returns {
            'trip_id': ...,
            'vehicle_type': '4'|'6',
            'member_count': 3,
            'status': ...,
            'trip_type': ...,
            'trip_date': ...,
            'trip_time': ...,
            'route_revision': ...
        }
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT t.id, t.vehicle_type, t.status, t.operation as trip_type, t.trip_day AS trip_date, t.schedule_time AS trip_time,
                   t.route_revision,
                   COUNT(tm.id) as member_count
            FROM trips t
            LEFT JOIN trip_employees tm ON tm.trip_id = t.id
            WHERE t.id = ?
            GROUP BY t.id
            """,
            (trip_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None
