# backend/services/trip_validation_service.py
"""
RG Travel Solution - Trip Validation Service
Steps 1-3: Data Filtering + Availability Scan + Validation

**STEP 1: Define Filter by TripType + Time**
- Filter employees strictly by tripType and selectedTime
- If tripType=PICKUP: only employees whose loginTime == selectedTime
- If tripType=DROP: only employees whose logoutTime == selectedTime
- Exclude employees marked absent (pre-approved absence request)
- Exclude employees already assigned to an active trip
- Validation errors if no employees match

**STEP 2: Availability Scan (Cabs + Drivers)**
- Fetch all AVAILABLE cabs and APPROVED drivers
- Link each cab to its driver if assigned
- Build capacity inventory: available4Count, available6Count
- If no cabs available, return error
- If drivers not enough for cabs, limit usable cabs to driverCount
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TripValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_trip_request(
    trip_type: str,
    selected_time: str,
    vehicle_types: List[int],
    employee_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Validate basic trip request parameters.
    
    Args:
        trip_type: "pickup" or "drop"
        selected_time: HH:MM format (e.g., "09:00")
        vehicle_types: List of allowed vehicle types e.g. [4, 6]
        employee_ids: Optional list of employee IDs
        
    Returns:
        {"success": bool, "errors": [...], "warnings": [...]}
    """
    errors = []
    warnings = []
    
    # Validate trip type
    if trip_type not in ("pickup", "drop"):
        errors.append(f"Invalid trip_type: {trip_type}. Must be 'pickup' or 'drop'.")
    
    # Validate time format: HH:MM
    if not _is_valid_time_format(selected_time):
        errors.append(f"Invalid time format: {selected_time}. Expected HH:MM (24-hour).")
    
    # Validate vehicle types
    if not vehicle_types:
        errors.append("At least one vehicle type must be selected.")
    else:
        for vtype in vehicle_types:
            if vtype not in (4, 6):
                errors.append(f"Invalid vehicle_type: {vtype}. Must be 4 or 6.")
    
    # Warn if no employee filter
    if not employee_ids:
        warnings.append("No employee IDs specified. Will use all eligible employees.")
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def filter_eligible_employees(
    db_conn,
    trip_type: str,
    selected_time: str,
    employee_ids: Optional[List[int]] = None,
    trip_day: Optional[str] = None,
    admin_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    STEP 1: Filter employees by tripType and selectedTime.
    
    Rules:
    1. If trip_type=PICKUP: employee.login_time == selected_time
    2. If trip_type=DROP: employee.logout_time == selected_time
    3. Exclude employees with approved absence for trip_day
    4. Exclude employees who requested "No Trip" for trip_day
    5. Exclude employees already assigned to active trips
    6. Exclude inactive or unapproved employees
    
    Args:
        db_conn: Database connection
        trip_type: "pickup" or "drop"
        selected_time: HH:MM times
        employee_ids: Optional filter list
        trip_day: YYYYMMDD format for absence checking
        
    Returns:
        (eligible_employees, exclusions_list)
    """
    exclusions = []
    
    try:
        # Validate input
        time_key = "login_time" if trip_type == "pickup" else "logout_time"
        
        # Build query
        query = """
            SELECT 
                e.id, e.name, e.mobile, e.email,
                e.login_time, e.logout_time,
                e.is_active, e.is_approved,
                e.pickup_lat, e.pickup_lng, e.pickup_address,
                e.home_lat, e.home_lng, e.home_address,
                e.drop_lat, e.drop_lng, e.drop_location
            FROM employees e
            WHERE e.is_active = 1 AND e.is_approved = 1
        """
        params: List[Any] = []

        if admin_id:
            query += " AND CAST(COALESCE(e.admin_id, '') AS TEXT) = ?"
            params.append(str(admin_id))
        
        # Filter by selected time
        if trip_type == "pickup":
            query += " AND e.login_time = ?"
        else:  # drop
            query += " AND e.logout_time = ?"
        params.append(selected_time)
        
        # Optional: filter by specific employee IDs
        if employee_ids:
            placeholders = ",".join(["?" for _ in employee_ids])
            query += f" AND e.id IN ({placeholders})"
            for eid in employee_ids:
                params.append(eid)
        
        cursor = db_conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            exclusions.append(
                f"No active/approved employees found with {time_key}={selected_time}"
            )
            return [], exclusions
        
        candidates = []
        for row in rows:
            emp_id = row[0]
            
            # Check 1: Absence on trip_day
            if trip_day:
                # Ensure trip_day is str for type safety
                day: str = trip_day
                absence_check = _check_employee_absence(db_conn, emp_id, day)
                if absence_check:
                    exclusions.append(f"EMP#{emp_id}: Approved absence on {day}")
                    continue
                
                # Check 2: "No Trip" Request
                no_trip_check = _check_no_trip_request(db_conn, emp_id, day)
                if no_trip_check:
                    exclusions.append(f"EMP#{emp_id}: Requested 'No Trip' for {day}")
                    continue
            
            # Check 3: Already assigned to active trip for same day+time (strict)
            active_trip_check = _check_active_trip_assignment(
                db_conn, emp_id, trip_type, trip_day=trip_day, selected_time=selected_time
            )
            if active_trip_check:
                exclusions.append(f"EMP#{emp_id}: Already assigned to active {trip_type} trip")
                continue
            
            # Convert row to dict
            employee = {
                "id": row[0],
                "name": row[1],
                "mobile": row[2],
                "email": row[3],
                "login_time": row[4],
                "logout_time": row[5],
                "is_active": row[6],
                "is_approved": row[7],
                "pickup_lat": row[8],
                "pickup_lng": row[9],
                "pickup_address": row[10],
                "home_lat": row[11],
                "home_lng": row[12],
                "home_address": row[13],
                "drop_lat": row[14],
                "drop_lng": row[15],
                "drop_location": row[16],
            }
            candidates.append(employee)
        
        if not candidates:
            if exclusions:
                exclusions.insert(0, "All employees were filtered out:")
            else:
                exclusions.append("No eligible employees found.")
        
        return candidates, exclusions
    
    except Exception as e:
        logger.error(f"Error filtering employees: {e}")
        raise TripValidationError(f"Failed to filter employees: {str(e)}")


def scan_cab_availability(
    db_conn,
    vehicle_type: Optional[int] = None,
    driver_ids: Optional[List[int]] = None,
    trip_type: Optional[str] = None,
    selected_time: Optional[str] = None,
    trip_day: Optional[str] = None,
    admin_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    STEP 2: Fetch AVAILABLE cabs and APPROVED drivers.
    
    Args:
        driver_ids: Optional list of driver IDs to filter by (from vehicle selection step)
    
    Returns:
        {
            "success": bool,
            "message": str,
            "data": {
                "available_4_seaters": [{"id": "cab123", "driver_id": "drv456", ...}, ...],
                "available_6_seaters": [...],
                "available_4_count": 5,
                "available_6_count": 3,
                "available_drivers": [{"id": "drv001", "name": "John", ...}, ...],
                "available_driver_count": 8,
                "total_capacity": 23  # 5*4 + 3*6
            }
        }
    """
    try:
        cursor = db_conn.cursor()
        
        # Build driver filter clause if driver_ids provided
        driver_filter = ""
        base_params: List[Any] = []
        join_sql = ""
        if admin_id:
            join_sql = """
                INNER JOIN driver_admin_assignments daa
                    ON daa.driver_id = drivers.id
                   AND daa.admin_id = ?
                   AND daa.is_active = 1
            """
            base_params.append(str(admin_id))
        params: List[Any] = list(base_params)
        if driver_ids and len(driver_ids) > 0:
            placeholders = ",".join("?" * len(driver_ids))
            driver_filter = f" AND drivers.id IN ({placeholders})"
            params.extend(driver_ids)
        vehicle_filter = ""
        if vehicle_type in (4, 6):
            vehicle_filter = " AND CAST(drivers.vehicle_type AS TEXT) = ?"
            params.append(str(vehicle_type))

        # Exclude drivers already tied to non-completed trips.
        active_trip_predicates = [
            "driver_id IS NOT NULL",
            "LOWER(COALESCE(status, 'created')) IN ('created', 'assigned', 'started', 'active', 'in_progress')",
        ]
        if trip_type in ("pickup", "drop"):
            active_trip_predicates.append("LOWER(COALESCE(operation, trip_type, '')) = ?")
            params.append(trip_type)
        if selected_time:
            active_trip_predicates.append("COALESCE(time_slot, schedule_time, '') = ?")
            params.append(selected_time)
        if trip_day:
            normalized_day = str(trip_day).replace("-", "")
            active_trip_predicates.append("REPLACE(COALESCE(trip_day, ''), '-', '') = ?")
            params.append(normalized_day)
        active_trip_filter = (
            " AND drivers.id NOT IN (SELECT driver_id FROM trips WHERE "
            + " AND ".join(active_trip_predicates)
            + ")"
        )
        
        # Fetch all AVAILABLE cabs with their drivers
        cab_query = f"""
            SELECT 
                drivers.id, drivers.vehicle_no, drivers.vehicle_type, drivers.id as driver_id, drivers.is_online as status
            FROM drivers
            {join_sql}
            WHERE (drivers.is_online = 1 OR drivers.is_approved = 1){driver_filter}{vehicle_filter}
              {active_trip_filter}
            ORDER BY drivers.vehicle_type DESC
        """
        cursor.execute(cab_query, params)
        cabs = cursor.fetchall()
        
        # Fetch all APPROVED drivers (apply same filter if provided)
        driver_query = f"""
            SELECT 
                drivers.id, drivers.name, drivers.mobile, drivers.is_approved, drivers.is_online
            FROM drivers
            {join_sql}
            WHERE drivers.is_approved = 1{driver_filter}{vehicle_filter}
              {active_trip_filter}
            ORDER BY drivers.id
        """
        cursor.execute(driver_query, params)
        drivers = cursor.fetchall()
        
        # Categorize cabs by type
        cabs_4 = []
        cabs_6 = []
        assigned_cabs = set()
        
        for cab in cabs:
            cab_dict = {
                "id": cab[0],
                "vehicle_no": cab[1],
                "vehicle_type": cab[2],
                "driver_id": cab[3],
                "status": cab[4]
            }
            
            vtype = cab[2]
            if vtype == "4" or vtype == 4:
                cabs_4.append(cab_dict)
            elif vtype == "6" or vtype == 6:
                cabs_6.append(cab_dict)
            
            if cab[3]:  # driver_id assigned
                assigned_cabs.add(cab[0])
        
        # Drivers list
        drivers_list = []
        for driver in drivers:
            drivers_list.append({
                "id": driver[0],
                "name": driver[1],
                "mobile": driver[2],
                "is_approved": driver[3],
                "is_online": driver[4]
            })
        
        total_4_count = len(cabs_4)
        total_6_count = len(cabs_6)
        driver_count = len(drivers_list)
        
        # Validation: Enough drivers?
        total_cabs = total_4_count + total_6_count
        if driver_count < total_cabs:
            logger.warning(
                f"Driver shortage: {driver_count} drivers for {total_cabs} cabs. "
                f"Only {driver_count} cabs can be used."
            )
        
        total_capacity = (total_4_count * 4) + (total_6_count * 6)
        
        # Check for errors
        if not cabs_4 and not cabs_6:
            return {
                "success": False,
                "message": "No available cabs found",
                "data": None
            }
        
        if not drivers_list:
            return {
                "success": False,
                "message": "No approved drivers available",
                "data": None
            }
        
        return {
            "success": True,
            "message": f"Found {total_4_count} 4-seaters and {total_6_count} 6-seaters",
            "data": {
                "available_4_seaters": cabs_4,
                "available_6_seaters": cabs_6,
                "available_4_count": total_4_count,
                "available_6_count": total_6_count,
                "available_drivers": drivers_list,
                "available_driver_count": driver_count,
                "usable_cabs": min(total_cabs, driver_count),  # Limited by drivers
                "total_4_capacity": total_4_count * 4,
                "total_6_capacity": total_6_count * 6,
                "total_capacity": total_capacity
            }
        }
    
    except Exception as e:
        logger.error(f"Error scanning cab availability: {e}")
        raise TripValidationError(f"Failed to scan cab availability: {str(e)}")


def validate_sufficient_resources(
    employee_count: int,
    available_4: int,
    available_6: int,
    available_drivers: int
) -> Tuple[bool, Optional[str]]:
    """
    Check if we have sufficient resources to create a trip.
    
    Args:
        employee_count: Number of employees to assign
        available_4: Number of 4-seater cabs
        available_6: Number of 6-seater cabs
        available_drivers: Number of available drivers
        
    Returns:
        (is_valid, error_message)
    """
    total_capacity = (available_4 * 4) + (available_6 * 6)
    total_cabs = available_4 + available_6
    
    if employee_count == 0:
        return False, "No employees to assign"
    
    if not available_4 and not available_6:
        return False, "No available cabs"
    
    if available_drivers == 0:
        return False, "No available drivers"
    
    if available_drivers < total_cabs:
        total_cabs = available_drivers
        total_capacity = min(total_capacity, available_drivers * 6)
    
    if employee_count > total_capacity:
        return False, (
            f"Insufficient capacity: {employee_count} employees but only "
            f"{total_capacity} seats available ({available_4}×4 + {available_6}×6)"
        )
    
    return True, None


# ===================== HELPER FUNCTIONS =====================

def _is_valid_time_format(time_str: str) -> bool:
    """Validate HH:MM format (24-hour clock)"""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return False
        hour, minute = int(parts[0]), int(parts[1])
        return 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, AttributeError):
        return False


