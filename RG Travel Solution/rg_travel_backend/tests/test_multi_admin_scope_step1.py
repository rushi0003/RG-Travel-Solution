from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime


class MultiAdminScopeStep1Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, 'test_rg_travel.db')
        os.environ['RG_DB_PATH'] = self.db_path

        from app import create_app
        from db import get_db, init_db
        from utils.security import create_token, hash_password
        from services.trip_validation_service import (
            filter_eligible_employees,
            scan_cab_availability,
        )

        self._get_db = get_db
        self._create_token = create_token
        self._hash_password = hash_password
        self._filter_eligible_employees = filter_eligible_employees
        self._scan_cab_availability = scan_cab_availability

        init_db()
        self.app = create_app()
        self.client = self.app.test_client()

        with self.app.app_context():
            conn = self._get_db()
            try:
                salt1, hash1 = self._hash_password('secret123')
                salt2, hash2 = self._hash_password('secret456')
                now = datetime.utcnow().isoformat()
                conn.executemany(
                    """
                    INSERT INTO admins (
                        id, name, mobile, email, password_salt, password_hash,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        ('admin_a', 'Admin A', '9876543210', 'a@example.com', salt1, hash1, now, now),
                        ('admin_b', 'Admin B', '9876543211', 'b@example.com', salt2, hash2, now, now),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

        with self.app.app_context():
            self.admin_a_headers = {
                'Authorization': f"Bearer {self._create_token('admin_a', 'admin')['token']}"
            }
            self.admin_b_headers = {
                'Authorization': f"Bearer {self._create_token('admin_b', 'admin')['token']}"
            }

    def _employee_headers(self, employee_id: int | str):
        return {
            'Authorization': f"Bearer {self._create_token(str(employee_id), 'employee')['token']}"
        }

    def _driver_headers(self, driver_id: int | str):
        return {
            'Authorization': f"Bearer {self._create_token(str(driver_id), 'driver')['token']}"
        }

    def tearDown(self) -> None:
        os.environ.pop('RG_DB_PATH', None)
        self.tmp_dir.cleanup()

    def test_employee_crud_is_admin_scoped(self) -> None:
        create = self.client.post(
            '/api/admin/employees',
            headers=self.admin_a_headers,
            json={
                'name': 'Employee One',
                'mobile': '9000000001',
                'login_time': '09:00',
                'logout_time': '18:00',
                'address': 'Sector 1, Pune',
                'lat': 18.5204,
                'lng': 73.8567,
            },
        )
        self.assertEqual(create.status_code, 200, create.get_data(as_text=True))
        employee_id = create.get_json()['data']['employee_id']

        list_a = self.client.get('/api/admin/employees', headers=self.admin_a_headers)
        self.assertEqual(list_a.status_code, 200, list_a.get_data(as_text=True))
        employees_a = list_a.get_json()['data']
        self.assertEqual(len(employees_a), 1)
        self.assertEqual(employees_a[0]['mobile'], '9000000001')

        list_b = self.client.get('/api/admin/employees', headers=self.admin_b_headers)
        self.assertEqual(list_b.status_code, 200, list_b.get_data(as_text=True))
        self.assertEqual(list_b.get_json()['data'], [])

        update_b = self.client.put(
            f'/api/admin/employees/{employee_id}',
            headers=self.admin_b_headers,
            json={
                'name': 'Employee One Updated',
                'mobile': '9000000001',
                'login_time': '09:00',
                'logout_time': '18:00',
                'address': 'Sector 1, Pune',
                'lat': 18.5204,
                'lng': 73.8567,
            },
        )
        self.assertEqual(update_b.status_code, 404, update_b.get_data(as_text=True))

    def test_driver_visibility_is_admin_scoped(self) -> None:
        create = self.client.post(
            '/api/admin/drivers',
            headers=self.admin_a_headers,
            json={
                'name': 'Driver One',
                'mobile': '9111111111',
                'dl_no': 'MH1234567890123',
                'cab_no': 'MH12AB1234',
                'vehicle_type': '4',
                'home_town': 'Pune',
                'home_lat': 18.5204,
                'home_lng': 73.8567,
            },
        )
        self.assertEqual(create.status_code, 200, create.get_data(as_text=True))
        driver_id = create.get_json()['data']['driver_id']

        list_a = self.client.get('/api/admin/drivers', headers=self.admin_a_headers)
        self.assertEqual(list_a.status_code, 200, list_a.get_data(as_text=True))
        drivers_a = list_a.get_json()['data']
        self.assertEqual(len(drivers_a), 1)
        self.assertEqual(drivers_a[0]['id'], driver_id)

        list_b = self.client.get('/api/admin/drivers', headers=self.admin_b_headers)
        self.assertEqual(list_b.status_code, 200, list_b.get_data(as_text=True))
        self.assertEqual(list_b.get_json()['data'], [])

    def test_pending_employee_requests_are_not_shared_between_admins(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.executemany(
                    """
                    INSERT INTO employee_requests (
                        id, name, mobile, login_time, logout_time,
                        home_address, lat, lng, admin_id, status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            1, 'Pending A', '9000000101', '09:00', '18:00',
                            'Pune A', 18.5204, 73.8567, 'admin_a', 'Pending', now,
                        ),
                        (
                            2, 'Pending B', '9000000102', '09:00', '18:00',
                            'Pune B', 18.5304, 73.8667, 'admin_b', 'Pending', now,
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

        list_a = self.client.get('/api/admin/employee-requests', headers=self.admin_a_headers)
        self.assertEqual(list_a.status_code, 200, list_a.get_data(as_text=True))
        self.assertEqual([item['id'] for item in list_a.get_json()['data']], [1])

        list_b = self.client.get('/api/admin/employee-requests', headers=self.admin_b_headers)
        self.assertEqual(list_b.status_code, 200, list_b.get_data(as_text=True))
        self.assertEqual([item['id'] for item in list_b.get_json()['data']], [2])

        approve_cross = self.client.post(
            '/api/admin/employee-requests/1/approve',
            headers=self.admin_b_headers,
            json={},
        )
        self.assertEqual(approve_cross.status_code, 404, approve_cross.get_data(as_text=True))

        reject_cross = self.client.post(
            '/api/admin/employee-requests/2/reject',
            headers=self.admin_a_headers,
            json={'reason': 'wrong tenant'},
        )
        self.assertEqual(reject_cross.status_code, 404, reject_cross.get_data(as_text=True))

    def test_employee_signup_request_requires_company_and_sets_admin_id(self) -> None:
        companies = self.client.get('/api/auth/companies')
        self.assertEqual(companies.status_code, 200, companies.get_data(as_text=True))
        company_ids = [item['id'] for item in companies.get_json()['data']]
        self.assertEqual(company_ids, ['admin_a', 'admin_b'])

        missing_company = self.client.post(
            '/api/auth/employee/signup-request',
            json={
                'name': 'Emp Pending',
                'mobile': '9000000199',
                'login_time': '09:00',
                'logout_time': '18:00',
                'home_address': 'Pune',
            },
        )
        self.assertEqual(missing_company.status_code, 400, missing_company.get_data(as_text=True))

        created = self.client.post(
            '/api/auth/employee/signup-request',
            json={
                'name': 'Emp Pending',
                'mobile': '9000000199',
                'login_time': '09:00',
                'logout_time': '18:00',
                'home_address': 'Pune Camp Road',
                'admin_id': 'admin_b',
            },
        )
        self.assertEqual(created.status_code, 200, created.get_data(as_text=True))

        with self.app.app_context():
            conn = self._get_db()
            try:
                row = conn.execute(
                    "SELECT admin_id FROM employee_requests WHERE mobile = ?",
                    ('9000000199',),
                ).fetchone()
                self.assertIsNotNone(row)
                admin_id = row['admin_id'] if hasattr(row, 'keys') else row[0]
                self.assertEqual(admin_id, 'admin_b')
            finally:
                conn.close()

    def test_driver_signup_request_requires_company_and_sets_admin_id(self) -> None:
        missing_company = self.client.post(
            '/api/auth/driver/signup-request',
            json={
                'name': 'Drv Pending',
                'mobile': '9111111199',
                'dl_no': 'MH1234567890123',
                'cab_no': 'MH12AB1299',
                'vehicle_type': '4',
                'home_town': 'Pune Camp',
            },
        )
        self.assertEqual(missing_company.status_code, 400, missing_company.get_data(as_text=True))

        created = self.client.post(
            '/api/auth/driver/signup-request',
            json={
                'name': 'Drv Pending',
                'mobile': '9111111199',
                'dl_no': 'MH1234567890123',
                'cab_no': 'MH12AB1299',
                'vehicle_type': '4',
                'home_town': 'Pune Camp',
                'admin_id': 'admin_a',
            },
        )
        self.assertEqual(created.status_code, 200, created.get_data(as_text=True))

        with self.app.app_context():
            conn = self._get_db()
            try:
                row = conn.execute(
                    "SELECT admin_id FROM driver_requests WHERE mobile = ?",
                    ('9111111199',),
                ).fetchone()
                self.assertIsNotNone(row)
                admin_id = row['admin_id'] if hasattr(row, 'keys') else row[0]
                self.assertEqual(admin_id, 'admin_a')
            finally:
                conn.close()

    def test_trip_resources_and_live_trips_are_admin_scoped(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO employees (
                        id, name, mobile, employee_code, login_time, logout_time,
                        home_address, home_lat, home_lng, admin_id, is_active, is_approved,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        101, 'Emp A', '9000000011', 'EMP00101', '09:00', '18:00',
                        'Pune A', 18.5204, 73.8567, 'admin_a', now, now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO employees (
                        id, name, mobile, employee_code, login_time, logout_time,
                        home_address, home_lat, home_lng, admin_id, is_active, is_approved,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        202, 'Emp B', '9000000022', 'EMP00202', '09:00', '18:00',
                        'Pune B', 18.5304, 73.8667, 'admin_b', now, now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO drivers (
                        id, name, mobile, dl_no, vehicle_no, vehicle_type,
                        home_town, primary_admin_id, is_approved, is_online,
                        password_salt, password_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    """,
                    (
                        'drv_a', 'Driver A', '9111111122', 'MH1234567890999', 'MH12AA1111',
                        '4', 'Pune', 'admin_a', 'salt', 'hash', now, now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO drivers (
                        id, name, mobile, dl_no, vehicle_no, vehicle_type,
                        home_town, primary_admin_id, is_approved, is_online,
                        password_salt, password_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    """,
                    (
                        'drv_b', 'Driver B', '9222222233', 'MH1234567890888', 'MH12BB2222',
                        '4', 'Pune', 'admin_b', 'salt', 'hash', now, now,
                    ),
                )
                conn.executemany(
                    """
                    INSERT INTO driver_admin_assignments (driver_id, admin_id, is_active)
                    VALUES (?, ?, 1)
                    """,
                    [('drv_a', 'admin_a'), ('drv_b', 'admin_b')],
                )
                conn.execute(
                    """
                    INSERT INTO trips (
                        route_no, trip_day, operation, trip_type, schedule_time, status,
                        admin_id, driver_id, vehicle_type, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ('ROUTEA001', '20260315', 'pickup', 'pickup', '09:00', 'assigned', 'admin_a', 'drv_a', '4', now, now),
                )
                conn.execute(
                    """
                    INSERT INTO trips (
                        route_no, trip_day, operation, trip_type, schedule_time, status,
                        admin_id, driver_id, vehicle_type, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ('ROUTEB001', '20260315', 'pickup', 'pickup', '09:00', 'assigned', 'admin_b', 'drv_b', '4', now, now),
                )
                conn.executemany(
                    """
                    INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    [(1, 101, 1, now), (2, 202, 1, now)],
                )
                conn.commit()

                eligible_a, _ = self._filter_eligible_employees(
                    conn,
                    trip_type='pickup',
                    selected_time='09:00',
                    trip_day='20260315',
                    admin_id='admin_a',
                )
                self.assertEqual([emp['id'] for emp in eligible_a], [])

                availability_b = self._scan_cab_availability(
                    conn,
                    trip_type='pickup',
                    selected_time='10:00',
                    trip_day='20260315',
                    admin_id='admin_b',
                )
                self.assertTrue(availability_b['success'])
                self.assertEqual(availability_b['data']['available_driver_count'], 1)
                self.assertEqual(availability_b['data']['available_drivers'][0]['id'], 'drv_b')
            finally:
                conn.close()

        live_a = self.client.get('/api/admin/trips/live', headers=self.admin_a_headers)
        self.assertEqual(live_a.status_code, 200, live_a.get_data(as_text=True))
        trips_a = live_a.get_json()['data']
        self.assertEqual(len(trips_a), 1)
        self.assertEqual(trips_a[0]['route_no'], 'ROUTEA001')

        live_b = self.client.get('/api/admin/trips/live', headers=self.admin_b_headers)
        self.assertEqual(live_b.status_code, 200, live_b.get_data(as_text=True))
        trips_b = live_b.get_json()['data']
        self.assertEqual(len(trips_b), 1)
        self.assertEqual(trips_b[0]['route_no'], 'ROUTEB001')

    def test_driver_company_switch_filters_driver_views(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.executemany(
                    """
                    INSERT INTO drivers (
                        id, name, mobile, dl_no, vehicle_no, vehicle_type,
                        home_town, primary_admin_id, current_admin_id, is_approved,
                        is_online, password_salt, password_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    """,
                    [
                        (
                            'drv_switch', 'Switch Driver', '9333333333', 'MH1234567890777',
                            'MH12CC3333', '4', 'Pune', 'admin_a', 'admin_a',
                            'salt', 'hash', now, now,
                        ),
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO driver_admin_assignments (driver_id, admin_id, is_active)
                    VALUES (?, ?, 1)
                    """,
                    [('drv_switch', 'admin_a'), ('drv_switch', 'admin_b')],
                )
                conn.executemany(
                    """
                    INSERT INTO trips (
                        route_no, trip_day, operation, trip_type, schedule_time, status,
                        admin_id, driver_id, vehicle_type, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        ('SWA001', '20260315', 'pickup', 'pickup', '09:00', 'assigned', 'admin_a', 'drv_switch', '4', now, now),
                        ('SWB001', '20260315', 'pickup', 'pickup', '10:00', 'assigned', 'admin_b', 'drv_switch', '4', now, now),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

        driver_headers = self._driver_headers('drv_switch')

        companies = self.client.get('/api/driver/drv_switch/companies', headers=driver_headers)
        self.assertEqual(companies.status_code, 200, companies.get_data(as_text=True))
        companies_data = companies.get_json()['data']
        self.assertEqual(companies_data['selected_admin_id'], 'admin_a')
        self.assertEqual(len(companies_data['companies']), 2)

        profile_a = self.client.get('/api/driver/profile/drv_switch', headers=driver_headers)
        self.assertEqual(profile_a.status_code, 200, profile_a.get_data(as_text=True))
        self.assertEqual(profile_a.get_json()['data']['selected_admin_id'], 'admin_a')

        trips_a = self.client.get('/api/driver/drv_switch/my-trips', headers=driver_headers)
        self.assertEqual(trips_a.status_code, 200, trips_a.get_data(as_text=True))
        routes_a = [trip['route_no'] for trip in trips_a.get_json()['data']['trips']]
        self.assertEqual(routes_a, ['SWA001'])

        switch_resp = self.client.post(
            '/api/driver/drv_switch/switch-company',
            headers=driver_headers,
            json={'admin_id': 'admin_b'},
        )
        self.assertEqual(switch_resp.status_code, 200, switch_resp.get_data(as_text=True))
        self.assertEqual(switch_resp.get_json()['data']['selected_admin_id'], 'admin_b')

        assigned_b = self.client.get('/api/driver/drv_switch/assigned-trip', headers=driver_headers)
        self.assertEqual(assigned_b.status_code, 200, assigned_b.get_data(as_text=True))
        self.assertEqual(assigned_b.get_json()['data']['route_no'], 'SWB001')

        trips_b = self.client.get('/api/driver/drv_switch/my-trips', headers=driver_headers)
        self.assertEqual(trips_b.status_code, 200, trips_b.get_data(as_text=True))
        routes_b = [trip['route_no'] for trip in trips_b.get_json()['data']['trips']]
        self.assertEqual(routes_b, ['SWB001'])

    def test_driver_selected_company_blocks_other_company_history_and_actions(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO drivers (
                        id, name, mobile, dl_no, vehicle_no, vehicle_type,
                        home_town, primary_admin_id, current_admin_id, is_approved,
                        is_online, password_salt, password_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    """,
                    (
                        'drv_guard', 'Guard Driver', '9444444444', 'MH1234567890666',
                        'MH12DD4444', '4', 'Pune', 'admin_a', 'admin_a',
                        'salt', 'hash', now, now,
                    ),
                )
                conn.executemany(
                    """
                    INSERT INTO driver_admin_assignments (driver_id, admin_id, is_active)
                    VALUES (?, ?, 1)
                    """,
                    [('drv_guard', 'admin_a'), ('drv_guard', 'admin_b')],
                )
                conn.executemany(
                    """
                    INSERT INTO employees (
                        id, name, mobile, employee_code, login_time, logout_time,
                        home_address, home_lat, home_lng, admin_id, is_active, is_approved,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    [
                        (
                            301, 'Emp Hist A', '9000000301', 'EMP00301', '09:00', '18:00',
                            'Pune A', 18.5204, 73.8567, 'admin_a', now, now,
                        ),
                        (
                            302, 'Emp Hist B', '9000000302', 'EMP00302', '09:00', '18:00',
                            'Pune B', 18.5304, 73.8667, 'admin_b', now, now,
                        ),
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO trips (
                        id, route_no, trip_day, operation, trip_type, schedule_time, status,
                        admin_id, driver_id, vehicle_type, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (11, 'HISTA001', '20260314', 'pickup', 'pickup', '09:00', 'completed', 'admin_a', 'drv_guard', '4', now, now),
                        (12, 'HISTB001', '20260314', 'pickup', 'pickup', '10:00', 'completed', 'admin_b', 'drv_guard', '4', now, now),
                        (13, 'STARTB001', '20260315', 'pickup', 'pickup', '11:00', 'assigned', 'admin_b', 'drv_guard', '4', now, now),
                        (14, 'DONEB001', '20260315', 'pickup', 'pickup', '12:00', 'started', 'admin_b', 'drv_guard', '4', now, now),
                        (15, 'ACTB001', '20260315', 'pickup', 'pickup', '13:00', 'assigned', 'admin_b', 'drv_guard', '4', now, now),
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    [(11, 301, 1, now), (12, 302, 1, now), (15, 302, 1, now)],
                )
                conn.commit()
            finally:
                conn.close()

        driver_headers = self._driver_headers('drv_guard')

        history = self.client.get('/api/driver/drv_guard/trip-history', headers=driver_headers)
        self.assertEqual(history.status_code, 200, history.get_data(as_text=True))
        history_routes = [trip['route_no'] for trip in history.get_json()['data']]
        self.assertEqual(history_routes, ['HISTA001'])

        otp_resp = self.client.post(
            '/api/driver/drv_guard/trip/15/otp/verify',
            headers=driver_headers,
            json={'otp_type': 'start', 'otp': '123456', 'employee_id': 302},
        )
        self.assertEqual(otp_resp.status_code, 404, otp_resp.get_data(as_text=True))

        start_resp = self.client.post('/api/driver/drv_guard/trip/13/start', headers=driver_headers, json={})
        self.assertEqual(start_resp.status_code, 404, start_resp.get_data(as_text=True))

        complete_resp = self.client.post('/api/driver/drv_guard/trip/14/complete', headers=driver_headers, json={})
        self.assertEqual(complete_resp.status_code, 404, complete_resp.get_data(as_text=True))

        no_show_resp = self.client.post(
            '/api/driver/drv_guard/trip/15/no-show',
            headers=driver_headers,
            json={'employee_id': 302},
        )
        self.assertEqual(no_show_resp.status_code, 404, no_show_resp.get_data(as_text=True))

        swap_resp = self.client.post(
            '/api/driver/drv_guard/trip/15/swap-request',
            headers=driver_headers,
            json={
                'new_driver_name': 'Replacement Driver',
                'new_driver_mobile': '9555555555',
                'new_cab_no': 'MH12EE5555',
                'reason': 'vehicle issue',
            },
        )
        self.assertEqual(swap_resp.status_code, 404, swap_resp.get_data(as_text=True))

        cancel_resp = self.client.post(
            '/api/driver/drv_guard/trip/13/cancel-request',
            headers=driver_headers,
            json={'reason': 'Unable to drive'},
        )
        self.assertEqual(cancel_resp.status_code, 404, cancel_resp.get_data(as_text=True))

    def test_employee_views_stay_scoped_to_employee_admin(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.executemany(
                    """
                    UPDATE admins
                    SET office_name = ?, office_location = ?, office_address = ?
                    WHERE id = ?
                    """,
                    [
                        ('Admin A Office', '18.5204,73.8567', 'Pune Office A', 'admin_a'),
                        ('Admin B Office', '19.0760,72.8777', 'Mumbai Office B', 'admin_b'),
                    ],
                )
                conn.execute(
                    """
                    INSERT INTO employees (
                        id, name, mobile, employee_code, login_time, logout_time,
                        home_address, home_lat, home_lng, admin_id, is_active, is_approved,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        401, 'Scoped Employee', '9000000401', 'EMP00401', '09:00', '18:00',
                        'Pune Home', 18.5204, 73.8567, 'admin_a', now, now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO drivers (
                        id, name, mobile, dl_no, vehicle_no, vehicle_type,
                        home_town, primary_admin_id, is_approved, is_online,
                        password_salt, password_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    """,
                    (
                        'drv_emp', 'Employee Driver', '9666666666', 'MH1234567890555',
                        'MH12FF6666', '4', 'Pune', 'admin_a', 'salt', 'hash', now, now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO driver_admin_assignments (driver_id, admin_id, is_active)
                    VALUES (?, ?, 1)
                    """,
                    ('drv_emp', 'admin_a'),
                )
                conn.executemany(
                    """
                    INSERT INTO trips (
                        id, route_no, trip_day, operation, trip_type, schedule_time, status,
                        admin_id, driver_id, vehicle_type, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (21, 'EMPA001', '20260315', 'pickup', 'pickup', '09:00', 'assigned', 'admin_a', 'drv_emp', '4', now, now),
                        (22, 'EMPB001', '20260315', 'pickup', 'pickup', '10:00', 'assigned', 'admin_b', 'drv_emp', '4', now, now),
                        (23, 'EMPHA01', '20260314', 'pickup', 'pickup', '08:00', 'completed', 'admin_a', 'drv_emp', '4', now, now),
                        (24, 'EMPHB01', '20260314', 'pickup', 'pickup', '07:00', 'completed', 'admin_b', 'drv_emp', '4', now, now),
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show, created_at)
                    VALUES (?, ?, ?, 0, ?)
                    """,
                    [(21, 401, 1, now), (22, 401, 1, now), (23, 401, 1, now), (24, 401, 1, now)],
                )
                conn.commit()
            finally:
                conn.close()

        employee_headers = self._employee_headers(401)

        profile = self.client.get('/api/employee/401/profile', headers=employee_headers)
        self.assertEqual(profile.status_code, 200, profile.get_data(as_text=True))
        profile_data = profile.get_json()['data']
        self.assertEqual(profile_data['admin_id'], 'admin_a')
        self.assertEqual(profile_data['office_address'], 'Pune Office A')

        active_trip = self.client.get(
            '/api/employee/401/my-trip?trip_date=2026-03-15',
            headers=employee_headers,
        )
        self.assertEqual(active_trip.status_code, 200, active_trip.get_data(as_text=True))
        self.assertTrue(active_trip.get_json()['data']['has_trip'])
        self.assertEqual(active_trip.get_json()['data']['trip']['route_no'], 'EMPA001')

        active_trips = self.client.get(
            '/api/employee/401/my-trips?date=2026-03-15',
            headers=employee_headers,
        )
        self.assertEqual(active_trips.status_code, 200, active_trips.get_data(as_text=True))
        active_routes = [trip['route_no'] for trip in active_trips.get_json()['data']['trips']]
        self.assertEqual(active_routes, ['EMPA001'])

        history = self.client.get('/api/employee/401/trip-history', headers=employee_headers)
        self.assertEqual(history.status_code, 200, history.get_data(as_text=True))
        history_routes = [trip['route_no'] for trip in history.get_json()['data']]
        self.assertEqual(history_routes, ['EMPHA01'])

    def test_employee_auth_blocks_cross_user_access(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO employees (
                        id, name, mobile, employee_code, login_time, logout_time,
                        home_address, home_lat, home_lng, admin_id, is_active, is_approved,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        501, 'Auth Employee', '9000000501', 'EMP00501', '09:00', '18:00',
                        'Pune', 18.5204, 73.8567, 'admin_a', now, now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        wrong_headers = self._employee_headers(999)

        profile = self.client.get('/api/employee/501/profile', headers=wrong_headers)
        self.assertEqual(profile.status_code, 403, profile.get_data(as_text=True))

        history = self.client.get('/api/employee/501/trip-history', headers=wrong_headers)
        self.assertEqual(history.status_code, 403, history.get_data(as_text=True))

        helpdesk = self.client.post(
            '/api/employee/501/helpdesk',
            headers=wrong_headers,
            json={'subject': 'Need help', 'message': 'Cross user test'},
        )
        self.assertEqual(helpdesk.status_code, 403, helpdesk.get_data(as_text=True))

    def test_driver_auth_blocks_cross_user_access(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO drivers (
                        id, name, mobile, dl_no, vehicle_no, vehicle_type,
                        home_town, primary_admin_id, current_admin_id, is_approved,
                        is_online, password_salt, password_hash, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    """,
                    (
                        'drv_auth', 'Auth Driver', '9777777777', 'MH1234567890444',
                        'MH12GG7777', '4', 'Pune', 'admin_a', 'admin_a',
                        'salt', 'hash', now, now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO driver_admin_assignments (driver_id, admin_id, is_active)
                    VALUES (?, ?, 1)
                    """,
                    ('drv_auth', 'admin_a'),
                )
                conn.execute(
                    """
                    INSERT INTO trips (
                        id, route_no, trip_day, operation, trip_type, schedule_time, status,
                        admin_id, driver_id, vehicle_type, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (31, 'DRVA001', '20260315', 'pickup', 'pickup', '09:00', 'assigned', 'admin_a', 'drv_auth', '4', now, now),
                )
                conn.commit()
            finally:
                conn.close()

        wrong_headers = self._driver_headers('drv_other')

        profile = self.client.get('/api/driver/profile/drv_auth', headers=wrong_headers)
        self.assertEqual(profile.status_code, 403, profile.get_data(as_text=True))

        companies = self.client.get('/api/driver/drv_auth/companies', headers=wrong_headers)
        self.assertEqual(companies.status_code, 403, companies.get_data(as_text=True))

        history = self.client.get('/api/driver/drv_auth/trip-history', headers=wrong_headers)
        self.assertEqual(history.status_code, 403, history.get_data(as_text=True))

        helpdesk = self.client.post(
            '/api/driver/drv_auth/helpdesk',
            headers=wrong_headers,
            json={'subject': 'Need help', 'message': 'Cross driver test'},
        )
        self.assertEqual(helpdesk.status_code, 403, helpdesk.get_data(as_text=True))

        start = self.client.post(
            '/api/driver/drv_auth/trip/31/start',
            headers=wrong_headers,
            json={},
        )
        self.assertEqual(start.status_code, 403, start.get_data(as_text=True))

    def test_admin_profile_auth_blocks_cross_admin_access(self) -> None:
        own = self.client.get('/api/admin/profile/admin_a', headers=self.admin_a_headers)
        self.assertEqual(own.status_code, 200, own.get_data(as_text=True))

        wrong = self.client.get('/api/admin/profile/admin_b', headers=self.admin_a_headers)
        self.assertEqual(wrong.status_code, 403, wrong.get_data(as_text=True))

        update_wrong = self.client.put(
            '/api/admin/profile/admin_b',
            headers=self.admin_a_headers,
            json={
                'name': 'Admin B',
                'mobile': '9876543211',
                'office_name': 'Office B',
                'office_address': 'Address B',
                'office_lat': 19.0760,
                'office_lng': 72.8777,
            },
        )
        self.assertEqual(update_wrong.status_code, 403, update_wrong.get_data(as_text=True))

    def test_admin_legacy_lists_are_tenant_scoped(self) -> None:
        with self.app.app_context():
            conn = self._get_db()
            try:
                now = datetime.utcnow().isoformat()
                conn.executemany(
                    """
                    INSERT INTO employees (
                        id, name, mobile, employee_code, login_time, logout_time,
                        home_address, home_lat, home_lng, admin_id, is_active, is_approved,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    [
                        (601, 'Legacy Emp A', '9000000601', 'EMP00601', '09:00', '18:00', 'Pune', 18.5204, 73.8567, 'admin_a', now, now),
                        (602, 'Legacy Emp B', '9000000602', 'EMP00602', '09:00', '18:00', 'Mumbai', 19.0760, 72.8777, 'admin_b', now, now),
                    ],
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS employee_change_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        name TEXT,
                        mobile TEXT,
                        home_address TEXT,
                        status TEXT,
                        created_at TEXT
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO employee_change_requests (
                        employee_id, name, mobile, home_address, status, created_at
                    )
                    VALUES (?, ?, ?, ?, 'Pending', ?)
                    """,
                    [
                        (601, 'Legacy Emp A Updated', '9000000601', 'Pune Updated', now),
                        (602, 'Legacy Emp B Updated', '9000000602', 'Mumbai Updated', now),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

        changes_a = self.client.get('/api/admin/employee-change-requests', headers=self.admin_a_headers)
        self.assertEqual(changes_a.status_code, 200, changes_a.get_data(as_text=True))
        change_employee_ids_a = [item['employee_id'] for item in changes_a.get_json()['data']]
        self.assertEqual(change_employee_ids_a, [601])


if __name__ == '__main__':
    unittest.main()
