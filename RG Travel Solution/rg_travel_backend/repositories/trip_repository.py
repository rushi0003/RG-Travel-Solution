from .base_repository import BaseRepository
from typing import Optional, List, Dict
from datetime import datetime
import json

class TripRepository(BaseRepository):
    
    def create_trip(self, route_no: str, trip_day: str, operation: str, schedule_time: str, 
                   vehicle_type: str, total_km: float, polyline: str, 
                   admin_id: str = None, driver_id: str = None) -> int:
        query = """
            INSERT INTO trips (
                route_no, trip_day, operation, trip_type, schedule_time, 
                vehicle_type, total_km, polyline, status, 
                admin_id, driver_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'created', ?, ?, ?, ?)
        """
        now = datetime.now().isoformat()
        self.execute(query, (
            route_no, trip_day, operation, operation, schedule_time, 
            vehicle_type, total_km, polyline, 
            admin_id, driver_id, now, now
        ))
        return self.cur.lastrowid

    def add_employee_to_trip(self, trip_id: int, employee_id: str, sequence_no: int = 0):
        query = """
            INSERT INTO trip_employees (trip_id, employee_id, sequence_no, created_at)
            VALUES (?, ?, ?, ?)
        """
        self.execute(query, (trip_id, employee_id, sequence_no, datetime.now().isoformat()))

    def get_trip_details(self, trip_id: int) -> Optional[Dict]:
        query = """
            SELECT t.*, 
                   c.reg_no as cab_reg_no, c.model as cab_model, c.capacity as cab_capacity,
                   d.name as driver_name, d.mobile as driver_mobile
            FROM trips t
            LEFT JOIN drivers d ON t.driver_id = d.id
            LEFT JOIN cabs c ON d.vehicle_no = c.reg_no
            WHERE t.id = ?
        """
        row = self.fetch_one(query, (trip_id,))
        return dict(row) if row else None

    def get_trip_employees(self, trip_id: int) -> List[Dict]:
        query = """
            SELECT te.*, e.name, e.mobile, COALESCE(e.home_address, '') AS address, e.pickup_lat, e.pickup_lng, e.drop_lat, e.drop_lng
            FROM trip_employees te
            JOIN employees e ON te.employee_id = e.id
            WHERE te.trip_id = ?
            ORDER BY te.sequence_no ASC
        """
        # Note: Address field might vary based on schema (e.g. pickup_address vs home_address)
        # Adjusting query to be generic or fetch available address fields
        query = """
            SELECT te.*, e.name, e.mobile, 
                   COALESCE(e.home_address, '') AS address, e.drop_location,
                   e.pickup_lat, e.pickup_lng, e.drop_lat, e.drop_lng
            FROM trip_employees te
            JOIN employees e ON te.employee_id = e.id
            WHERE te.trip_id = ?
            ORDER BY te.sequence_no ASC
        """
        rows = self.fetch_all(query, (trip_id,))
        return [dict(r) for r in rows]

    def update_trip_driver(self, trip_id: int, driver_id: str) -> bool:
        query = "UPDATE trips SET driver_id = ?, updated_at = ? WHERE id = ?"
        self.execute(query, (driver_id, datetime.now().isoformat(), trip_id))
        return self.cur.rowcount > 0

    def get_trip_by_route_no(self, route_no: str) -> Optional[Dict]:
        query = "SELECT * FROM trips WHERE route_no = ?"
        row = self.fetch_one(query, (route_no,))
        return dict(row) if row else None
    
    def remove_all_employees_from_trip(self, trip_id: int):
        self.execute("DELETE FROM trip_employees WHERE trip_id = ?", (trip_id,))
