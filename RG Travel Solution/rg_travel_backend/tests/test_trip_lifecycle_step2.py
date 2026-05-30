import os
import sqlite3
import tempfile
import unittest

try:
    from rg_travel_backend.services.trip_lifecycle_service import (
        apply_swap_approval,
        mark_member_no_show,
        mark_trip_cancelled,
        mark_trip_completed,
    )
except ModuleNotFoundError:
    from services.trip_lifecycle_service import (
        apply_swap_approval,
        mark_member_no_show,
        mark_trip_cancelled,
        mark_trip_completed,
    )


class TestTripLifecycleStep2(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="trip_lifecycle_step2_", suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._prepare_db()
        self._seed_data()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _prepare_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                route_no TEXT,
                status TEXT,
                driver_id TEXT,
                vehicle_no TEXT,
                trip_day TEXT,
                total_km REAL,
                polyline TEXT,
                route_json TEXT,
                end_time TEXT,
                cancel_reason TEXT,
                cancelled_at TEXT,
                cancelled_by TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_employees (
                trip_id INTEGER,
                employee_id TEXT,
                is_no_show INTEGER DEFAULT 0,
                no_show_marked_at TEXT,
                no_show_marked_by TEXT,
                no_show_reason TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE drivers (
                id TEXT PRIMARY KEY,
                name TEXT,
                mobile TEXT,
                vehicle_no TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE swap_requests (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER,
                old_driver_id TEXT,
                new_driver_id TEXT,
                status TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_cab_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                cab_no TEXT,
                driver_id TEXT,
                trip_day TEXT,
                total_km REAL,
                operation TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                route_no TEXT,
                event_type TEXT,
                actor_role TEXT,
                actor_id TEXT,
                payload_json TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    def _seed_data(self):
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO drivers (id, name, mobile, vehicle_no) VALUES (?, ?, ?, ?)",
            [
                ("1", "Driver One", "9000000001", "MH12AA1111"),
                ("2", "Driver Two", "9000000002", "MH12BB2222"),
            ],
        )
        cur.executemany(
            """
            INSERT INTO trips (
                id, route_no, status, driver_id, vehicle_no, trip_day, total_km,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (201, "R201", "started", "1", "MH12AA1111", "20260307", 12.0, "2026-03-07T08:00:00", "2026-03-07T08:00:00"),
                (202, "R202", "assigned", "1", "MH12AA1111", "20260307", 18.0, "2026-03-07T08:00:00", "2026-03-07T08:00:00"),
                (203, "R203", "started", "1", "MH12AA1111", "20260307", 9.0, "2026-03-07T08:00:00", "2026-03-07T08:00:00"),
            ],
        )
        cur.execute(
            "INSERT INTO trip_employees (trip_id, employee_id, is_no_show) VALUES (203, '11', 0)"
        )
        cur.execute(
            "INSERT INTO swap_requests (id, trip_id, old_driver_id, status) VALUES (301, 202, '1', 'pending')"
        )
        self.conn.commit()

    def test_mark_trip_completed_persists_history_fields(self):
        result = mark_trip_completed(
            self.conn,
            201,
            actor_role="driver",
            actor_id="1",
            total_km=25.75,
            polyline="encoded",
            route_json='{"stops":2}',
        )
        self.conn.commit()

        cur = self.conn.cursor()
        cur.execute("SELECT status, total_km, polyline, route_json, end_time FROM trips WHERE id = 201")
        row = cur.fetchone()
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["total_km"], 25.75)
        self.assertEqual(row["polyline"], "encoded")
        self.assertEqual(row["route_json"], '{"stops":2}')
        self.assertTrue(row["end_time"])
        self.assertEqual(result["trip_id"], 201)

        cur.execute("SELECT event_type FROM trip_events WHERE trip_id = 201 ORDER BY id DESC LIMIT 1")
        self.assertEqual(cur.fetchone()["event_type"], "trip_completed")

        cur.execute("SELECT cab_no, total_km, operation FROM trip_cab_history WHERE trip_id = 201 ORDER BY id DESC LIMIT 1")
        hist = cur.fetchone()
        self.assertEqual(hist["cab_no"], "MH12AA1111")
        self.assertEqual(hist["total_km"], 25.75)
        self.assertEqual(hist["operation"], "completed")

    def test_mark_trip_cancelled_clears_km_and_sets_cancel_metadata(self):
        result = mark_trip_cancelled(
            self.conn,
            202,
            reason="Driver cancel request approved",
            actor_role="admin",
            actor_id="admin_1",
        )
        self.conn.commit()

        cur = self.conn.cursor()
        cur.execute(
            "SELECT status, total_km, cancel_reason, cancelled_at, cancelled_by, end_time FROM trips WHERE id = 202"
        )
        row = cur.fetchone()
        self.assertEqual(row["status"], "cancelled")
        self.assertIsNone(row["total_km"])
        self.assertEqual(row["cancel_reason"], "Driver cancel request approved")
        self.assertEqual(row["cancelled_by"], "admin_1")
        self.assertTrue(row["cancelled_at"])
        self.assertIsNone(row["end_time"])
        self.assertEqual(result["trip_id"], 202)

    def test_mark_member_no_show_persists_metadata(self):
        result = mark_member_no_show(
            self.conn,
            203,
            11,
            marked_by_driver_id="1",
            reason="Employee not reachable",
        )
        self.conn.commit()

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT is_no_show, no_show_marked_at, no_show_marked_by, no_show_reason
            FROM trip_employees
            WHERE trip_id = 203 AND employee_id = '11'
            """
        )
        row = cur.fetchone()
        self.assertEqual(row["is_no_show"], 1)
        self.assertTrue(row["no_show_marked_at"])
        self.assertEqual(row["no_show_marked_by"], "1")
        self.assertEqual(row["no_show_reason"], "Employee not reachable")
        self.assertEqual(result["employee_id"], 11)

    def test_apply_swap_approval_updates_trip_and_request(self):
        result = apply_swap_approval(
            self.conn,
            202,
            request_id=301,
            old_driver_id="1",
            new_driver_id="2",
            new_cab_no="MH12BB2222",
            reviewed_by="admin_2",
        )
        self.conn.commit()

        cur = self.conn.cursor()
        cur.execute("SELECT driver_id, vehicle_no FROM trips WHERE id = 202")
        trip = cur.fetchone()
        self.assertEqual(trip["driver_id"], "2")
        self.assertEqual(trip["vehicle_no"], "MH12BB2222")

        cur.execute("SELECT status, new_driver_id, reviewed_by, reviewed_at FROM swap_requests WHERE id = 301")
        req = cur.fetchone()
        self.assertEqual(req["status"], "approved")
        self.assertEqual(req["new_driver_id"], "2")
        self.assertEqual(req["reviewed_by"], "admin_2")
        self.assertTrue(req["reviewed_at"])
        self.assertEqual(result["request_id"], 301)


if __name__ == "__main__":
    unittest.main()
