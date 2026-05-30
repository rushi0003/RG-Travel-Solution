from .base_repository import BaseRepository
import json
from datetime import datetime

class AuditRepository(BaseRepository):
    def log_action(self, admin_id: str, action: str, target_type: str, target_id: str, details: dict, ip_address: str = None):
        """
        Log an admin action to the admin_audit table.
        """
        query = """
            INSERT INTO admin_audit 
            (admin_id, action, target_type, target_id, details, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute(query, (
            admin_id, 
            action, 
            target_type, 
            target_id, 
            json.dumps(details), 
            ip_address,
            datetime.now().isoformat()
        ))
