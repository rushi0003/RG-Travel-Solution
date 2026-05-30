from .base_repository import BaseRepository
from typing import Optional, List, Dict

class DriverRepository(BaseRepository):
    
    def get_driver_by_id(self, driver_id: str) -> Optional[Dict]:
        query = """
            SELECT d.*, c.reg_no as cab_reg_no, c.model as cab_model, c.capacity as cab_capacity
            FROM drivers d
            LEFT JOIN cabs c ON d.vehicle_no = c.reg_no
            WHERE d.id = ?
        """
        row = self.fetch_one(query, (driver_id,))
        return dict(row) if row else None

    def find_available_driver(self, vehicle_type: str, needed_capacity: int) -> Optional[Dict]:
        """
        Find an available, approved, online driver with a specific vehicle type/capacity.
        This is a simplified selection logic.
        """
        # Logic: 
        # 1. Driver must be approved and online.
        # 2. Cabs must be active and match capacity.
        # 3. Driver must NOT have an active trip (status IN assigned, started).
        
        query = """
            SELECT d.id, d.name, d.mobile, c.reg_no, c.capacity
            FROM drivers d
            JOIN cabs c ON d.vehicle_no = c.reg_no
            WHERE d.is_approved = 1 
              AND d.is_online = 1
              AND c.status = 'active'
              AND c.capacity >= ?
              AND d.id NOT IN (
                  SELECT driver_id FROM trips 
                  WHERE status IN ('assigned', 'started') AND driver_id IS NOT NULL
              )
            LIMIT 1
        """
        # Note: If vehicle_type is strict (e.g. '4' vs '6'), add `AND c.capacity = ?` logic
        row = self.fetch_one(query, (needed_capacity,))
        return dict(row) if row else None

    def get_cab_by_reg_no(self, reg_no: str) -> Optional[Dict]:
        query = "SELECT * FROM cabs WHERE reg_no = ?"
        row = self.fetch_one(query, (reg_no,))
        return dict(row) if row else None
