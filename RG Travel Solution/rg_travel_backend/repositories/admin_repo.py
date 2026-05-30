# backend/repositories/admin_repo.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from . import RepoError, RowDict


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row_to_dict(row: Any) -> Dict[str, Any]:
    # sqlite3.Row is already dict-like, but converting keeps it JSON friendly
    return dict(row) if row is not None else {}


@dataclass
class AdminRepo:
    """
    Admin Repository (DB Access Layer)

    Expectation:
      - self.conn is sqlite connection returned by get_db()
      - connection.row_factory = sqlite3.Row in db/__init__.py
    """
    conn: Any

    def _admin_columns(self) -> set[str]:
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(admins)")
        return {str(row["name"]) for row in cur.fetchall()}

    # =========================================================
    # ADMIN PROFILE
    # =========================================================
    def get_admin_by_id(self, admin_id: int) -> Optional[RowDict]:
        columns = self._admin_columns()
        select_parts = ['id', 'name', 'mobile']
        optional_parts = [
            'email',
            'office_name',
            'office_location',
            'office_address',
            'office_lat',
            'office_lng',
        ]
        select_parts.extend([col for col in optional_parts if col in columns])
        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT {', '.join(select_parts)}
            FROM admins
            WHERE id = ?
            """,
            (admin_id,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None

    def get_admin_by_mobile(self, mobile: str) -> Optional[RowDict]:
        columns = self._admin_columns()
        select_parts = ['id', 'name', 'mobile']
        optional_parts = [
            'email',
            'office_name',
            'office_location',
            'office_address',
            'office_lat',
            'office_lng',
        ]
        select_parts.extend([col for col in optional_parts if col in columns])
        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT {', '.join(select_parts)}
            FROM admins
            WHERE mobile = ?
            """,
            (mobile,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None

    def list_admins(self) -> List[RowDict]:
        columns = self._admin_columns()
        select_parts = ['id', 'name', 'mobile']
        optional_parts = [
            'email',
            'office_name',
            'office_location',
            'office_address',
            'office_lat',
            'office_lng',
            'created_at',
            'updated_at',
        ]
        select_parts.extend([col for col in optional_parts if col in columns])
        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT {', '.join(select_parts)}
            FROM admins
            ORDER BY datetime(created_at) DESC, id DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]

    def create_admin(
        self,
        *,
        admin_id: str,
        name: str,
        mobile: str,
        password_salt: str,
        password_hash: str,
        email: Optional[str] = None,
        office_name: Optional[str] = None,
        office_location: Optional[str] = None,
        office_address: Optional[str] = None,
        office_lat: Optional[float] = None,
        office_lng: Optional[float] = None,
    ) -> RowDict:
        columns = self._admin_columns()
        cur = self.conn.cursor()
        now = _now()
        insert_columns = [
            'id',
            'name',
            'mobile',
            'password_salt',
            'password_hash',
            'created_at',
            'updated_at',
        ]
        values: list[Any] = [
            admin_id,
            name,
            mobile,
            password_salt,
            password_hash,
            now,
            now,
        ]

        optional_values = {
            'email': email,
            'office_name': office_name,
            'office_location': office_location,
            'office_address': office_address,
            'office_lat': office_lat,
            'office_lng': office_lng,
        }
        for column, value in optional_values.items():
            if column in columns:
                insert_columns.append(column)
                values.append(value)

        cur.execute(
            f"""
            INSERT INTO admins (
                {', '.join(insert_columns)}
            )
            VALUES ({', '.join(['?'] * len(insert_columns))})
            """,
            tuple(values),
        )
        self.conn.commit()
        select_parts = ['id', 'name', 'mobile']
        optional_parts = [
            'email',
            'office_name',
            'office_location',
            'office_address',
            'office_lat',
            'office_lng',
            'created_at',
            'updated_at',
        ]
        select_parts.extend([col for col in optional_parts if col in columns])
        cur.execute(
            f"""
            SELECT {', '.join(select_parts)}
            FROM admins
            WHERE id = ?
            """,
            (admin_id,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else {}

    def delete_admin(self, admin_id: str) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
        if cur.rowcount == 0:
            raise RepoError("Admin not found.")
        self.conn.commit()

    def upsert_admin_office_profile(
        self,
        admin_id: int,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        office_name: Optional[str] = None,
        office_address: Optional[str] = None,
        office_lat: Optional[float] = None,
        office_lng: Optional[float] = None,
    ) -> None:
        """
        Update admin basic + office profile.
        Uses COALESCE to update only provided values.
        """
        columns = self._admin_columns()
        updates: list[str] = []
        params: list[Any] = []

        def add_update(column: str, value: Any) -> None:
            if column in columns and value is not None:
                updates.append(f"{column} = ?")
                params.append(value)

        add_update("name", name)
        add_update("mobile", mobile)
        add_update("office_name", office_name)
        add_update("office_address", office_address)
        add_update("office_lat", office_lat)
        add_update("office_lng", office_lng)
        add_update("office_location", office_address)
        if "updated_at" in columns:
            updates.append("updated_at = ?")
            params.append(_now())
        if not updates:
            return

        cur = self.conn.cursor()
        params.append(admin_id)
        cur.execute(
            f"""
            UPDATE admins
            SET {', '.join(updates)}
            WHERE id = ?
            """,
            tuple(params),
        )
        self.conn.commit()

    # =========================================================
    # APPROVAL QUEUES (Drivers/Employees + change requests)
    # =========================================================
    def list_pending_driver_requests(self) -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, hometown, created_at
            FROM drivers
            WHERE is_approved = 0
            ORDER BY id DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]

    def list_pending_employee_requests(self) -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, employee_code, login_time, logout_time, home_address, created_at
            FROM employees
            WHERE is_approved = 0
            ORDER BY id DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]

    def approve_driver(self, driver_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE drivers
            SET is_approved = 1, approved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (_now(), _now(), driver_id),
        )
        self.conn.commit()

    def reject_driver(self, driver_id: int, reason: str = "") -> None:
        """
        For demo: we keep driver row but mark rejected.
        If your schema uses driver_requests table, change logic accordingly.
        """
        cur = self.conn.cursor()
        # optional column rejected_reason / is_rejected
        cur.execute(
            """
            UPDATE drivers
            SET is_approved = 0,
                is_rejected = 1,
                rejected_reason = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (reason, _now(), driver_id),
        )
        self.conn.commit()

    def approve_employee(self, employee_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE employees
            SET is_approved = 1, approved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (_now(), _now(), employee_id),
        )
        self.conn.commit()

    def reject_employee(self, employee_id: int, reason: str = "") -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE employees
            SET is_approved = 0,
                is_rejected = 1,
                rejected_reason = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (reason, _now(), employee_id),
        )
        self.conn.commit()

    # --- Profile change request approvals (optional tables) ---
    def list_employee_change_requests(self, status: str = "pending") -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.employee_id, e.name, e.mobile, r.payload_json, r.status, r.reason, r.created_at
            FROM employee_change_requests r
            JOIN employees e ON e.id = r.employee_id
            WHERE r.status = ?
            ORDER BY r.id DESC
            """,
            (status,),
        )
        return [dict(r) for r in cur.fetchall()]

    def set_employee_change_request_status(
        self,
        request_id: int,
        status: str,
        admin_reason: str = "",
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE employee_change_requests
            SET status = ?, admin_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, admin_reason, _now(), request_id),
        )
        self.conn.commit()

    def apply_employee_change_request(self, request_id: int) -> None:
        """
        Applies request payload to employees table.
        Requires employee_change_requests(payload_json JSON).
        """
        import json

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT employee_id, payload_json
            FROM employee_change_requests
            WHERE id = ? AND status = 'pending'
            """,
            (request_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RepoError("Change request not found or not pending.")

        employee_id = int(row["employee_id"])
        payload = json.loads(row["payload_json"] or "{}")

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
            (
                payload.get("name"),
                payload.get("mobile"),
                payload.get("login_time"),
                payload.get("logout_time"),
                payload.get("home_address"),
                payload.get("home_lat"),
                payload.get("home_lng"),
                _now(),
                employee_id,
            ),
        )

        # mark request approved
        cur.execute(
            """
            UPDATE employee_change_requests
            SET status = 'approved', updated_at = ?
            WHERE id = ?
            """,
            (_now(), request_id),
        )
        self.conn.commit()

    # =========================================================
    # ABSENCE REQUESTS (admin action)
    # =========================================================
    def list_absence_requests(self, status: str = "pending") -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.employee_id, e.name, e.mobile,
                   r.absent_date, r.reason, r.status, r.created_at
            FROM employee_absence_requests r
            JOIN employees e ON e.id = r.employee_id
            WHERE r.status = ?
            ORDER BY r.absent_date DESC, r.id DESC
            """,
            (status,),
        )
        return [dict(r) for r in cur.fetchall()]

    def set_absence_request_status(
        self,
        request_id: int,
        status: str,
        admin_reason: str = "",
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE employee_absence_requests
            SET status = ?, admin_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, admin_reason, _now(), request_id),
        )
        self.conn.commit()

    # =========================================================
    # LIST DRIVERS/EMPLOYEES (approved)
    # =========================================================
    def list_drivers(self, approved_only: bool = True) -> List[RowDict]:
        cur = self.conn.cursor()
        if approved_only:
            cur.execute(
                """
                SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, hometown, is_approved
                FROM drivers
                WHERE is_approved = 1
                ORDER BY id DESC
                """
            )
        else:
            cur.execute(
                """
                SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, hometown, is_approved
                FROM drivers
                ORDER BY id DESC
                """
            )
        return [dict(r) for r in cur.fetchall()]

    def list_employees(self, approved_only: bool = True) -> List[RowDict]:
        cur = self.conn.cursor()
        if approved_only:
            cur.execute(
                """
                SELECT id, name, mobile, employee_code, login_time, logout_time, home_address, is_approved
                FROM employees
                WHERE is_approved = 1
                ORDER BY id DESC
                """
            )
        else:
            cur.execute(
                """
                SELECT id, name, mobile, employee_code, login_time, logout_time, home_address, is_approved
                FROM employees
                ORDER BY id DESC
                """
            )
        return [dict(r) for r in cur.fetchall()]

    def update_driver(
        self,
        driver_id: int,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        dl_no: Optional[str] = None,
        vehicle_no: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        hometown: Optional[str] = None,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE drivers
            SET
                name = COALESCE(?, name),
                mobile = COALESCE(?, mobile),
                dl_no = COALESCE(?, dl_no),
                vehicle_no = COALESCE(?, vehicle_no),
                vehicle_type = COALESCE(?, vehicle_type),
                hometown = COALESCE(?, hometown),
                updated_at = ?
            WHERE id = ?
            """,
            (name, mobile, dl_no, vehicle_no, vehicle_type, hometown, _now(), driver_id),
        )
        self.conn.commit()

    def update_employee(
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

    def delete_driver(self, driver_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))
        self.conn.commit()

    def delete_employee(self, employee_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        self.conn.commit()

    # =========================================================
    # TRIPS (admin views + update)
    # =========================================================
    def list_trips(
        self,
        status: Optional[str] = None,
        trip_date: Optional[str] = None,
        trip_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RowDict]:
        """
        status: created/assigned/in_progress/completed/cancelled
        trip_type: pickup/drop
        trip_date: YYYY-MM-DD
        """
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))

        sql = """
            SELECT
                t.id, t.route_no, t.trip_type, t.trip_date, t.trip_time,
                t.status, t.vehicle_no, t.vehicle_type, t.total_km,
                d.name AS driver_name, d.mobile AS driver_mobile
            FROM trips t
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE 1=1
        """
        params: List[Any] = []

        if status:
            sql += " AND t.status = ?"
            params.append(status)

        if trip_date:
            sql += " AND t.trip_date = ?"
            params.append(trip_date)

        if trip_type:
            sql += " AND t.trip_type = ?"
            params.append(trip_type)

        sql += " ORDER BY t.trip_date DESC, t.trip_time DESC, t.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]

    def get_trip_by_route_no(self, route_no: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, route_no, trip_type, trip_date, trip_time, status,
                   driver_id, vehicle_no, vehicle_type, total_km
            FROM trips
            WHERE route_no = ?
            LIMIT 1
            """,
            (route_no,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_trip_members(self, trip_id: int) -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                tm.employee_id,
                e.name,
                e.mobile,
                e.home_address,
                tm.sequence_no AS pickup_order,
                CASE WHEN tm.is_no_show = 1 THEN 'no_show' ELSE 'assigned' END AS member_status
            FROM trip_employees tm
            JOIN employees e ON e.id = tm.employee_id
            WHERE tm.trip_id = ?
            ORDER BY tm.sequence_no ASC, e.name ASC
            """,
            (trip_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def set_trip_status(self, trip_id: int, status: str) -> None:
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
        Admin cancels trip with reason (required in your logic).
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trips
            SET status = 'cancelled', cancel_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (reason, _now(), trip_id),
        )
        self.conn.commit()

    def complete_trip(self, trip_id: int) -> None:
        """
        Mark completed. Total KM usually computed by routing_service and saved separately.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trips
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (_now(), _now(), trip_id),
        )
        self.conn.commit()

    # =========================================================
    # ASSIGN DRIVER / VEHICLE TO TRIP
    # =========================================================
    def assign_driver_to_trip(
        self,
        trip_id: int,
        driver_id: int,
        vehicle_no: Optional[str] = None,
        vehicle_type: Optional[str] = None,
    ) -> None:
        """
        Assign driver & (optional) vehicle to trip.
        vehicle_no/type normally derived from driver, but admin can override.
        """
        cur = self.conn.cursor()

        # get driver info if needed
        if vehicle_no is None or vehicle_type is None:
            cur.execute(
                """
                SELECT vehicle_no, vehicle_type
                FROM drivers
                WHERE id = ?
                """,
                (driver_id,),
            )
            d = cur.fetchone()
            if not d:
                raise RepoError("Driver not found.")
            if vehicle_no is None:
                vehicle_no = d["vehicle_no"]
            if vehicle_type is None:
                vehicle_type = d["vehicle_type"]

        cur.execute(
            """
            UPDATE trips
            SET driver_id = ?, vehicle_no = ?, vehicle_type = ?, status='assigned', updated_at = ?
            WHERE id = ?
            """,
            (driver_id, vehicle_no, vehicle_type, _now(), trip_id),
        )
        self.conn.commit()

    # =========================================================
    # MEMBERS UPDATE (Admin "any changes" in live trip)
    # =========================================================
    def add_employee_to_trip(self, trip_id: int, employee_id: int, pickup_order: int) -> None:
        cur = self.conn.cursor()
        # prevent duplicates
        cur.execute(
            "SELECT id FROM trip_employees WHERE trip_id = ? AND employee_id = ?",
            (trip_id, employee_id),
        )
        if cur.fetchone():
            raise RepoError("Employee already in this trip.")

        cur.execute(
            """
            INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
            VALUES (?, ?, ?, 0, ?)
            """,
            (trip_id, employee_id, pickup_order, _now()),
        )
        self.conn.commit()

    def remove_employee_from_trip(self, trip_id: int, employee_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM trip_employees WHERE trip_id = ? AND employee_id = ?",
            (trip_id, employee_id),
        )
        self.conn.commit()

    def mark_member_no_show(self, trip_id: int, employee_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE trip_employees
            SET is_no_show = 1
            WHERE trip_id = ? AND employee_id = ?
            """,
            (trip_id, employee_id),
        )
        self.conn.commit()
