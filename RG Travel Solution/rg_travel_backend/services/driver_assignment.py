# backend/services/driver_assignment.py
# RG Travel Solution - Fair Driver Assignment Service
# STEP 8: Intelligent driver assignment with rotation and workload balancing

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, cast
from dataclasses import dataclass

try:
    from db.database import query
except ImportError:
    # Handle environment differences
    from ..db.database import query

logger = logging.getLogger(__name__)


@dataclass
class DriverCandidate:
    """Driver candidate with workload metrics."""
    id: str
    name: str
    mobile: str
    vehicle_no: str
    vehicle_type: str
    home_town: Optional[str]
    
    # Workload metrics (calculated)
    weekly_trips: int = 0
    total_distance_km: float = 0.0
    consecutive_same_route: int = 0
    days_since_last_trip: int = 0
    workload_score: float = 0.0
    
    # Go Home priority
    go_home_requested: bool = False
    go_home_town: Optional[str] = None


def calculate_workload_score(
    weekly_trips: int,
    total_distance_km: float,
    consecutive_same_route: int,
    days_since_last_trip: int
) -> float:
    """
    Calculate driver workload score.
    Lower score = better candidate for assignment.
    
    Formula:
        score = (weekly_trips × 100) + 
                (total_distance_km × 10) + 
                (consecutive_same_route × 50) + 
                (days_since_last_trip × -20)
    
    Args:
        weekly_trips: Number of trips in last 7 days
        total_distance_km: Total distance driven in last 7 days
        consecutive_same_route: Days assigned to same route consecutively
        days_since_last_trip: Days since last completed trip
    
    Returns:
        Workload score (lower is better)
    
    Examples:
        Driver A: 12 trips, 250 km, 2 consecutive, 1 day rest
        → (12×100) + (250×10) + (2×50) + (1×-20) = 3780
        
        Driver B: 8 trips, 180 km, 0 consecutive, 3 days rest
        → (8×100) + (180×10) + (0×50) + (3×-20) = 2540 ✅ Better
    """
    score = (
        (weekly_trips * 100) +
        (total_distance_km * 10) +
        (consecutive_same_route * 50) +
        (days_since_last_trip * -20)
    )
    return float(int(score * 100) / 100.0)


def get_available_drivers(
    db_conn,
    vehicle_type: int,
    exclude_in_active_trips: bool = True
) -> List[DriverCandidate]:
    """
    Fetch approved drivers with matching vehicle type.
    
    Args:
        db_conn: Database connection
        vehicle_type: Required vehicle capacity (4 or 6)
        exclude_in_active_trips: Skip drivers already assigned to active trips
    
    Returns:
        List of DriverCandidate objects
    """
    from db.database import query
    
    sql = """
        SELECT d.id, d.name, d.mobile, d.vehicle_no, d.vehicle_type, d.home_town
        FROM drivers d
        WHERE d.is_approved = 1
        AND d.vehicle_type = ?
    """
    
    if exclude_in_active_trips:
        sql += """
            AND d.id NOT IN (
                SELECT driver_id FROM trips
                WHERE driver_id IS NOT NULL
                AND status IN ('assigned', 'started')
                AND date(schedule_time) = date('now')
            )
        """
    
    rows = query(db_conn, sql, [str(vehicle_type)])
    
    candidates = []
    cursor = db_conn.cursor() if hasattr(db_conn, "cursor") else None
    for row in rows:
        # Check for approved "Go Home" request for TODAY
        go_home_requested = False
        go_home_town = None
        
        try:
            # Check driver_hometown_requests table (approved for today)
            if cursor is not None:
                cursor.execute(
                    """
                    SELECT r.home_town FROM driver_hometown_requests r
                    WHERE r.driver_id = ? AND r.status = 'approved'
                    AND date(r.travel_date) = date('now')
                    AND NOT EXISTS (
                        SELECT 1
                        FROM trips t
                        WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                          AND LOWER(COALESCE(t.status, 'created')) IN
                              ('created','assigned','started','active','in_progress','live','completed')
                          AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                              datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                    )
                    LIMIT 1
                    """,
                    (row["id"],),
                )
                hometown_row = cursor.fetchone()
                if hometown_row:
                    go_home_requested = True
                    go_home_town = str(hometown_row[0])
            else:
                h_rows = query(
                    db_conn,
                    """
                    SELECT r.home_town FROM driver_hometown_requests r
                    WHERE r.driver_id = ? AND r.status = 'approved'
                    AND date(r.travel_date) = date('now')
                    AND NOT EXISTS (
                        SELECT 1
                        FROM trips t
                        WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                          AND LOWER(COALESCE(t.status, 'created')) IN
                              ('created','assigned','started','active','in_progress','live','completed')
                          AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                              datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                    )
                    LIMIT 1
                    """,
                    [row["id"]]
                )
                if h_rows:
                    go_home_requested = True
                    go_home_town = str(h_rows[0]["home_town"])
            if go_home_requested and not go_home_town:
                go_home_requested = True
                go_home_town = str(row.get("home_town") or "")
        except Exception as e:
            logger.debug(f"Could not check hometown requests: {e}")

        candidates.append(DriverCandidate(
            id=row["id"],
            name=row["name"],
            mobile=row["mobile"],
            vehicle_no=row["vehicle_no"],
            vehicle_type=row["vehicle_type"],
            home_town=row["home_town"],
            go_home_requested=go_home_requested,
            go_home_town=go_home_town
        ))
    
    return candidates


