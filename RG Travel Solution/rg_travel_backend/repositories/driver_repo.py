# backend/repositories/driver_repo.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from . import RepoError, RowDict
except (ImportError, ValueError):
    try:
        from repositories import RepoError, RowDict # type: ignore
    except ImportError:
        RepoError = Exception
        RowDict = Dict[str, Any]


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row(row: Any) -> Dict[str, Any]:
    return dict(row) if row else {}


def _parse_iso(dt_str: str) -> Optional[datetime]:
    """
    Best-effort ISO parser for UTC isoformat strings.
    """
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", ""))
    except Exception:
        return None


@dataclass
class DriverRepo:
    """
    Driver Repository (DB Access Layer)

    Requires:
      - sqlite connection from get_db()
      - row_factory = sqlite3.Row (recommended)

    Expected core tables (minimum):
      - drivers
      - trips
      - trip_employees
      - driver_locations

    Optional tables (recommended for your workflow):
      - driver_change_requests
      - driver_vehicle_swap_requests
      - driver_hometown_requests
    """
    conn: Any

    # =========================================================
    # DRIVER PROFILE
    # =========================================================
    def get_driver_by_id(self, driver_id: int) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type,
                   home_town, is_approved, is_rejected,
                   rejected_reason, created_at, updated_at
            FROM drivers
            WHERE id = ?
            """,
            (driver_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_driver_by_mobile(self, mobile: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type,
                   home_town, is_approved, is_rejected, rejected_reason
            FROM drivers
            WHERE mobile = ?
            LIMIT 1
            """,
            (mobile,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_driver_by_dl(self, dl_no: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved
            FROM drivers
            WHERE dl_no = ?
            LIMIT 1
            """,
            (dl_no,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_driver_by_vehicle_no(self, vehicle_no: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved
            FROM drivers
            WHERE vehicle_no = ?
            LIMIT 1
            """,
            (vehicle_no,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def create_driver(
        self,
        name: str,
        mobile: str,
        dl_no: str,
        vehicle_no: str,
        vehicle_type: str,
        hometown: str = "",
        is_approved: int = 0,
    ) -> int:
        """
        Driver signup request (admin approval required by default).
        Enforce uniqueness by (mobile, dl_no, vehicle_no) at service/validation level too.
        """
        cur = self.conn.cursor()

        # soft uniqueness checks
        if self.get_driver_by_mobile(mobile):
            raise RepoError("Driver mobile already exists.")
        if self.get_driver_by_dl(dl_no):
            raise RepoError("Driver DL already exists.")
        if self.get_driver_by_vehicle_no(vehicle_no):
            raise RepoError("Vehicle number already exists.")

        cur.execute(
            """
            INSERT INTO drivers
            (name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, mobile, dl_no, vehicle_no, vehicle_type, home_town, is_approved, _now(), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_driver_profile_direct(
        self,
        driver_id: int,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        dl_no: Optional[str] = None,
        vehicle_no: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        hometown: Optional[str] = None,
    ) -> None:
        """
        Direct update (admin use). Driver-side edits should go through change request table.
        """
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
                home_town = COALESCE(?, home_town),
                updated_at = ?
            WHERE id = ?
            """,
            (name, mobile, dl_no, vehicle_no, vehicle_type, home_town, _now(), driver_id),
        )
        self.conn.commit()

    # =========================================================
    # DRIVER CHANGE REQUESTS (driver -> admin approve)
    # =========================================================
    def create_driver_change_request(self, driver_id: int, payload_json: str) -> int:
        """
        payload_json: JSON string of requested fields
        Table expected: driver_change_requests(id, driver_id, payload_json, status, reason, created_at, updated_at)
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO driver_change_requests
            (driver_id, payload_json, status, created_at, updated_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (driver_id, payload_json, _now(), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_driver_change_requests(self, status: str = "pending") -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.driver_id, d.name, d.mobile, r.payload_json, r.status, r.reason, r.created_at
            FROM driver_change_requests r
            JOIN drivers d ON d.id = r.driver_id
            WHERE r.status = ?
            ORDER BY r.id DESC
            """,
            (status,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # HOMETOWN REQUEST (driver -> admin approve)
    # =========================================================
    def create_hometown_request(self, driver_id: int, hometown: str) -> int:
        """
        Table expected: driver_hometown_requests(id, driver_id, hometown, status, admin_reason, created_at, updated_at)
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO driver_hometown_requests
            (driver_id, hometown, status, created_at, updated_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (driver_id, hometown, _now(), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_hometown_requests(self, status: str = "pending") -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.driver_id, d.name, d.mobile, r.home_town, r.status, r.admin_reason, r.created_at
            FROM driver_hometown_requests r
            JOIN drivers d ON d.id = r.driver_id
            WHERE r.status = ?
            ORDER BY r.id DESC
            """,
            (status,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # LIVE TRACKING (driver_locations)
    # =========================================================
    def upsert_driver_location(
        self,
        driver_id: int,
        lat: float,
        lng: float,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
    ) -> None:
        """
        Table expected: driver_locations(
            driver_id INTEGER PRIMARY KEY,
            lat REAL, lng REAL, speed REAL, heading REAL,
            updated_at TEXT
        )
        """
        cur = self.conn.cursor()

        # Upsert via REPLACE (simplest for sqlite)
        cur.execute(
            """
            INSERT INTO driver_locations (driver_id, lat, lng, speed, heading, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(driver_id) DO UPDATE SET
                lat=excluded.lat,
                lng=excluded.lng,
                speed=excluded.speed,
                heading=excluded.heading,
                updated_at=excluded.updated_at
            """,
            (driver_id, lat, lng, speed, heading, _now()),
        )
        self.conn.commit()

    def get_driver_location(self, driver_id: int) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT driver_id, lat, lng, speed, heading, updated_at
            FROM driver_locations
            WHERE driver_id = ?
            """,
            (driver_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def list_online_drivers(self, online_within_seconds: int = 30) -> List[RowDict]:
        """
        Returns drivers whose location ping is within last N seconds.
        Since updated_at is ISO string, we filter in python.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT dl.driver_id, dl.lat, dl.lng, dl.speed, dl.heading, dl.updated_at,
                   d.name, d.mobile, d.vehicle_no, d.vehicle_type
            FROM driver_locations dl
            JOIN drivers d ON d.id = dl.driver_id
            WHERE d.is_approved = 1
            ORDER BY dl.updated_at DESC
            """
        )
        rows = [dict(x) for x in cur.fetchall()]

        now = datetime.utcnow()
        out: List[RowDict] = []
        for r in rows:
            dt = _parse_iso(r.get("updated_at", ""))
            if not dt:
                continue
            if (now - dt) <= timedelta(seconds=int(online_within_seconds)):
                out.append(r)
        return out

    # =========================================================
    # ASSIGNED TRIP (driver dashboard)
    # =========================================================
    def get_active_trip_for_driver(self, driver_id: int) -> Optional[RowDict]:
        """
        Step 9: Driver dashboard visibility.
        Active trip = status in created/assigned/started/active/in_progress.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, route_no, trip_type, trip_date, trip_time,
                   status, driver_id, vehicle_no, vehicle_type,
                   total_km, route_polyline
            FROM trips
            WHERE driver_id = ?
              AND status IN ('created','assigned','started','active','in_progress')
            ORDER BY id DESC
            LIMIT 1
            """,
            (driver_id,),
        )
        r = cur.fetchone()
        return dict(r) if r else None

    def get_trip_by_route_no(self, route_no: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, route_no, trip_type, trip_date, trip_time,
                   status, driver_id, vehicle_no, vehicle_type, total_km, route_polyline
            FROM trips
            WHERE route_no = ?
            LIMIT 1
            """,
            (route_no,),
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

    def mark_member_no_show(self, trip_id: int, employee_id: int) -> None:
        """
        Driver marks employee no-show at pickup/drop.
        """
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

    # =========================================================
    # EMERGENCY VEHICLE / DRIVER SWAP (driver -> admin approve)
    # =========================================================
    def create_vehicle_swap_request(
        self,
        trip_id: int,
        driver_id: int,
        new_driver_name: str,
        new_driver_mobile: str,
        new_vehicle_no: str,
        proof_photo_path: str = "",
        note: str = "",
    ) -> int:
        """
        Table expected: driver_vehicle_swap_requests(
            id, trip_id, driver_id,
            new_driver_name, new_driver_mobile, new_vehicle_no,
            proof_photo_path, note,
            status, admin_reason, created_at, updated_at
        )
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO driver_vehicle_swap_requests
            (trip_id, driver_id, new_driver_name, new_driver_mobile, new_vehicle_no,
             proof_photo_path, note, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (trip_id, driver_id, new_driver_name, new_driver_mobile, new_vehicle_no,
             proof_photo_path, note, _now(), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_vehicle_swap_requests(self, status: str = "pending") -> List[RowDict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT r.id, r.trip_id, r.driver_id,
                   d.name AS current_driver_name, d.mobile AS current_driver_mobile,
                   r.new_driver_name, r.new_driver_mobile, r.new_vehicle_no,
                   r.proof_photo_path, r.note,
                   r.status, r.admin_reason, r.created_at
            FROM driver_vehicle_swap_requests r
            JOIN drivers d ON d.id = r.driver_id
            WHERE r.status = ?
            ORDER BY r.id DESC
            """,
            (status,),
        )
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # DRIVER TRIP HISTORY (for driver profile page)
    # =========================================================
    def list_trip_history_for_driver(
        self,
        driver_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RowDict]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, route_no, trip_type, trip_date, trip_time,
                   status, vehicle_no, vehicle_type, total_km
            FROM trips
            WHERE driver_id = ?
            ORDER BY trip_date DESC, trip_time DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (driver_id, limit, offset),
        )
        return [dict(x) for x in cur.fetchall()]
    def fetch_available_drivers(self, trip_day: str, time_slot: str) -> List[RowDict]:
        """
        Fetch all APPROVED drivers who are NOT assigning to an active/scheduled trip
        at the specific trip_day and time_slot.
        
        Args:
            trip_day: YYYYMMDD
            time_slot: HH:MM
        """
        cur = self.conn.cursor()
        
        # We need to find drivers who are BUSY.
        # A driver is busy if they have a trip on this day at this time 
        # that is NOT cancelled or completed (i.e., created, assigned, started).
        # Note: If trips have duration, we might need more complex overlap logic.
        # For now, assuming distinct time slots or single trip per slot.
        busy_query = """
            SELECT driver_id 
            FROM trips 
            WHERE trip_day = ? 
              AND schedule_time = ? 
              AND status IN ('created', 'assigned', 'started', 'active')
        """
        
        # Main query: Approved drivers NOT IN busy_query
        query = f"""
            SELECT id, name, mobile, vehicle_no, vehicle_type, home_town, is_approved
            FROM drivers
            WHERE is_approved = 1
              AND id NOT IN ({busy_query})
        """
        
        cur.execute(query, (trip_day, time_slot))
        return [dict(x) for x in cur.fetchall()]

    # =========================================================
    # FAIRNESS ROTATION (cab_rotation_state)
    # =========================================================
    def get_cab_rotation_state(self, cab_no: str) -> Optional[RowDict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM cab_rotation_state WHERE cab_no = ?", (cab_no,))
        r = cur.fetchone()
        return dict(r) if r else None

    def update_cab_rotation_state(self, cab_no: str, km: float, bucket: str, trip_day: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO cab_rotation_state (cab_no, last_bucket, last_trip_day, trip_count, total_km, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(cab_no) DO UPDATE SET
                last_bucket = excluded.last_bucket,
                last_trip_day = excluded.last_trip_day,
                trip_count = trip_count + 1,
                total_km = total_km + excluded.total_km,
                updated_at = excluded.updated_at
            """,
            (cab_no, bucket, trip_day, km, _now()),
        )
        self.conn.commit()

    def get_recent_trip_areas(self, driver_id: str, days: int = 3) -> List[str]:
        """
        Returns a list of route_no or area indicators for recent trips.
        Used for Avoid Repeat logic.
        """
        cur = self.conn.cursor()
        # Since we don't have a specific 'area' column, we'll use first few stops as an indicator
        # or simplified route_no if it contains area info. 
        # For now, let's just fetch recent trip polylines or route_no.
        cur.execute(
            """
            SELECT route_no FROM trips
            WHERE driver_id = ? 
              AND created_at >= ?
            """,
            (driver_id, (datetime.utcnow() - timedelta(days=days)).isoformat()),
        )
        return [r[0] for r in cur.fetchall()]
