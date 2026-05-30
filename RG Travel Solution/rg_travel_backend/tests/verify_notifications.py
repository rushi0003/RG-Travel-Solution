import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add parent dir to path to import app setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.notification_service import NotificationService

class TestNotificationService(unittest.TestCase):

    def setUp(self):
        self.admin_id = "admin_123"

    @patch('services.notification_service.get_db')
    def test_create_and_get_notifications(self, mock_get_db):
        # Mock DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Test Create
        NotificationService.create_notification(
            title="Test Alert",
            message="This is a test",
            type="warning",
            admin_id=self.admin_id
        )
        
        # Verify Insert
        self.assertTrue(mock_cursor.execute.called)
        insert_sql = mock_cursor.execute.call_args_list[0][0][0]
        self.assertIn("INSERT INTO admin_notifications", insert_sql)

        # Test Get
        mock_cursor.fetchall.return_value = [
            {"id": 1, "title": "Test Alert", "message": "This is a test", "type": "warning", "is_read": 0, "created_at": "2023-01-01"}
        ]
        
        notes = NotificationService.get_notifications(self.admin_id)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['title'], "Test Alert")

    @patch('services.notification_service.get_db')
    def test_mark_read(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1

        result = NotificationService.mark_as_read(1, self.admin_id)
        
        self.assertTrue(result)
        self.assertTrue(mock_cursor.execute.called)
        update_sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("UPDATE admin_notifications", update_sql)

    @patch('services.notification_service.get_db')
    def test_mark_all_read(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = NotificationService.mark_all_read(self.admin_id)
        
        self.assertTrue(result)
        self.assertTrue(mock_cursor.execute.called)

if __name__ == '__main__':
    unittest.main()
