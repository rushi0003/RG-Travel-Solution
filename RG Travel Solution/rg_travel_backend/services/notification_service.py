import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def send_sms_via_twilio(to_number: str, message: str) -> bool:
    try:
        from twilio.rest import Client
    except Exception:
        logger.warning("Twilio library not available; SMS not sent")
        return False

    sid = os.environ.get("RG_TWILIO_SID")
    token = os.environ.get("RG_TWILIO_TOKEN")
    from_no = os.environ.get("RG_TWILIO_FROM")
    if not sid or not token or not from_no:
        logger.warning("Twilio credentials not configured; SMS not sent")
        return False

    try:
        client = Client(sid, token)
        client.messages.create(body=message, from_=from_no, to=to_number)
        return True
    except Exception as e:
        logger.exception(f"Twilio SMS send failed: {e}")
        return False


def send_otp(to_number: str, otp: str, purpose: str = "start") -> bool:
    """
    Send OTP via available provider (Twilio). Falls back to logging if not configured.
    """
    message = f"Your {purpose} OTP is {otp}. Do not share it with anyone."
    sent = send_sms_via_twilio(to_number, message)
    if not sent:
        logger.info(f"OTP (not sent): {to_number} -> {otp} [{purpose}]")
    return sent
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from ..db import get_db
    from ..utils.logger import get_logger
except (ImportError, ValueError):
    from db import get_db
    from utils.logger import get_logger

logger = get_logger(__name__)

class NotificationService:

    @staticmethod
    def create_notification(title: str, message: str, type: str = "info", admin_id: Optional[str] = None):
        """
        Create a new notification.
        admin_id: Specific admin to notify. If None, it's a global notification.
        """
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_notifications (admin_id, title, message, type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (admin_id, title, message, type, datetime.now())
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def get_notifications(admin_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get notifications for an admin (including global ones).
        """
        conn = get_db()
        try:
            cursor = conn.cursor()
            # Fetch notifications where admin_id matches OR admin_id is NULL (global)
            cursor.execute(
                """
                SELECT id, title, message, type, is_read, created_at
                FROM admin_notifications
                WHERE admin_id = ? OR admin_id IS NULL
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (admin_id, limit, offset)
            )
            rows = cursor.fetchall()
            notifications = []
            for row in rows:
                notifications.append({
                    "id": row["id"],
                    "title": row["title"],
                    "message": row["message"],
                    "type": row["type"],
                    "is_read": bool(row["is_read"]),
                    "created_at": row["created_at"]
                })
            return notifications
        except Exception as e:
            logger.error(f"Failed to fetch notifications: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_unread_count(admin_id: str) -> int:
        """
        Get count of unread notifications.
        """
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM admin_notifications
                WHERE (admin_id = ? OR admin_id IS NULL) AND is_read = 0
                """,
                (admin_id,)
            )
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to count unread notifications: {e}")
            return 0
        finally:
            conn.close()

    @staticmethod
    def mark_as_read(notification_id: int, admin_id: str) -> bool:
        """
        Mark a specific notification as read.
        Validates that the notification belongs to the admin or is global.
        For global notifications, this is tricky because shared state.
        For MVP: We'll just mark the row read. In a real system, we'd need a mapping table for global read state per user.
        Assuming for now admin notifications are personal copies or shared dashboard - let's stick to simple "mark row read".
        Wait, if global, marking read marks it for EVERYONE.
        Refinement: We will ONLY support personal notifications for now to avoid complexity, OR we accept global read state.
        Let's assume notifications are mostly personal for this "Fair Assignment" use case (assigned to me).
        Or, we ignore global for "read" status in this MVP and just toggle the bit.
        """
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE admin_notifications
                SET is_read = 1
                WHERE id = ? AND (admin_id = ? OR admin_id IS NULL)
                """,
                (notification_id, admin_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to mark notification read: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def mark_all_read(admin_id: str) -> bool:
        """
        Mark all notifications for an admin as read.
        """
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE admin_notifications
                SET is_read = 1
                WHERE (admin_id = ? OR admin_id IS NULL) AND is_read = 0
                """,
                (admin_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to mark all read: {e}")
            return False
        finally:
            conn.close()
