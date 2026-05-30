# backend/services/availability_service.py
# RG Travel Solution - Cab & Driver Availability Service
# STEP 3: Resource availability scanning for trip assignment

from datetime import datetime
from typing import Dict, Any, List, Optional
from db import get_db


def scan_cab_availability(
    vehicle_type: Optional[str] = None,
    include_offline: bool = False
) -> Dict[str, Any]:
    """
    Scan available cabs and approved drivers.
    
    Args:
        vehicle_type: Filter by "4" or "6" seater (optional)
        include_offline: Include offline drivers (default False)
    
    Returns:
        {
            "success": True/False,
            "message": str (if error),
            "data": {
                "available4Count": int,
                "available6Count": int,
                "totalAvailable": int,
                "drivers": [...],  # Available drivers
                "unavailable_drivers": [...],  # Drivers in active trips
                "summary": {...}
            }
        }
    
    Logic:
        - Fetch approved drivers (is_approved = 1)
        - LEFT JOIN with trips to find drivers in active trips
        - Active trips: status IN ('created', 'assigned', 'started') AND trip_day = today
        - Build capacity inventory by vehicle_type
        - Return error if no cabs available
    """
    conn = get_db()
    today_trip_day = datetime.now().strftime("%Y%m%d")
    
    # Fetch approved drivers with their vehicle info and check active trip status
    base_sql = """
        SELECT 
            d.id as driver_id,
            d.name,
            d.mobile,
            d.vehicle_no,
            d.vehicle_type,
            d.is_online,
            t.id as active_trip_id,
            t.route_no,
            t.status
        FROM drivers d
        LEFT JOIN trips t ON t.driver_id = d.id 
            AND t.status IN ('created', 'assigned', 'started')
            AND t.trip_day = ?
        WHERE d.is_approved = 1
    """
    
    params: List[Any] = [today_trip_day]
    
    # Optional filters
    if vehicle_type and vehicle_type in ("4", "6"):
        base_sql += " AND d.vehicle_type = ?"
        params.append(vehicle_type)
    
    if not include_offline:
        base_sql += " AND d.is_online = 1"
    
    try:
        cur = conn.cursor()
        cur.execute(base_sql, tuple(params))
        rows = cur.fetchall()
    finally:
        conn.close()
    
    # Process results
    available_drivers: List[Dict[str, Any]] = []
    unavailable_drivers: List[Dict[str, Any]] = []
    count_4 = 0
    count_6 = 0
    
    for r in rows:
        driver_id = str(r[0] or "")
        name = str(r[1] or "")
        mobile = str(r[2] or "")
        vehicle_no = str(r[3] or "")
        vtype = str(r[4] or "4")  # Default to 4 if null
        is_online = bool(r[5])
        active_trip_id = r[6]
        route_no = str(r[7] or "") if r[7] else None
        
        driver_data = {
            "driver_id": driver_id,
            "name": name,
            "mobile": mobile,
            "vehicle_no": vehicle_no,
            "vehicle_type": vtype,
            "is_online": is_online
        }
        
        if active_trip_id:
            # Driver is in active trip - unavailable
            unavailable_drivers.append({
                **driver_data,
                "is_available": False,
                "reason": f"Assigned to active trip #{route_no}" if route_no else "Assigned to active trip"
            })
        else:
            # Driver is available
            available_drivers.append({
                **driver_data,
                "is_available": True
            })
            
            # Count by vehicle type for capacity inventory
            if vtype == "4":
                count_4 += 1
            elif vtype == "6":
                count_6 += 1
    
    total_available = count_4 + count_6
    
    # VALIDATION: No cabs available - return error
    if total_available == 0:
        reasons = []
        suggestions = []
        
        if unavailable_drivers:
            reasons.append("All approved drivers are currently assigned to active trips")
            suggestions.append("Wait for current trips to complete")
            suggestions.append("Consider scheduling trips for different time slots")
        else:
            reasons.append("No approved drivers found in system")
            suggestions.append("Check pending driver approval requests in Admin Dashboard")
            suggestions.append("Approve driver requests to increase fleet capacity")
        
        if not include_offline:
            suggestions.append("Contact drivers to mark themselves online")
        
        return {
            "success": False,
            "message": "No available cabs found",
            "data": {
                "available4Count": 0,
                "available6Count": 0,
                "totalAvailable": 0,
                "reasons": reasons,
                "suggestions": suggestions
            }
        }
    
    # SUCCESS: Return available drivers and capacity inventory
    return {
        "success": True,
        "data": {
            "available4Count": count_4,
            "available6Count": count_6,
            "totalAvailable": total_available,
            "drivers": available_drivers,
            "unavailable_drivers": unavailable_drivers,
            "summary": {
                "total_approved_drivers": len(rows),
                "drivers_in_active_trips": len(unavailable_drivers),
                "drivers_available": len(available_drivers)
            }
        }
    }
