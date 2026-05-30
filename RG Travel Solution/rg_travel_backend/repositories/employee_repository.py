from .base_repository import BaseRepository
from typing import List, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime

class EmployeeRepository(BaseRepository):
    
    def fetch_eligible_employees(self, 
                               trip_day: str, 
                               time_window_val: str, 
                               operation: str, 
                               exclude_absent: bool = True, 
                               employee_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Fetch employees eligible for a trip.
        Strictly filters by:
        1. Login/Logout time matching selected time.
        2. Not marked as Absent for the given date (YYYY-MM-DD).
        3. Trip Not Required flag is 0.
        4. Not already in an active/assigned/started trip.
        """
        time_col = "login_time" if operation == "pickup" else "logout_time"
        
        # Convert trip_day (YYYYMMDD) to absence_date (YYYY-MM-DD) if needed
        # Assuming trip_day is passed as YYYYMMDD from service
        try:
             absence_date = f"{trip_day[:4]}-{trip_day[4:6]}-{trip_day[6:]}"
        except IndexError:
             absence_date = trip_day # Fallback if already formatted or invalid

        # Base query
        query = f"""
            SELECT
                e.id,
                e.name,
                e.mobile,
                COALESCE(e.home_address, '') AS address,
                COALESCE(e.home_lat, 0) AS home_lat,
                COALESCE(e.home_lng, 0) AS home_lng,
                COALESCE(e.pickup_lat, 0) AS pickup_lat,
                COALESCE(e.pickup_lng, 0) AS pickup_lng,
                COALESCE(e.login_time, '') AS login_time,
                COALESCE(e.logout_time, '') AS logout_time
            FROM employees e
            
            -- Exclusion 1: Active Trips
            LEFT JOIN (
                SELECT te.employee_id 
                FROM trip_employees te
                JOIN trips t ON t.id = te.trip_id
                WHERE t.status IN ('created', 'assigned', 'started', 'active') 
                  AND t.trip_day = ?
            ) busy_emp ON CAST(e.id AS TEXT) = busy_emp.employee_id

            -- Exclusion 2: Approved Absences
            LEFT JOIN employee_absences ea ON CAST(e.id AS TEXT) = ea.employee_id 
                AND ea.absence_date = ? 
                AND ea.status = 'approved'
            
            WHERE COALESCE(e.is_active, 1) = 1
              AND COALESCE(e.{time_col}, '') = ?
              AND busy_emp.employee_id IS NULL
        """
        
        params: List[Any] = [trip_day, absence_date, time_window_val]
        
        if exclude_absent:
            query += " AND ea.id IS NULL" # ensure no matching absence record found
            
        if employee_ids:
            placeholders = ",".join(["?"] * len(employee_ids))
            query += f" AND e.id IN ({placeholders})"
            params.extend(employee_ids)
            
        print(f"DEBUG QUERY: {query} params={params}")
        rows = self.fetch_all(query, tuple(params))
        return [dict(r) for r in rows]