def _check_employee_absence(db_conn, employee_id: int, trip_day: str) -> bool:
    """
    Check if employee has an approved absence on trip_day.
    trip_day format: YYYYMMDD or YYYY-MM-DD
    """
    try:
        # Convert YYYYMMDD to YYYY-MM-DD if needed
        day_str = str(trip_day)
        if len(day_str) == 8 and "-" not in day_str:
            from datetime import datetime
            date_str = datetime.strptime(day_str, "%Y%m%d").strftime("%Y-%m-%d")
        else:
            date_str = day_str
        
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT 1 FROM employee_absences
            WHERE employee_id = ? AND absence_date = ? AND status = 'approved'
            LIMIT 1
            """,
            (str(employee_id), date_str)
        )
        
        return cursor.fetchone() is not None
    
    except Exception as e:
        logger.warning(f"Error checking absence for EMP#{employee_id}: {e}")
        return False


def _check_no_trip_request(db_conn, employee_id: int, trip_day: str) -> bool:
    """
    Check if employee has requested 'No Trip' for trip_day.
    trip_day format: YYYYMMDD or YYYY-MM-DD
    """
    try:
        # Convert YYYYMMDD to YYYY-MM-DD if needed
        day_str = str(trip_day)
        if len(day_str) == 8 and "-" not in day_str:
            from datetime import datetime
            date_str = datetime.strptime(day_str, "%Y%m%d").strftime("%Y-%m-%d")
        else:
            date_str = day_str
        
        cursor = db_conn.cursor()
        # Table might not exist yet if migration hasn't run, handle gracefully
        cursor.execute(
            """
            SELECT 1 FROM employee_trip_requests
            WHERE employee_id = ? AND request_date = ? AND request_type = 'no_trip' AND status = 'approved'
            LIMIT 1
            """,
            (str(employee_id), date_str)
        )
        
        return cursor.fetchone() is not None
    
    except Exception as e:
        # Gracefully handle missing table during migration phase
        if "no such table" in str(e).lower():
            return False
        logger.warning(f"Error checking no-trip request for EMP#{employee_id}: {e}")
        return False


def _check_active_trip_assignment(
    db_conn,
    employee_id: int,
    trip_type: str,
    trip_day: Optional[str] = None,
    selected_time: Optional[str] = None,
) -> bool:
    """
    Check if employee is already assigned to an active trip of the same type.
    When trip_day and selected_time are provided, only exclude if the existing
    trip is for the same day and same time slot (so other slots remain eligible).
    """
    try:
        cursor = db_conn.cursor()
        params: List[Any] = [str(employee_id), trip_type]
        where = (
            "te.employee_id = ? AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ? "
            "AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress')"
        )
        if trip_day:
            normalized_day = str(trip_day).replace("-", "")
            where += " AND REPLACE(COALESCE(t.trip_day, ''), '-', '') = ?"
            params.append(normalized_day)
        if selected_time:
            where += " AND COALESCE(t.time_slot, t.schedule_time, '') = ?"
            params.append(selected_time)
        cursor.execute(
            f"""
            SELECT 1 FROM trip_employees te
            JOIN trips t ON te.trip_id = t.id
            WHERE {where}
            LIMIT 1
            """,
            tuple(params),
        )
        return cursor.fetchone() is not None
    except Exception as e:
        logger.warning(f"Error checking active trips for EMP#{employee_id}: {e}")
        return False


def get_trip_validation_summary(
    validated_employees: List[Dict[str, Any]],
    cab_availability: Dict[str, Any],
    exclusions: List[str]
) -> Dict[str, Any]:
    """
    Build a comprehensive validation summary for the admin.
    
    Returns:
        {
            "total_eligible": int,
            "total_available_capacity": int,
            "capacity_4_seaters": int,
            "capacity_6_seaters": int,
            "available_drivers": int,
            "warnings": [],
            "errors": []
        }
    """
    data = cab_availability.get("data", {})
    
    errors = []
    warnings = []
    
    # Add any exclusion rules to warnings
    if exclusions:
        # Show first 5
        top_exclusions: List[str] = []
        limit = 5 if len(exclusions) > 5 else len(exclusions)
        for i in range(limit):
            top_exclusions.append(exclusions[i])
            
        warnings.extend(top_exclusions)
        if len(exclusions) > 5:
            warnings.append(f"... and {len(exclusions) - 5} more excluded")
    
    # Calculate utilization
    total_capacity = data.get("total_capacity", 0)
    available_drivers = data.get("available_driver_count", 0)
    employee_count = len(validated_employees)
    
    if employee_count > 0 and total_capacity > 0:
        utilization = (employee_count / total_capacity) * 100
        if utilization > 90:
            warnings.append("High capacity utilization (>90%)")
    
    return {
        "total_eligible": employee_count,
        "total_available_capacity": total_capacity,
        "capacity_4_seaters": data.get("total_4_capacity", 0),
        "capacity_6_seaters": data.get("total_6_capacity", 0),
        "available_drivers": available_drivers,
        "usable_cabs": data.get("usable_cabs", 0),
        "warnings": warnings,
        "errors": errors
    }
