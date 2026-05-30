import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import sqlite3
from datetime import datetime

# Add backend to path if needed (usually cwd is enough)
# sys.path.append(os.path.join(os.getcwd(), 'rg_travel_backend'))

from rg_travel_backend.services.admin_override_service import AdminOverrideService
from rg_travel_backend.repositories.trip_repo import TripRepo

def setup_db(conn):
    try:
        with open('rg_travel_backend/db/schema.sql', 'r') as f:
            schema = f.read()
        conn.executescript(schema)
        conn.execute("PRAGMA foreign_keys = ON;")
    except Exception as e:
        print(f"Error setting up DB: {e}")
        raise

class TestAdminOverride(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        setup_db(self.conn)
        
        self.db_patcher = patch('rg_travel_backend.services.admin_override_service.get_db', return_value=self.conn)
        self.mock_get_db = self.db_patcher.start()
        
        self.routing_patcher = patch('rg_travel_backend.services.admin_override_service.routing_service')
        self.mock_routing = self.routing_patcher.start()
        
        self.mock_routing.build_multi_stop_route.return_value = {
            "success": True,
            "polyline": "encoded_polyline_mock",
            "total_km": 15.5,
            "ordered_points": []
        }

        self.service = AdminOverrideService()
        self.repo = TripRepo(self.conn)
        self._populate_data()

    def tearDown(self):
        self.db_patcher.stop()
        self.routing_patcher.stop()
        self.conn.close()

    def _populate_data(self):
        cur = self.conn.cursor()
        now_str = datetime.utcnow().isoformat()
        
        # Add Admin (required for FK)
        cur.execute("INSERT INTO admins (id, name, mobile, password_salt, password_hash, created_at, updated_at) VALUES ('admin1', 'Admin', '000', 'salt', 'hash', ?, ?)", (now_str, now_str))

        # Add Drivers
        cur.execute("INSERT INTO drivers (id, name, mobile, vehicle_no, dl_no, password_salt, password_hash, created_at, updated_at) VALUES ('d1', 'Driver A', '999', 'CAB001', 'DL001', 'salt', 'hash', ?, ?)", (now_str, now_str))
        cur.execute("INSERT INTO drivers (id, name, mobile, vehicle_no, dl_no, password_salt, password_hash, created_at, updated_at) VALUES ('d2', 'Driver B', '888', 'CAB002', 'DL002', 'salt', 'hash', ?, ?)", (now_str, now_str))
        
        cur.execute("INSERT INTO employees (id, name, mobile, home_lat, home_lng) VALUES (101, 'Emp 1', '111', 12.9, 77.6)")
        cur.execute("INSERT INTO employees (id, name, mobile, home_lat, home_lng) VALUES (102, 'Emp 2', '222', 12.91, 77.61)")
        cur.execute("INSERT INTO employees (id, name, mobile, home_lat, home_lng) VALUES (103, 'Emp 3', '333', 12.92, 77.62)")
        
        # Add extra employees for full capacity test
        cur.execute("INSERT INTO employees (id, name, mobile) VALUES (104, 'Emp 4', '444')")
        cur.execute("INSERT INTO employees (id, name, mobile) VALUES (105, 'Emp 5', '555')")
        cur.execute("INSERT INTO employees (id, name, mobile) VALUES (106, 'Emp 6', '666')")
        
        self.conn.commit()

        self.trip1_id = self.repo.create_trip(
            route_no="20260001JAN",
            trip_type="pickup",
            trip_date="20260101",
            trip_time="09:00",
            status="assigned",
            driver_id="d1",
            vehicle_no="CAB001",
            vehicle_type="4",
            office_lat=12.95,
            office_lng=77.7
        )
        self.repo.add_trip_members(self.trip1_id, ["101", "102"])

        self.trip2_id = self.repo.create_trip(
            route_no="20260002JAN",
            trip_type="pickup",
            trip_date="20260101",
            trip_time="09:00",
            status="assigned",
            driver_id="d2",
            vehicle_no="CAB002",
            vehicle_type="4",
            office_lat=12.95,
            office_lng=77.7
        )
        self.repo.add_trip_members(self.trip2_id, ["103"])

    def test_move_employee_success(self):
        result = self.service.move_employee("admin1", "102", self.trip1_id, self.trip2_id)
        self.assertTrue(result["success"], f"Move failed: {result.get('message')}")
        
        m1_new = self.repo.list_trip_members(self.trip1_id)
        self.assertEqual(len(m1_new), 1)
        self.assertEqual(str(m1_new[0]["employee_id"]), "101")

        m2_new = self.repo.list_trip_members(self.trip2_id)
        self.assertEqual(len(m2_new), 2)
        
        t1 = self.repo.get_trip_by_id(self.trip1_id)
        self.assertGreater(t1["route_revision"], 1)
        self.assertEqual(self.mock_routing.build_multi_stop_route.call_count, 2)

    def test_move_employee_full_capacity(self):
        # Fill trip2 to capacity
        self.repo.add_trip_members(self.trip2_id, ["103", "104", "105", "106"]) 
        
        result = self.service.move_employee("admin1", "101", self.trip1_id, self.trip2_id)
        self.assertFalse(result["success"])

    def test_swap_vehicle_success(self):
        result = self.service.swap_vehicle("admin1", self.trip1_id, "CAB_NEW", "d_new")
        self.assertTrue(result["success"])

        updated_trip = self.repo.get_trip_by_id(self.trip1_id)
        self.assertEqual(updated_trip["vehicle_no"], "CAB_NEW")
        self.assertGreater(updated_trip["route_revision"], 1)

if __name__ == '__main__':
    unittest.main()
