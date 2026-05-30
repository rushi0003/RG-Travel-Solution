import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

from rg_travel_backend.routes.trip_creation_v2_routes import trip_v2_bp


class TestTripV2StartAdminOverride(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="trip_v2_start_", suffix=".db")
        os.close(fd)
        self._prepare_db()

        self.app = Flask(__name__)
        self.app.register_blueprint(trip_v2_bp)
        self.client = self.app.test_client()

        self.db_patcher = patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.get_db",
            side_effect=self._new_conn,
        )
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _new_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _prepare_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                status TEXT,
                route_no TEXT,
                trip_type TEXT,
                operation TEXT,
                time_slot TEXT,
                schedule_time TEXT,
                trip_day TEXT,
                total_km REAL,
                start_time TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _insert_trip(self, trip_id: int, status: str = "assigned", trip_type: str = "pickup"):
        conn = self._new_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO trips (id, status, route_no, trip_type, operation, time_slot, schedule_time, trip_day, total_km)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trip_id,
                status,
                f"R{trip_id:04d}",
                trip_type,
                trip_type,
                "08:00",
                "08:00",
                "20260306",
                12.0,
            ),
        )
        conn.commit()
        conn.close()

    def _get_trip_status(self, trip_id: int) -> str:
        conn = self._new_conn()
        cur = conn.cursor()
        cur.execute("SELECT status FROM trips WHERE id = ?", (trip_id,))
        row = cur.fetchone()
        conn.close()
        return str(row["status"] if row else "")

    def test_admin_bypasses_pickup_pending_start_otps(self):
        self._insert_trip(1, status="assigned", trip_type="pickup")

        with patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.evaluate_trip_start_gate",
            return_value={"can_start_now": True},
        ), patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.get_pending_employee_otp_ids",
            return_value={"data": {"pending_employee_ids": ["101", "102"]}},
        ) as mock_pending, patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.log_trip_event"
        ) as mock_log:
            resp = self.client.post("/api/v2/trips/1/start", json={"by": "admin"})

        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertTrue(body.get("success"))
        self.assertEqual(self._get_trip_status(1), "started")
        # Gate should be bypassed for admin override, so pending OTP check isn't required.
        mock_pending.assert_not_called()
        logged_events = [str(call.args[0]) for call in mock_log.call_args_list if call.args]
        self.assertIn("trip_start_admin_override", logged_events)
        self.assertIn("trip_started", logged_events)

    def test_non_admin_pickup_still_blocked_with_pending_start_otps(self):
        self._insert_trip(2, status="assigned", trip_type="pickup")

        with patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.evaluate_trip_start_gate",
            return_value={"can_start_now": True},
        ), patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.get_pending_employee_otp_ids",
            return_value={"data": {"pending_employee_ids": ["101"]}},
        ):
            resp = self.client.post("/api/v2/trips/2/start", json={"by": "driver"})

        self.assertEqual(resp.status_code, 400)
        body = resp.get_json() or {}
        self.assertIn("Employee start OTP pending", str(body.get("message", "")))
        self.assertEqual(self._get_trip_status(2), "assigned")

    def test_already_started_is_idempotent(self):
        self._insert_trip(3, status="started", trip_type="pickup")

        with patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.evaluate_trip_start_gate",
            return_value={"can_start_now": True},
        ):
            resp = self.client.post("/api/v2/trips/3/start", json={"by": "admin"})

        self.assertEqual(resp.status_code, 200)
        body = resp.get_json() or {}
        self.assertIn("already started", str(body.get("message", "")).lower())
        self.assertEqual(self._get_trip_status(3), "started")

    def test_preassigned_guard_still_blocks_admin_override(self):
        self._insert_trip(4, status="assigned", trip_type="pickup")

        with patch(
            "rg_travel_backend.routes.trip_creation_v2_routes.evaluate_trip_start_gate",
            return_value={
                "can_start_now": False,
                "start_allowed_after": "2026-03-06T09:00:00",
                "seconds_until_start": 600,
                "server_now": "2026-03-06T08:50:00",
            },
        ):
            resp = self.client.post("/api/v2/trips/4/start", json={"by": "admin"})

        self.assertEqual(resp.status_code, 400)
        body = resp.get_json() or {}
        self.assertEqual(body.get("error_code"), "TRIP_NOT_STARTED_YET")
        self.assertEqual(self._get_trip_status(4), "assigned")


if __name__ == "__main__":
    unittest.main()