def get_driver_trip_history(
    db_conn,
    driver_id: str,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get driver's trip history for last N days.
    
    Args:
        db_conn: Database connection
        driver_id: Driver ID
        days: Number of days to look back
    
    Returns:
        List of trip records
    """
    from db.database import query
    
    sql = """
        SELECT 
            id, route_no, trip_day, operation, schedule_time,
            status, total_km, created_at
        FROM trips
        WHERE driver_id = ?
        AND status IN ('completed', 'started', 'assigned')
        AND julianday('now') - julianday(created_at) <= ?
        ORDER BY created_at DESC
    """
    
    return query(db_conn, sql, [driver_id, days])


def calculate_route_area(employees: List[Dict[str, Any]], operation: str) -> str:
    """
    Calculate route area identifier based on employee locations.
    Uses centroid lat/lng rounded to 2 decimals (approx 1km precision).
    
    Args:
        employees: List of employee points with coordinates
        operation: "pickup" or "drop"
    
    Returns:
        Route area identifier (e.g., "area_19.08_72.88")
    """
    if not employees:
        return "area_unknown"
    
    # Extract coordinates based on operation
    lats = []
    lngs = []
    
    for emp in employees:
        if operation == "pickup":
            lat = emp.get("pickup_lat") or emp.get("home_lat")
            lng = emp.get("pickup_lng") or emp.get("home_lng")
        else:  # drop
            lat = emp.get("home_lat") or emp.get("drop_lat")
            lng = emp.get("home_lng") or emp.get("drop_lng")
        
        if lat and lng:
            lats.append(lat)
            lngs.append(lng)
    
    if not lats:
        return "area_unknown"
    
    # Calculate centroid
    avg_lat = sum(lats) / len(lats)
    avg_lng = sum(lngs) / len(lngs)
    
    # Round to 2 decimals (heuristic avoiding Pyre round error)
    area_lat = float(int(avg_lat * 100) / 100.0)
    area_lng = float(int(avg_lng * 100) / 100.0)
    
    return f"area_{area_lat}_{area_lng}"


def count_consecutive_same_route(
    trip_history: List[Dict[str, Any]],
    route_area: str
) -> int:
    """
    Count consecutive days driver was assigned to same route area.
    
    Args:
        trip_history: List of trips (sorted by date, newest first)
        route_area: Target route area to check
    
    Returns:
        Number of consecutive days on same route
    """
    consecutive = 0
    
    # Group trips by day
    trips_by_day = {}
    for trip in trip_history:
        day = trip["trip_day"] or (trip["created_at"] or "")[:10].replace("-", "")
        if day not in trips_by_day:
            trips_by_day[day] = []
        trips_by_day[day].append(trip)
    
    # Sort days (newest first)
    sorted_days = sorted(trips_by_day.keys(), reverse=True)
    
    # Count consecutive days with same area
    # Note: We'd need route_area stored in trips table for accurate tracking
    # For now, use simple heuristic based on trip count
    
    # Simplified version: count recent trips (placeholder)
    # TODO: Store route_area in trips table for accurate tracking
    return 0  # Will be updated after database schema includes route_area


def calculate_days_since_last_trip(trip_history: List[Dict[str, Any]]) -> int:
    """
    Calculate days since driver's last completed trip.
    
    Args:
        trip_history: List of trips (sorted by date, newest first)
    
    Returns:
        Number of days since last trip (0 if today, max 7)
    """
    if not trip_history:
        return 7  # Max bonus for completely fresh driver
    
    # Get most recent trip
    latest_trip = trip_history[0]
    trip_date_str = latest_trip["trip_day"] or (latest_trip["created_at"] or "")[:10]
    
    try:
        if len(trip_date_str) == 8:  # YYYYMMDD format
            trip_date = datetime.strptime(trip_date_str, "%Y%m%d").date()
        else:  # ISO format
            trip_date = datetime.fromisoformat(trip_date_str).date()
        
        today = datetime.now().date()
        days_diff = (today - trip_date).days
        
        return min(days_diff, 7)  # Cap at 7 days
    
    except Exception as e:
        logger.warning(f"Error parsing trip date: {e}")
        return 0


def matches_hometown(
    driver: DriverCandidate,
    employees: List[Dict[str, Any]]
) -> bool:
    """
    Check if driver's hometown matches employee locations.
    Gives bonus for local knowledge.
    """
    # Prefer explicit go_home_town if set, else fallback to profile hometown
    town = driver.go_home_town or driver.home_town
    if not town:
        return False
    
    hometown_lower = str(town).lower()
    
    for emp in employees:
        # Check multiple address fields
        for addr_field in ["home_address", "pickup_address", "address"]:
            address = emp.get(addr_field, "")
            if address and hometown_lower in str(address).lower():
                return True
    
    return False


def assign_drivers_to_groups(
    db_conn,
    groups: List[List[Dict[str, Any]]],
    vehicle_type: int,
    operation: str,
    trip_day: str
) -> List[Dict[str, Any]]:
    """
    Assign drivers to groups using fair rotation algorithm.
    
    Algorithm:
        1. Get available drivers (matching vehicle type, not in active trips)
        2. Calculate workload score for each driver
        3. For each group, assign driver with lowest workload score
        4. Mark driver as used, continue to next group
    
    Args:
        db_conn: Database connection
        groups: List of employee groups (from clustering)
        vehicle_type: Required vehicle capacity (4 or 6)
        operation: Trip type (pickup/drop)
        trip_day: Trip date (YYYYMMDD)
    
    Returns:
        List of assignments: [
            {
                "group_index": 0,
                "driver_id": "drv_123",
                "driver_name": "John Doe",
                "vehicle_no": "MH12AB1234",
                "workload_score": 2540.0,
                "assignment_reason": "lowest_workload"
            },
            ...
        ]
    
    Raises:
        ValueError: If not enough drivers available
    """
    # Step 1: Get available drivers
    available_drivers = get_available_drivers(
        db_conn,
        vehicle_type=vehicle_type,
        exclude_in_active_trips=True
    )
    
    if len(available_drivers) < len(groups):
        raise ValueError("Driver shortage")
    
    # Step 2: Calculate workload for each driver
    for driver in available_drivers:
        # Get trip history
        history = get_driver_trip_history(db_conn, driver.id, days=7)
        
        # Calculate metrics
        driver.weekly_trips = len(history)
        driver.total_distance_km = sum((trip["total_km"] or 0) for trip in history)
        driver.days_since_last_trip = calculate_days_since_last_trip(history)
        
        # Calculate route area for first employee group (for consecutive check)
        # This is a placeholder - will be more accurate after schema update
        driver.consecutive_same_route = 0  # TODO: Implement after schema update
        
        # Calculate workload score
        driver.workload_score = calculate_workload_score(
            weekly_trips=driver.weekly_trips,
            total_distance_km=driver.total_distance_km,
            consecutive_same_route=driver.consecutive_same_route,
            days_since_last_trip=driver.days_since_last_trip
        )
    
    # Step 3: Assign drivers to groups
    assignments = []
    used_driver_ids = set()
    
    for group_idx, group in enumerate(groups):
        # Get candidates (not yet assigned)
        candidates = [d for d in available_drivers if d.id not in used_driver_ids]
        
        if not candidates:
            raise ValueError(f"Not enough drivers for group {group_idx}")
        
        # Apply hometown matching bonus
        for driver in candidates:
            if matches_hometown(driver, group):
                driver.workload_score -= 30  # Bonus for hometown match
        
        # Sort by workload score (ascending - lower is better)
        candidates.sort(key=lambda d: (d.workload_score, d.id))  # ID as tiebreaker
        
        # Select driver with lowest score
        selected_driver = candidates[0]
        
        # Determine assignment reason
        if selected_driver.go_home_requested and matches_hometown(selected_driver, group):
            reason = "go_home_priority"
        elif selected_driver.workload_score < 0:
            reason = "hometown_match"
        elif selected_driver.days_since_last_trip >= 3:
            reason = "rest_days_bonus"
        elif selected_driver.weekly_trips < 5:
            reason = "low_trip_count"
        else:
            reason = "lowest_workload"
        
        assignments.append({
            "group_index": group_idx,
            "driver_id": selected_driver.id,
            "driver_name": selected_driver.name,
            "vehicle_no": selected_driver.vehicle_no,
            "workload_score": float(int(selected_driver.workload_score * 100) / 100.0),
            "assignment_reason": reason,
            "weekly_trips": selected_driver.weekly_trips,
            "total_distance_km": float(int(selected_driver.total_distance_km * 100) / 100.0),
            "days_since_last": selected_driver.days_since_last_trip
        })
        
        used_driver_ids.add(selected_driver.id)
    
    return assignments
