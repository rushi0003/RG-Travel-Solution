from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime


class AdminAccessManagementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, 'test_rg_travel.db')
        os.environ['RG_DB_PATH'] = self.db_path

        from app import create_app
        from db import get_db, init_db
        from utils.security import hash_password

        self._get_db = get_db
        self._hash_password = hash_password

        init_db()
        self.app = create_app()
        self.client = self.app.test_client()

        with self.app.app_context():
            conn = self._get_db()
            try:
                salt, password_hash = self._hash_password('secret123')
                now = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO admins (
                        id, name, mobile, email, password_salt, password_hash,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        'admin_seed',
                        'Seed Admin',
                        '9876543210',
                        'seed@example.com',
                        salt,
                        password_hash,
                        now,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def tearDown(self) -> None:
        os.environ.pop('RG_DB_PATH', None)
        self.tmp_dir.cleanup()

    def test_admin_can_create_list_and_delete_admin(self) -> None:
        login = self.client.post(
            '/api/admin/login',
            json={'mobile': '9876543210', 'password': 'secret123'},
        )
        self.assertEqual(login.status_code, 200, login.get_data(as_text=True))
        token = login.get_json()['data']['token']
        headers = {'Authorization': f'Bearer {token}'}

        create = self.client.post(
            '/api/admin/admins',
            headers=headers,
            json={
                'name': 'Ops Admin',
                'mobile': '9123456789',
                'password': 'welcome123',
                'email': 'ops@example.com',
                'office_name': 'HQ',
            },
        )
        self.assertEqual(create.status_code, 200, create.get_data(as_text=True))
        created_admin = create.get_json()['data']
        self.assertEqual(created_admin['name'], 'Ops Admin')

        listing = self.client.get('/api/admin/admins', headers=headers)
        self.assertEqual(listing.status_code, 200, listing.get_data(as_text=True))
        admins = listing.get_json()['data']
        self.assertEqual(len(admins), 2)
        self.assertTrue(any(admin['mobile'] == '9123456789' for admin in admins))

        delete = self.client.delete(
            f"/api/admin/admins/{created_admin['id']}",
            headers=headers,
        )
        self.assertEqual(delete.status_code, 200, delete.get_data(as_text=True))

        final_listing = self.client.get('/api/admin/admins', headers=headers)
        final_admins = final_listing.get_json()['data']
        self.assertEqual(len(final_admins), 1)
        self.assertFalse(any(admin['mobile'] == '9123456789' for admin in final_admins))


if __name__ == '__main__':
    unittest.main()
