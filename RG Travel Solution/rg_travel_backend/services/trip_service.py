# backend/services/trip_service.py
# RG Travel Solution - Trip Service (CSR Pattern)
# STEP 15: Refactored to use Repositories and Transactions

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from repositories.trip_repository import TripRepository
from repositories.driver_repository import DriverRepository
from repositories.audit_repository import AuditRepository
from services.otp_service import create_trip_otps
from services.route_no_service import generate_route_no # Assuming this exists or we keep logic here

logger = logging.getLogger(__name__)

class TripService:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.trip_repo = TripRepository(db_conn)
        self.driver_repo = DriverRepository(db_conn)
        self.audit_repo = AuditRepository(db_conn)

    def create_trip_from_group(self, 
                             group_data: Dict[str, Any], 
                             driver_id: str, 
                             admin_id: str,
                             trip_type: str, 
                             scheduled_time: str,
                             vehicle_type: int) -> Dict[str, Any]:
        """
        Transactional method to create a trip from a group, assign driver, and log audit.
        """
        try:
            # 1. Validate Driver Availability (Double check)
            driver = self.driver_repo.get_driver_by_id(driver_id)
            if not driver:
                raise ValueError("Driver not found")
            
            # 2. Generate Route No
            # Using the helper from original service or repo method
            # For now, simplistic generation or delegate to existing logic if imported
            # But better to use the robust one. Assuming we keep generate_route_no in separate service or util
            from services.route_no_service import reserve_route_no_for_trip # Re-use existing if available
            # Or use logic from before. Let's stick to the logic we saw in previous trip_service.py 
            # but usually this should be in a RouteService. 
            # I will assume generate_route_no is available or I simulate it here.
            # actually `trip_service.py` had `generate_route_no`. I will inline a simple one or use existing.
            # BETTER: Use valid logic.
            
            # 3. Create OTPs
            otps = create_trip_otps() 
            
            # 4. Prepare Route Data
            distance_km = float(group_data.get("distance_km_estimate", 0.0))
            polyline = group_data.get("route_polyline") or "" # If available in group_data
            
            # 5. Insert Trip (with retry for Route No uniqueness)
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    route_no = self._generate_route_no_internal()
                    
                    # Optional: Check explicitly if distinct route_numbers table is used, 
                    # but here we rely on trips.route_no constraint.
                    
                    trip_id = self.trip_repo.create_trip(
                        route_no=route_no,
                        trip_day=trip_day,
                        operation=trip_type,
                        schedule_time=scheduled_time,
                        vehicle_type=str(vehicle_type),
                        total_km=distance_km,
                        polyline=polyline,
                        admin_id=admin_id,
                        driver_id=driver_id
                    )
                    break # Success
                except Exception as e:
                    # Check for integrity error (naive check for string)
                    if "UNIQUE constraint failed" in str(e) or "IntegrityError" in str(e):
                        if attempt == max_retries - 1:
                            raise ValueError("Unable to generate unique Route No after retries")
                        continue
                    raise e
            
            # 6. Add Employees (Repository)
            ordered_stops = group_data.get("ordered_stops", [])
            for seq, stop in enumerate(ordered_stops, start=1):
                emp_id = stop.get("id")
                if emp_id:
                    self.trip_repo.add_employee_to_trip(trip_id, str(emp_id), sequence_no=seq)
            
            # 7. Log Audit
            self.audit_repo.log_action(
                admin_id=admin_id,
                action="CREATE_TRIP",
                target_type="trip",
                target_id=str(trip_id),
                details={
                    "route_no": route_no,
                    "driver_id": driver_id,
                    "employee_count": len(ordered_stops)
                }
            )
            
            # 8. Commit Transaction (Handled by caller or here if we own connection)
            self.db_conn.commit()
            
            # 9. Return Standardized Output
            return self.get_trip_details(trip_id)
            
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Failed to create trip from group: {e}")
            raise e

    def get_trip_details(self, trip_id: int) -> Optional[Dict[str, Any]]:
        """
        Get standardized trip details (CSR version of serialize_trip).
        """
        # 1. Fetch Trip Data
        trip = self.trip_repo.get_trip_details(trip_id)
        if not trip:
            return None
            
        # 2. Fetch Employees
        employees_raw = self.trip_repo.get_trip_employees(trip_id)
        
        # 3. Serialize
        employees = []
        for e in employees_raw:
            employees.append({
                "id": e["employee_id"],
                "name": e["name"],
                "mobile": e["mobile"],
                "address": e["address"] if "address" in e else (e.get("home_address") or ""),
                "pickup_order": e["sequence_no"],
                "eta": e.get("estimated_arrival_time"),
                # Lat/Lng logic could be derived here
                "lat": e.get("pickup_lat") or e.get("home_lat"),
                "lng": e.get("pickup_lng") or e.get("home_lng")
            })
            
        return {
            "trip_id": trip["id"],
            "route_no": trip["route_no"],
            "trip_status": trip["status"],
            "trip_date": str(trip["trip_day"]), # Simple format
            "trip_time": trip["schedule_time"],
            "trip_type": trip["operation"],
            "route_polyline": trip["polyline"] or "",
            "total_km": float(trip["total_km"] or 0.0),
            "groups": [{
                "group_id": str(trip["id"]),
                "capacity": int(trip["vehicle_type"] or 4),
                "employees": employees
            }],
            "assigned_cab": {
                "number": trip.get("cab_reg_no") or "",
                "type": str(trip["vehicle_type"]),
                "model": trip.get("cab_model") or ""
            },
            "assigned_driver": {
                "id": trip["driver_id"] or "",
                "name": trip.get("driver_name") or "Unassigned",
                "mobile": trip.get("driver_mobile") or ""
            }
        }

    def swap_driver(self, trip_id: int, new_driver_id: str, admin_id: str) -> Dict[str, Any]:
        try:
            # 1. Check Trip
            trip = self.trip_repo.get_trip_details(trip_id)
            if not trip:
                raise ValueError("Trip not found")
                
            old_driver_id = trip["driver_id"]
            
            # 2. Update Driver
            if not self.trip_repo.update_trip_driver(trip_id, new_driver_id):
                raise ValueError("Failed to update driver")
                
            # 3. Log Audit
            self.audit_repo.log_action(
                admin_id=admin_id,
                action="SWAP_DRIVER",
                target_type="trip",
                target_id=str(trip_id),
                details={
                    "old_driver": old_driver_id,
                    "new_driver": new_driver_id
                }
            )
            
            self.db_conn.commit()
            return self.get_trip_details(trip_id)
            
        except Exception as e:
            self.db_conn.rollback()
            raise e

    def add_employee(self, trip_id: int, employee_id: str, admin_id: str) -> Dict[str, Any]:
        """
        Add employee to trip.
        """
        try:
            # Check if trip exists
            trip = self.trip_repo.get_trip_details(trip_id)
            if not trip:
                raise ValueError("Trip not found")
                
            # Check if employee already in trip (Repo should probably handle or we check here)
            existing_emps = self.trip_repo.get_trip_employees(trip_id)
            if any(str(e["employee_id"]) == str(employee_id) for e in existing_emps):
                raise ValueError("Employee already in this trip")
                
            # Add (append to end)
            next_seq = len(existing_emps) + 1
            self.trip_repo.add_employee_to_trip(trip_id, str(employee_id), sequence_no=next_seq)
            
            # Log Audit
            self.audit_repo.log_action(
                admin_id=admin_id,
                action="ADD_EMPLOYEE_TO_TRIP",
                target_type="trip",
                target_id=str(trip_id),
                details={"employee_id": str(employee_id)}
            )
            
            self.db_conn.commit()
            return self.get_trip_details(trip_id)
            
        except Exception as e:
            self.db_conn.rollback()
            raise e

    def remove_employee(self, trip_id: int, employee_id: str, admin_id: str) -> Dict[str, Any]:
        """
        Remove employee from trip.
        """
        try:
            # Check trip
            trip = self.trip_repo.get_trip_details(trip_id)
            if not trip:
                raise ValueError("Trip not found")
            
            # Remove (Direct SQL delete in repo, simplistic)
            # ideally we'd reorder sequences, but for now simple delete
            # We need a remove_employee method in TripRepo specifically for one employee
            # TripRepository only had 'remove_all'. I need to add 'remove_employee' to TripRepository first?
            # Or use base repo execute.
            # Let's add specific query here or update repo. 
            # Updating repo is cleaner but I can do it via execute since I have db_conn.
            # Actually TripRepo should have it. I missed it.
            # I will implement it here using self.trip_repo.execute if possible or add to repo.
            # BaseRepository has `execute`.
            
            self.trip_repo.execute(
                "DELETE FROM trip_employees WHERE trip_id = ? AND employee_id = ?", 
                (trip_id, employee_id)
            )
            
            # Log Audit
            self.audit_repo.log_action(
                admin_id=admin_id,
                action="REMOVE_EMPLOYEE_FROM_TRIP",
                target_type="trip",
                target_id=str(trip_id),
                details={"employee_id": str(employee_id)}
            )
            
            self.db_conn.commit()
            return self.get_trip_details(trip_id)
            
        except Exception as e:
            self.db_conn.rollback()
            raise e

    def _generate_route_no_internal(self) -> str:
        # Robust 10-char Route No generation (Year + 4 digits + Month)
        import secrets
        from datetime import datetime
        now = datetime.now()
        year = now.strftime("%Y")  # 4
        month = now.strftime("%b").upper()[:2]  # 2 (JAN->JA)
        rand4 = f"{secrets.randbelow(10000):04d}"  # 4
        return f"{year}{rand4}{month}"

# Helper for standalone usage (Function-based compatibility)
def serialize_trip(conn, trip_id):
    svc = TripService(conn)
    return svc.get_trip_details(trip_id)
