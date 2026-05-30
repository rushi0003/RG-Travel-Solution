# backend/repositories/employee_repo.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import RepoError, RowDict


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row(row: Any) -> Dict[str, Any]:
    return dict(row) if row else {}


@dataclass
class EmployeeRepo:
    """
    Employee Repository (DB Access Layer)

    Requires:
      - sqlite connection from get_db()
      - connection.row_factory = sqlite3.Row

    Core tables expected (minimum):
      - employees
      - trips
      - trip_employees

    Optional (recommended for your workflow):
      - employee_change_requests
      - employee_absence_requests
    """
    conn: Any

    # =========================================================
    # EMPLOYEE PROFILE / AUTH HELPERS
    # =========================================================
    def get_employee_by_id(self, employee_id: int) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, employee_code,
                   login_time, logout_time,
                   home_address, home_lat, home_lng,
                   is_approved, is_rejected, rejected_reason,
                   created_at, updated_at
            FROM employees
            WHERE id = ?
            """,
            (employee_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_employee_by_mobile(self, mobile: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, employee_code,
                   login_time, logout_time,
                   home_address, home_lat, home_lng,
                   is_approved
            FROM employees
            WHERE mobile = ?
            LIMIT 1
            """,
            (mobile,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_employee_by_code(self, employee_code: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, employee_code,
                   login_time, logout_time,
                   home_address, home_lat, home_lng,
                   is_approved
            FROM employees
            WHERE employee_code = ?
            LIMIT 1
            """,
            (employee_code,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def create_employee(
        self,
        name: str,
        mobile: str,
        employee_code: str,
        login_time: str,
        logout_time: str,
        home_address: str,
        home_lat: Optional[float] = None,
        home_lng: Optional[float] = None,
        is_approved: int = 0,
    ) -> int:
        """
        Employee signup request (admin approval required by default).
        Ensure uniqueness for mobile & employee_code.
        """
        if self.get_employee_by_mobile(mobile):
            raise RepoError("Employee mobile already exists.")
        if self.get_employee_by_code(employee_code):
            raise RepoError("Employee code already exists.")

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO employees
            (name, mobile, employee_code, login_time, logout_time,
             home_address, home_lat, home_lng,
             is_approved, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name, mobile, employee_code, login_time, logout_time,
                home_address, home_lat, home_lng,
                is_approved, _now(), _now()
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_employee_profile_direct(
        self,
        employee_id: int,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        login_time: Optional[str] = None,
        logout_time: Optional[str] = None,
        home_address: Optional[str] = None,
        home_lat: Optional[float] = None,
        home_lng: Optional[float] = None,
    ) -> None:
        """
        Direct update (admin use). Employee edits should go via change request.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE employees
            SET
                name = COALESCE(?, name),
                mobile = COALESCE(?, mobile),
                login_time = COALESCE(?, login_time),
                logout_time = COALESCE(?, logout_time),
                home_address = COALESCE(?, home_address),
                home_lat = COALESCE(?, home_lat),
                home_lng = COALESCE(?, home_lng),
                updated_at = ?
            WHERE id = ?
            """,
            (name, mobile, login_time, logout_time, home_address, home_lat, home_lng, _now(), employee_id),
        )
        self.conn.commit()

    def delete_employee(self, employee_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self.conn.commit()

    # =========================================================
    # EMPLOYEE CHANGE REQUESTS (employee -> admin approve)
    # =========================================================
    def create_employee_change_request(
        self,
        employee_id: int,
        payload_json: str,
        reason: str = "",
    ) -> int:
        """
        Table expected:
          employee_change_requests(
            id, employee_id, payload_json, status,
            reason, admin_reason, created_at, updated_at
          )
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO employee_change_requests
            (employee_id, payload_json, status, reason, created_at, updated_at)
            VALUES (?, ?, 'pending', ?, ?, ?)
            """,
            (employee_id, payload_json, reason, _now(), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_employee_change_requests(self, status: str = "pending") -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.employee_id, e.name, e.mobile,
                   r.payload_json, r.status, r.reason, r.admin_reason, r.created_at
            FROM employee_change_requests r
            JOIN employees e ON e.id = r.employee_id
            WHERE r.status = ?
            ORDER BY r.id DESC
            """,
            (status,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # ABSENCE REQUESTS (employee -> admin approve/reject)
    # =========================================================
    def create_absence_request(
        self,
        employee_id: int,
        absent_date: str,
        reason: str = "",
    ) -> int:
        """
        absent_date: YYYY-MM-DD (you said: at least one day before)
        Table expected:
          employee_absence_requests(
            id, employee_id, absent_date, reason,
            status, admin_reason, created_at, updated_at
          )
        """
        # prevent duplicates for same employee+date if you want
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id
            FROM employee_absence_requests
            WHERE employee_id = ? AND absent_date = ? AND status IN ('pending','approved')
            LIMIT 1
            """,
            (employee_id, absent_date),
        )
        if cur.fetchone():
            raise RepoError("Absence request already exists for this date.")

        cur.execute(
            """
            INSERT INTO employee_absence_requests
            (employee_id, absent_date, reason, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (employee_id, absent_date, reason, _now(), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_my_absence_requests(self, employee_id: int, limit: int = 50) -> List[RowDict]:
        limit = max(1, min(int(limit), 200))
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, absent_date, reason, status, admin_reason, created_at
            FROM employee_absence_requests
            WHERE employee_id = ?
            ORDER BY absent_date DESC, id DESC
            LIMIT ?
            """,
            (employee_id, limit),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # EMPLOYEE LISTING (Admin usage)
    # =========================================================
    def list_employees(self, approved_only: bool = True) -> List[RowDict]:
        cur = self.conn.cursor()
        if approved_only:
            cur.execute(
                """
                SELECT id, name, mobile, employee_code, login_time, logout_time,
                       home_address, home_lat, home_lng, is_approved
                FROM employees
                WHERE is_approved = 1
                ORDER BY id DESC
                """
            )
        else:
            cur.execute(
                """
                SELECT id, name, mobile, employee_code, login_time, logout_time,
                       home_address, home_lat, home_lng, is_approved
                FROM employees
                ORDER BY id DESC
                """
            )
        return [dict(x) for x in cur.fetchall()]

    def list_pending_employee_requests(self) -> List[RowDict]:
        """
        For admin approvals.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, employee_code, login_time, logout_time, home_address, created_at
            FROM employees
            WHERE is_approved = 0
            ORDER BY id DESC
            """
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # MY CURRENT TRIP (employee dashboard)
    # =========================================================
    def get_active_trip_for_employee(self, employee_id: int) -> Optional[RowDict]:
        """
        Step 9: Employee dashboard visibility.
        Active trip = employee in trip_members and status in created/assigned/started/active/in_progress.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                t.id, t.route_no, t.trip_type, t.trip_date, t.trip_time,
                t.status, t.driver_id, t.vehicle_no, t.vehicle_type,
                t.total_km, t.route_polyline,
                d.name AS driver_name, d.mobile AS driver_mobile
            FROM trip_employees tm
            JOIN trips t ON t.id = tm.trip_id
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE tm.employee_id = ?
              AND t.status IN ('created','assigned','started','active','in_progress')
            ORDER BY t.id DESC
            LIMIT 1
            """,
            (employee_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_trip_members(self, trip_id: int) -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT tm.employee_id, e.name, e.mobile, e.home_address,
                   tm.sequence_no AS pickup_order, 
                   CASE WHEN tm.is_no_show = 1 THEN 'no_show' ELSE 'assigned' END AS member_status
            FROM trip_employees tm
            JOIN employees e ON e.id = tm.employee_id
            WHERE tm.trip_id = ?
            ORDER BY tm.sequence_no ASC, e.name ASC
            """,
            (trip_id,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # EMPLOYEE TRIP HISTORY
    # =========================================================
    def list_trip_history_for_employee(
        self,
        employee_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RowDict]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                t.id, t.route_no, t.trip_type, t.trip_date, t.trip_time,
                t.status, t.vehicle_no, t.vehicle_type, t.total_km,
                d.name AS driver_name, d.mobile AS driver_mobile
            FROM trip_employees tm
            JOIN trips t ON t.id = tm.trip_id
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE tm.employee_id = ?
            ORDER BY t.trip_date DESC, t.trip_time DESC, t.id DESC
            LIMIT ? OFFSET ?
            """,
            (employee_id, limit, offset),
        )
        return [dict(x) for x in cur.fetchall()]
