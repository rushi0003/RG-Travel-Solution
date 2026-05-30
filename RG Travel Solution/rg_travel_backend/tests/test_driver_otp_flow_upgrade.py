import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

from rg_travel_backend.routes.driver_routes import driver_bp
from rg_travel_backend.services.otp_service import hash_otp


class TestDriverOtpFlowUpgrade(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix='otp_flow_upgrade_', suffix='.db')
        os.close(fd)
        self._prepare_db()

        self.app = Flask(__name__)
        self.app.register_blueprint(driver_bp)
        self.client = self.app.test_client()

        self.db_patcher = patch(
            'rg_travel_backend.routes.driver_routes.get_db',
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
            CREATE TABLE drivers (
                id TEXT PRIMARY KEY,
                driver_id TEXT,
                dl_no TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trips (
                id INTEGER PRIMARY KEY,
                driver_id TEXT,
                trip_type TEXT,
                status TEXT,
                time_slot TEXT,
                schedule_time TEXT,
                trip_day TEXT,
                total_km REAL,
                start_time TEXT,
                end_time TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                employee_id TEXT,
                is_no_show INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE trip_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                employee_id TEXT,
                otp_type TEXT,
                otp_hash TEXT,
                otp_length INTEGER DEFAULT 6,
                expires_at TEXT,
                is_used INTEGER DEFAULT 0,
                used_at TEXT,
                verified_by TEXT,
                attempts INTEGER DEFAULT 0,
                last_attempt_at TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE otp_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                otp_type TEXT,
                driver_id TEXT,
                employee_id TEXT,
                action TEXT,
                reason TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _seed_pickup_trip(self):
        conn = self._new_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO drivers(id, driver_id) VALUES ('d1', 'd1')")
        cur.execute(
            """
            INSERT INTO trips(id, driver_id, trip_type, status, time_slot, schedule_time, trip_day, total_km)
            VALUES (1, 'd1', 'pickup', 'assigned', '09:00', '09:00', '20260306', 10.0)
            """
        )
        cur.execute("INSERT INTO trip_employees(trip_id, employee_id, is_no_show) VALUES (1, '101', 0)")
        cur.execute("INSERT INTO trip_employees(trip_id, employee_id, is_no_show) VALUES (1, '102', 0)")
        cur.execute(
            """
            INSERT INTO trip_otps(trip_id, otp_type, otp_hash, expires_at, is_used, created_at, updated_at)
            VALUES (1, 'start', ?, '2099-01-01T00:00:00+00:00', 0, 'x', 'x')
            """,
            (hash_otp('111111'),),
        )
        conn.commit()
        conn.close()

    def _seed_drop_trip(self):
        conn = self._new_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO drivers(id, driver_id) VALUES ('d2', 'd2')")
        cur.execute(
            """
            INSERT INTO trips(id, driver_id, trip_type, status, time_slot, schedule_time, trip_day, total_km)
            VALUES (2, 'd2', 'drop', 'assigned', '18:00', '18:00', '20260306', 10.0)
            """
        )
        cur.execute("INSERT INTO trip_employees(trip_id, employee_id, is_no_show) VALUES (2, '201', 0)")
        cur.execute("INSERT INTO trip_employees(trip_id, employee_id, is_no_show) VALUES (2, '202', 0)")
        cur.execute(
            """
            INSERT INTO trip_otps(trip_id, otp_type, otp_hash, expires_at, is_used, created_at, updated_at)
            VALUES (2, 'end', ?, '2099-01-01T00:00:00+00:00', 0, 'x', 'x')
            """,
            (hash_otp('222222'),),
        )
        conn.commit()
        conn.close()

    def test_verify_requires_employee_id(self):
        self._seed_pickup_trip()
        resp = self.client.post(
            '/api/driver/d1/trip/1/otp/verify',
            json={'otp_type': 'start', 'otp': '111111'},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('employee_id is required', resp.get_json()['message'])

    def test_pickup_start_blocked_until_all_employee_start_otp_verified(self):
        self._seed_pickup_trip()

        blocked = self.client.post('/api/driver/d1/trip/1/start')
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('Employee start OTP pending', blocked.get_json()['message'])

        v1 = self.client.post(
            '/api/driver/d1/trip/1/otp/verify',
            json={'otp_type': 'start', 'otp': '111111', 'employee_id': '101'},
        )
        self.assertEqual(v1.status_code, 200)

        still_blocked = self.client.post('/api/driver/d1/trip/1/start')
        self.assertEqual(still_blocked.status_code, 400)

        v2 = self.client.post(
            '/api/driver/d1/trip/1/otp/verify',
            json={'otp_type': 'start', 'otp': '111111', 'employee_id': '102'},
        )
        self.assertEqual(v2.status_code, 200)

        allowed = self.client.post('/api/driver/d1/trip/1/start')
        self.assertEqual(allowed.status_code, 200)
        self.assertIn('Trip started', allowed.get_json()['message'])

    def test_drop_flow_requires_all_end_otp_before_complete(self):
        self._seed_drop_trip()

        start = self.client.post('/api/driver/d2/trip/2/start')
        self.assertEqual(start.status_code, 200)

        wrong_phase = self.client.post(
            '/api/driver/d2/trip/2/otp/verify',
            json={'otp_type': 'start', 'otp': '222222', 'employee_id': '201'},
        )
        self.assertEqual(wrong_phase.status_code, 400)
        self.assertIn('Drop trip accepts only end OTP', wrong_phase.get_json()['message'])

        blocked = self.client.post('/api/driver/d2/trip/2/complete')
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('Employee end OTP pending', blocked.get_json()['message'])

        v1 = self.client.post(
            '/api/driver/d2/trip/2/otp/verify',
            json={'otp_type': 'end', 'otp': '222222', 'employee_id': '201'},
        )
        self.assertEqual(v1.status_code, 200)

        still_blocked = self.client.post('/api/driver/d2/trip/2/complete')
        self.assertEqual(still_blocked.status_code, 400)

        v2 = self.client.post(
            '/api/driver/d2/trip/2/otp/verify',
            json={'otp_type': 'end', 'otp': '222222', 'employee_id': '202'},
        )
        self.assertEqual(v2.status_code, 200)

        done = self.client.post('/api/driver/d2/trip/2/complete')
        self.assertEqual(done.status_code, 200)
        self.assertIn('Trip completed', done.get_json()['message'])


if __name__ == '__main__':
    unittest.main()
