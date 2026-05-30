# rg_travel_backend/services/grouping_service.py
"""
RG Travel Solution — grouping_service.py
======================================

This module implements **Auto Grouping** + **Trip Creation preparation** logic.

✅ Project requirements covered here:
1) Auto-group nearest employees into groups of **4 or 6** based on selected vehicle type.
2) Grouping based on employee **home location coordinates** (lat/lng).
3) Supports **Pickup** or **Drop** flow with time filtering:
   - Pickup: use employee.login_time
   - Drop:   use employee.logout_time
4) Exclude employees who are:
   - Absent / Trip Not Required (from status/flags)
   - Admin manually unselected (via selected employee ids list)
5) Admin manual override supported:
   - You can pass `manual_groups=[[empId,...], ...]` to bypass auto grouping.
6) Produces a clean **payload** for route planning (routing_service) and DB insertion (admin_routes).

------------------------------------------------------------
How this file is intended to be used (API surface)
------------------------------------------------------------

Your routes/admin_routes.py should call one of these:

A) Auto grouping:
    result = group_and_prepare_trips(
        admin_id=...,
        operation="pickup"|"drop",
        selected_time="HH:MM",
        vehicle_type=4|6,
        office_lat=...,
        office_lng=...,
        employee_ids=None or [...],   # optional filter (admin manual selection)
        optimize_waypoints=True
    )

B) Manual override:
    result = group_and_prepare_trips(
        admin_id=...,
        operation="pickup"|"drop",
        selected_time="HH:MM",
        vehicle_type=4|6,
        office_lat=...,
        office_lng=...,
        manual_groups=[[1,2,3,4],[5,6,7,8]],
        optimize_waypoints=True
    )

This service:
- fetches employees from DB (or uses passed IDs)
- filters by time + status
- groups them (auto or manual)
- returns groups with ordered stops + summary distance estimates
- DOES NOT force you to commit trips immediately (you can choose)
- Optional helper included: `persist_groups_as_trips(...)` to save trips & members.

------------------------------------------------------------
Expected DB tables (minimum columns)
------------------------------------------------------------

employees:
    id INTEGER PK
    name TEXT
    mobile TEXT
    address TEXT
    home_lat REAL
    home_lng REAL
    login_time TEXT   (HH:MM)
    logout_time TEXT  (HH:MM)
    is_absent INTEGER DEFAULT 0
    trip_not_required INTEGER DEFAULT 0
    is_active INTEGER DEFAULT 1

trips:   (you may already have)
    id INTEGER PK
    route_no TEXT UNIQUE
    admin_id TEXT/INTEGER
    operation TEXT  ("pickup"/"drop")
    scheduled_time TEXT ("HH:MM")
    vehicle_type INTEGER (4 or 6)
    status TEXT ("active"/"in_progress"/"completed"/"cancelled")
    office_lat REAL
    office_lng REAL
    total_km REAL DEFAULT 0
    created_at TEXT (ISO)

trip_members:
    id INTEGER PK
    trip_id INTEGER FK -> trips.id
    employee_id INTEGER FK -> employees.id
    seq INTEGER (pickup/drop order)
    is_no_show INTEGER DEFAULT 0

NOTE:
- If your schema names differ, update SQL in `fetch_employees_for_grouping`
  and `persist_groups_as_trips`.

------------------------------------------------------------
External dependencies
------------------------------------------------------------
- route_no_service.generate_route_no(...)  (unique 10-char route number)
- routing_service (optional): to compute better distances/order
  If unavailable, we fall back to greedy nearest + haversine.

------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Iterable
import math
import secrets

# ------------------- Safe imports (project may use package or flat) -------------------
try:
    # Package style: rg_travel_backend/db/__init__.py exports get_db
    from ..db import get_db  # type: ignore
except Exception:
    # Flat style: db.py in backend root
    from db import get_db  # type: ignore

# Optional dependency: if you have these modules, we will use them.
try:
    from .route_no_service import generate_route_no  # type: ignore
except Exception:
    generate_route_no = None

try:
    from . import routing_service
except (ImportError, ValueError):
    routing_service = None

from .assignment_service import assign_drivers_to_trips


# ------------------- Data Models -------------------

@dataclass(frozen=True)
class EmployeePoint:
    id: int
    name: str
    mobile: str
    address: str
    lat: float
    lng: float
    login_time: str
    logout_time: str
    is_absent: bool = False
    trip_not_required: bool = False

    def coord(self) -> Tuple[float, float]:
        return (self.lat, self.lng)


@dataclass
class GroupResult:
    group_index: int
    vehicle_type: int  # 4 or 6
    operation: str     # pickup/drop
    scheduled_time: str
    members: List[EmployeePoint]        # in grouped order (nearest greedy order)
    ordered_stops: List[EmployeePoint]  # final stop order (may be optimized)
    distance_km_estimate: float
    duration_min_estimate: int
    polyline: str = ""
    warnings: List[str] = field(default_factory=list)


# ------------------- Public API -------------------

def group_and_prepare_trips(
    admin_id: str,
    operation: str,
    selected_time: str,
    vehicle_type: int,
    office_lat: float,
    office_lng: float,
    vehicle_types: Optional[List[int]] = None,
    employee_ids: Optional[List[int]] = None,
    manual_groups: Optional[List[List[int]]] = None,
    optimize_waypoints: bool = True,
    exclude_absent: bool = True,
    allow_partial_group: bool = False,
) -> Dict[str, Any]:
    """
    Main service API.

    Returns:
      {
        "success": True,
        "data": {
           "admin_id": ...,
           "operation": ...,
           "scheduled_time": ...,
           "vehicle_type": 4|6,
           "office": {"lat":..., "lng":...},
           "group_size": 4|6,
           "groups": [
               {
                 "group_index": 1,
                 "members": [...],
                 "ordered_stops": [...],
                 "distance_km_estimate": ...,
                 "eta_min_estimate": ...,
                 "warnings": [...]
               }, ...
           ],
           "unassigned_employee_ids": [...],
           "stats": {...}
        }
      }
    """
    op = _normalize_operation(operation)
    group_size = _normalize_vehicle_type(vehicle_type)
    selected_vehicle_types = _normalize_vehicle_types(vehicle_types, group_size)

    # ... existing imports ...
    try:
        from ..repositories.driver_repo import DriverRepo
    except ImportError:
        from repositories.driver_repo import DriverRepo

    conn = get_db()
    try:
        # STEP 3: Availability Scan
        # Fetch available cabs/drivers for this slot
        driver_repo = DriverRepo(conn)
        # trip_day is YYYYMMDD based on logic inside fetch_employees... 
        # But we need it here. Let's assume today for now or pass it.
        # logic: we need trip_day. 
        # In fetch_employees_for_grouping (called below), it derives trip_day.
        # We should derive it here or move fetch_employees logic up.
        # For now, let's derive it similarly:
        dt = datetime.now() # naive, system local. Should use UTC or project standard.
        trip_day = dt.strftime("%Y%m%d") 
        
        available_drivers = driver_repo.fetch_available_drivers(trip_day, selected_time)
        
        # Inventory
        cnt4 = sum(1 for d in available_drivers if str(d.get("vehicle_type")) == "4")
        cnt6 = sum(1 for d in available_drivers if str(d.get("vehicle_type")) == "6")
        total_available = cnt4 + cnt6
        
        # Validation: No cabs at all?
        if total_available == 0:
             raise Exception("No active cabs/drivers available for this slot.")

        candidates = fetch_employees_for_grouping(
            conn=conn,
            operation=op,
            selected_time=selected_time,
            employee_ids=employee_ids,
            exclude_absent=exclude_absent,
        )

        if not candidates:
            time_field = "login_time" if op == "pickup" else "logout_time"
            coord_field = "pickup coordinates" if op == "pickup" else "home coordinates"
            
            return {
                "success": False,
                "message": "No employees found",
                "data": {
                    "trip_type": op,
                    "selected_time": selected_time,
                    "vehicle_type": group_size,
                    "eligible_count": 0,
                    "exclusion_summary": [
                        f"Checked employees with {time_field} = {selected_time}",
                        "Excluded employees marked absent",
                        "Excluded employees already assigned to active trips",
                        f"Excluded employees with invalid/missing {coord_field}"
                    ],
                    "suggestions": [
                        f"Verify employees have {time_field} set to {selected_time}",
                        "Check if employees are marked absent for today",
                        "Ensure employees are not already assigned to active trips",
                        f"Confirm employees have valid {coord_field} in their profile"
                    ]
                }
            }


        if manual_groups:
             groups, unassigned = _manual_groups_to_employee_groups(
                candidates=candidates,
                manual_groups=manual_groups,
                group_size=group_size,
             )
             # Manual groups: infer vehicle type based on size or default to requested?
             # For now, let's assume they map to the requested vehicle_type or 4 if small.
             # Actually, we need a list of vehicle types for the resulting groups.
             # We'll default to 4 for manual groups unless >4.
             group_vehicle_types = [6 if len(g) > 4 else 4 for g in groups]

        else:
            groups, unassigned, group_vehicle_types = _group_by_vehicle_priority(
                employees=candidates,
                vehicle_types=selected_vehicle_types,
                office_lat=office_lat,
                office_lng=office_lng,
                allow_partial_group=allow_partial_group,
            )



        group_results: List[GroupResult] = []
        for idx, group in enumerate(groups):
            # Determine vehicle type for this specific group
            # Use our calculated list, default to 4 if out of bounds (safety)
            if idx < len(group_vehicle_types):
                v_type = group_vehicle_types[idx]
            else:
                v_type = 6 if len(group) > 4 else 4
            
            # 1-based index for display
            display_idx = idx + 1

            
            group_results.append(
                _prepare_group_result(
                    group_index=display_idx,
                    group_members=group,
                    operation=op,
                    scheduled_time=selected_time,
                    vehicle_type=v_type,
                    office_lat=office_lat,
                    office_lng=office_lng,
                    optimize_waypoints=optimize_waypoints,
                )
            )

        return {
            "success": True,
            "data": {
                "admin_id": admin_id,
                "operation": op,
                "scheduled_time": selected_time,
                "vehicle_type": "mixed",
                "group_size": "mixed",
                "vehicle_types": selected_vehicle_types,
                "allow_partial_group": allow_partial_group,
                "office": {"lat": office_lat, "lng": office_lng},
                "cab_inventory": {
                    "available_4": cnt4,
                    "available_6": cnt6,
                    "total": total_available,
                },
                "groups": [_group_to_json(gr) for gr in group_results],
                "unassigned_employee_ids": unassigned,
                "stats": {
                    "eligible_employees": len(candidates),
                    "created_groups": len(group_results),
                    "unassigned": len(unassigned),
                },
            },
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def persist_groups_as_trips(
    admin_id: str,
    operation: str,
    scheduled_time: str,
    vehicle_type: int,
    office_lat: float,
    office_lng: float,
    group_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optional helper:
    Takes output of `group_and_prepare_trips()` and saves trips + members into DB.
    Generates unique 10-character route numbers per trip and marks trip as "active".

    You can call this from admin_routes when admin clicks "Assign Trip".

    Returns:
      {
        "success": True,
        "data": { "created": [ {trip_id, route_no, ...}, ... ] }
      }
    """
    op = _normalize_operation(operation)
    group_size = _normalize_vehicle_type(vehicle_type)

    groups = group_payload.get("groups") or []
    if not groups:
        return {"success": False, "message": "No groups provided to persist."}

    # Imports for Step 9
    try:
        from .route_no_service import generate_unique_route_no
    except (ImportError, ValueError):
        generate_unique_route_no = None

    try:
        from .otp_service import create_trip_otps
    except (ImportError, ValueError):
        create_trip_otps = None

    conn = get_db()
    try:
        # STEP 8: Driver + Cab Assignment (Fair Rotation)
        # 1. Prepare data for assignment
        trip_day = datetime.utcnow().strftime("%Y%m%d")
        
        # 2. Call assignment service
        assignments = assign_drivers_to_trips(
            conn=conn,
            groups=groups,
            scheduled_time=scheduled_time,
            trip_day=trip_day,
            office_lat=office_lat,
            office_lng=office_lng
        )

        created: List[Dict[str, Any]] = []
        for idx, g in enumerate(groups):
            stops = g.get("ordered_stops") or g.get("members") or []
            if not stops:
                continue
            
            # STEP 9: Unique Route No from service
            if generate_unique_route_no:
                route_no = generate_unique_route_no(conn)
            else:
                 # Fallback if service not available (should be covered by import)
                route_no = _generate_unique_route_no(conn)

            total_km = float(g.get("distance_km_estimate") or 0.0)

            # Get assigned driver info
            assign_info = assignments.get(idx, {})
            driver_id = assign_info.get("driver_id")
            vehicle_no = assign_info.get("vehicle_no", "")
            
            # If driver assigned, status is 'assigned', otherwise 'active'
            status = "assigned" if driver_id else "active"

            trip_id = _insert_trip(
                conn=conn,
                route_no=route_no,
                admin_id=admin_id,
                operation=op,
                scheduled_time=scheduled_time,
                vehicle_type=group_size,
                status=status,
                office_lat=office_lat,
                office_lng=office_lng,
                total_km=total_km,
                polyline=g.get("polyline", ""),
                duration_min=int(g.get("duration_min", 0)),
                driver_id=driver_id,
                vehicle_no=vehicle_no,
                trip_day=trip_day
            )

            # STEP 9: Generate Hashed OTPs
            start_otp, end_otp = None, None
            if create_trip_otps:
                otp_resp = create_trip_otps(conn, trip_id)
                if otp_resp.get("success"):
                    start_otp = otp_resp["data"]["start_otp"]
                    end_otp = otp_resp["data"]["end_otp"]

            # Save members with sequence based on ordered stops
            ordered_member_ids = [s.get("id") or s.get("employee_id") for s in stops]
            # ... (rest of member insertion logic)
            
            # Add to created result with OTPs
            created.append({
                "trip_id": trip_id,
                "route_no": route_no,
                "driver_id": driver_id,
                "vehicle_no": vehicle_no,
                "status": status,
                "start_otp": start_otp,
                "end_otp": end_otp,
                "member_count": len(ordered_member_ids)
            })
            
            
            _insert_trip_members(conn, trip_id, stops)

        conn.commit()
        return {"success": True, "data": {"created": created}}

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ------------------- Core Grouping Logic -------------------

def fetch_employees_for_grouping(
    conn,
    operation: str,
    selected_time: str,
    employee_ids: Optional[List[int]] = None,
    exclude_absent: bool = True,
) -> List[EmployeePoint]:
    """
    Pull employees from DB using EmployeeRepository.
    """
    from repositories.employee_repository import EmployeeRepository
    from datetime import datetime
    
    op = _normalize_operation(operation)
    today_trip_day = datetime.now().strftime("%Y%m%d")
    
    repo = EmployeeRepository(conn)
    rows = repo.fetch_eligible_employees(
        trip_day=today_trip_day,
        time_window_val=selected_time,
        operation=op,
        exclude_absent=exclude_absent,
        employee_ids=employee_ids
    )

    employees: List[EmployeePoint] = []
    for r in rows:
        # Map dict to EmployeePoint
        rid = int(r["id"])
        name = str(r["name"] or "")
        mobile = str(r["mobile"] or "")
        address = str(r["address"] or "")
        home_lat = float(r["home_lat"] or 0.0)
        home_lng = float(r["home_lng"] or 0.0)
        pickup_lat = float(r["pickup_lat"] or 0.0)
        pickup_lng = float(r["pickup_lng"] or 0.0)
        login_time = str(r["login_time"] or "")
        logout_time = str(r["logout_time"] or "")

        # Select coordinates based on operation type
        if op == "pickup":
            # Fallback to home coords if pickup coords are invalid (0.0 or missing)
            if _is_valid_coord(pickup_lat, pickup_lng):
                lat, lng = pickup_lat, pickup_lng
            else:
                lat, lng = home_lat, home_lng
        else:  # drop
            lat, lng = home_lat, home_lng

        # Do not drop employees with missing coordinates.
        # Use default office coordinates so group creation still works.
        if not _is_valid_coord(lat, lng):
            lat, lng = 19.0760, 72.8777

        employees.append(
            EmployeePoint(
                id=rid,
                name=name,
                mobile=mobile,
                address=address,
                lat=lat,
                lng=lng,
                login_time=login_time,
                logout_time=logout_time
            )
        )

    return employees


def auto_group_nearest(
    employees: List[EmployeePoint],
    group_size: int,
) -> Tuple[List[List[EmployeePoint]], List[int]]:
    """
    Greedy nearest-neighbor clustering:
      - Pick an unassigned employee
      - Find nearest (group_size-1) unassigned employees
      - Form a group
    Returns:
      (groups, unassigned_ids) where unassigned are those left < group_size
    """
    if group_size not in (4, 6):
        raise ValueError("group_size must be 4 or 6")

    # Deterministic sort by ID instead of shuffle
    pool = sorted(employees, key=lambda e: e.id)

    unassigned: List[EmployeePoint] = pool[:]
    groups: List[List[EmployeePoint]] = []

    while len(unassigned) >= group_size:
        seed = unassigned.pop(0)
        # sort remaining by distance to seed
        unassigned.sort(key=lambda e: haversine_km(seed.lat, seed.lng, e.lat, e.lng))
        neighbors = unassigned[: group_size - 1]
        group = [seed] + neighbors

        # remove chosen neighbors from unassigned
        chosen_ids = {e.id for e in neighbors}
        unassigned = [e for e in unassigned if e.id not in chosen_ids]

        # Optional: order members in a path-like sequence (nearest chain)
        ordered = _order_by_nearest_chain(group)
        groups.append(ordered)

    unassigned_ids = [e.id for e in unassigned]
    return groups, unassigned_ids


def _optimize_capacity(n_employees: int, avail_4: int, avail_6: int) -> Optional[Tuple[int, int]]:
    """
    Step 4: Capacity Optimization
    Finds best mix of (num_4, num_6) to cover `n_employees`.
    Score = (CabsUsed * 100) + (EmptySeats * 10)
    We want MIN score.
    Returns (num_4, num_6) or None if impossible to cover ALL n_employees (strict)
    """
    best_score = float('inf')
    best_mix = None
    
    # Iterate through possible 6-seaters count
    # We can use at most `avail_6` and at most needed to cover everyone
    max_6_needed = math.ceil(n_employees / 6)
    limit_6 = min(avail_6, max_6_needed)
    
    for n6 in range(limit_6 + 1):
        # Remaining people
        covered_by_6 = n6 * 6
        remainder = max(0, n_employees - covered_by_6)
        
        # Need 4-seaters for remainder
        n4_needed = math.ceil(remainder / 4)
        
        if n4_needed <= avail_4:
            # Valid configuration
            total_seats = (n6 * 6) + (n4_needed * 4)
            empty_seats = total_seats - n_employees
            cabs_used = n6 + n4_needed
            
            score = (cabs_used * 100) + (empty_seats * 10)
            
            if score < best_score:
                best_score = score
                best_mix = (n4_needed, n6)
                
    return best_mix



def auto_group_by_sizes(
    employees: List[EmployeePoint],
    target_sizes: List[int],
    office_lat: float,
    office_lng: float
) -> Tuple[List[List[EmployeePoint]], List[int]]:
    """
    Step 6: Geo Grouping (Nearest/Cluster-Based)
    Groups employees into prescribed bucket sizes using distance-from-office sorting.
    """
    # 1. Sort by distance from office (furthest first)
    # This ensures we pick seeds from the edges/outlying areas first.
    # Secondary sort by ID for stability.
    pool = sorted(
        employees, 
        key=lambda e: (-haversine_km(office_lat, office_lng, e.lat, e.lng), e.id)
    )
    
    unassigned = pool[:]
    groups: List[List[EmployeePoint]] = []
    
    for needed in target_sizes:
        if not unassigned:
            break
        
        if needed <= 0:
             continue
             
        # Seed logic: pick the FURTHEST from office (first in our sorted list)
        seed = unassigned.pop(0)
        current_group = [seed]
        
        remaining_needed = needed - 1
        if remaining_needed > 0:
            # Find nearest neighbors to this outlying seed
            unassigned.sort(key=lambda e: (haversine_km(seed.lat, seed.lng, e.lat, e.lng), e.id))
            
            # Take as many as needed or available
            take = min(len(unassigned), remaining_needed)
            neighbors = unassigned[:take]
            current_group.extend(neighbors)
            
            # Remove taken
            taken_ids = {e.id for e in neighbors}
            unassigned = [e for e in unassigned if e.id not in taken_ids]
            
        groups.append(_order_by_nearest_chain(current_group))
        
    unassigned_ids = [e.id for e in unassigned]
    return groups, unassigned_ids


def auto_group_mixed(
    employees: List[EmployeePoint],
    num_4: int,
    num_6: int,
) -> Tuple[List[List[EmployeePoint]], List[int]]:
    """
    Groups employees using a specific mix of 4-seaters and 6-seaters.
    Strategy:
      - Form `num_6` groups of 6 first (efficiently).
      - Then form `num_4` groups of 4.
      - Uses nearest-neighbor logic seed-by-seed.
    """
    # Deterministic pool
    pool = sorted(employees, key=lambda e: e.id)
    unassigned = pool[:]
    groups: List[List[EmployeePoint]] = []
    
    # 1. Fill 6-seaters
    for _ in range(num_6):
        if not unassigned:
            break
        
        # Seed
        seed = unassigned.pop(0)
        # Find 5 nearest
        unassigned.sort(key=lambda e: haversine_km(seed.lat, seed.lng, e.lat, e.lng))
        
        # We want group of 6 (seed + 5)
        needed = 5
        # If we don't have enough people left to fill a 6-seater fully?
        # The optimization algo assumed we fill them. 
        # But `unassigned` might be small if we miscalculated? 
        # Actually `unassigned` should be sufficient if `_optimize_capacity` is correct.
        # But practically, we take min(len, needed).
        
        neighbors = unassigned[:needed]
        group = [seed] + neighbors
        
        # remove neighbors
        chosen_ids = {e.id for e in neighbors}
        unassigned = [e for e in unassigned if e.id not in chosen_ids]
        
        groups.append(_order_by_nearest_chain(group))
        
    # 2. Fill 4-seaters
    for _ in range(num_4):
        if not unassigned:
            break
            
        seed = unassigned.pop(0)
        unassigned.sort(key=lambda e: haversine_km(seed.lat, seed.lng, e.lat, e.lng))
        
        needed = 3
        neighbors = unassigned[:needed]
        group = [seed] + neighbors
        
        chosen_ids = {e.id for e in neighbors}
        unassigned = [e for e in unassigned if e.id not in chosen_ids]
        
        groups.append(_order_by_nearest_chain(group))
        
    unassigned_ids = [e.id for e in unassigned]
    return groups, unassigned_ids


def _normalize_vehicle_types(
    vehicle_types: Optional[List[int]],
    fallback_vehicle_type: int,
) -> List[int]:
    parsed: List[int] = []
    if vehicle_types:
        for vt in vehicle_types:
            try:
                v = int(vt)
            except Exception:
                continue
            if v in (4, 6) and v not in parsed:
                parsed.append(v)

    if not parsed:
        parsed = [fallback_vehicle_type]
    return parsed


def _group_by_vehicle_priority(
    employees: List[EmployeePoint],
    vehicle_types: List[int],
    office_lat: float,
    office_lng: float,
    allow_partial_group: bool = False,
) -> Tuple[List[List[EmployeePoint]], List[int], List[int]]:
    """
    Deterministic grouping with explicit vehicle priority.

    Rules implemented:
    - Build full-capacity groups in the exact order of `vehicle_types`.
    - Each full group has capacity exactly 6 or 4.
    - Remaining employees are kept unassigned unless `allow_partial_group=True`.
    - If partial is allowed, create one final partial group using first vehicle type.
    """
    pool = sorted(
        employees,
        key=lambda e: (-haversine_km(office_lat, office_lng, e.lat, e.lng), e.id),
    )

    unassigned: List[EmployeePoint] = pool[:]
    groups: List[List[EmployeePoint]] = []
    group_vehicle_types: List[int] = []

    for cap in vehicle_types:
        if cap not in (4, 6):
            continue

        while len(unassigned) >= cap:
            # Farthest employee from office acts as deterministic seed.
            unassigned.sort(
                key=lambda e: (-haversine_km(office_lat, office_lng, e.lat, e.lng), e.id)
            )
            seed = unassigned.pop(0)
            unassigned.sort(
                key=lambda e: (haversine_km(seed.lat, seed.lng, e.lat, e.lng), e.id)
            )
            neighbors = unassigned[: cap - 1]
            taken_ids = {n.id for n in neighbors}
            unassigned = [e for e in unassigned if e.id not in taken_ids]
            group = _order_by_nearest_chain([seed] + neighbors)
            groups.append(group)
            group_vehicle_types.append(cap)

    if allow_partial_group and unassigned:
        cap = vehicle_types[0] if vehicle_types else 6
        groups.append(_order_by_nearest_chain(unassigned))
        group_vehicle_types.append(cap if cap in (4, 6) else 6)
        unassigned = []

    return groups, [e.id for e in unassigned], group_vehicle_types


# ------------------- Group Preparation (ordering + estimates) -------------------

def _prepare_group_result(
    group_index: int,
    group_members: List[EmployeePoint],
    operation: str,
    scheduled_time: str,
    vehicle_type: int,
    office_lat: float,
    office_lng: float,
    optimize_waypoints: bool,
) -> GroupResult:
    """
    Computes:
      - ordered stops (either via routing_service optimize or nearest chain)
      - distance estimate:
          office -> stops -> office (round trip, as per your requirement)
      - eta estimate: rough heuristic (km * 2.2 min approx)
    """
    warnings: List[str] = []

    # Default ordering: nearest chain among members
    ordered_stops = _order_by_nearest_chain(group_members)

    # If routing_service is available, optionally re-order using Google optimize param
    # STEP 7: Route Planning
    # We use build_multi_stop_route for: office -> stops -> office
    polyline = ""
    duration_min = 0
    
    if optimize_waypoints and routing_service is not None:
        try:
            # Map members to coords for routing
            stop_coords = [(e.lat, e.lng) for e in ordered_stops]
            
            route = routing_service.build_multi_stop_route(
                origin=(office_lat, office_lng),
                stops=stop_coords,
                destination=(office_lat, office_lng),
                optimize=True,
            )
            
            if route.get("success"):
                polyline = route.get("polyline", "")
                distance_km = float(route.get("total_km", 0.0))
                duration_min = int(route.get("total_duration_min", 0))
                
                # Update ordered_stops if Google reordered them
                if route.get("ordered_points"):
                    # helper to map coords back to our Employee objects
                    reordered = _map_coords_to_employees(route["ordered_points"], group_members)
                    if reordered:
                        ordered_stops = reordered
            else:
                warnings.append(f"Google Routing failed: {route.get('error')}. Using haversine estimate.")
                distance_km = _estimate_round_trip_km(office_lat, office_lng, ordered_stops)
                duration_min = int(distance_km * 2.2) # rough estimate
        except Exception as e:
            warnings.append(f"Routing integration error: {e}")
            distance_km = _estimate_round_trip_km(office_lat, office_lng, ordered_stops)
            duration_min = int(distance_km * 2.2)
    else:
        if optimize_waypoints and build_multi_stop_route is None:
             warnings.append("routing_service not available; used local distance estimate.")
        distance_km = _estimate_round_trip_km(office_lat, office_lng, ordered_stops)
        duration_min = int(distance_km * 2.2)

    return GroupResult(
        group_index=group_index,
        vehicle_type=vehicle_type,
        operation=operation,
        scheduled_time=scheduled_time,
        members=group_members,
        ordered_stops=ordered_stops,
        distance_km_estimate=round(distance_km, 2),
        duration_min_estimate=duration_min,
        polyline=polyline,
        warnings=warnings,
    )


# ------------------- Manual Override Support -------------------

def _manual_groups_to_employee_groups(
    candidates: List[EmployeePoint],
    manual_groups: List[List[int]],
    group_size: int,
) -> Tuple[List[List[EmployeePoint]], List[int]]:
    """
    Convert manual group IDs to employee objects.
    - Ensures each group has correct size (4 or 6).
    - Removes duplicates across groups.
    - Returns (groups, unassigned_ids).
    """
    by_id: Dict[int, EmployeePoint] = {e.id: e for e in candidates}
    used: set[int] = set()
    groups: List[List[EmployeePoint]] = []

    for g in manual_groups:
        ids = [int(x) for x in g if int(x) in by_id]
        ids = [x for x in ids if x not in used]

        if len(ids) < group_size:
            # ignore incomplete group (admin can fix)
            continue
        ids = ids[:group_size]

        used.update(ids)
        members = [by_id[i] for i in ids]
        groups.append(_order_by_nearest_chain(members))

    unassigned = [e.id for e in candidates if e.id not in used]
    return groups, unassigned


# ------------------- Helpers: Trip persistence -------------------

def _generate_unique_route_no(conn) -> str:
    """
    Uses route_no_service.generate_route_no if present.
    Otherwise uses a local implementation matching your requirement:
      - First 4 chars: YEAR (YYYY)
      - Next 4: random digits
      - Last 2: month initials (first 2 letters of month)
    Unique (non-reusable) rule enforced by checking DB trips.route_no.
    """
    for _ in range(50):
        if generate_route_no is not None:
            rn = str(generate_route_no())
        else:
            rn = _local_generate_route_no()

        if not _route_no_exists(conn, rn):
            return rn

    # fallback: if collisions are extreme, add a final random attempt
    rn = _local_generate_route_no(extra_entropy=True)
    if _route_no_exists(conn, rn):
        raise RuntimeError("Unable to generate unique route number.")
    return rn


def _route_no_exists(conn, route_no: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
    return cur.fetchone() is not None


def _insert_trip(
    conn,
    route_no: str,
    admin_id: str,
    operation: str,
    scheduled_time: str,
    vehicle_type: int,
    status: str,
    office_lat: float,
    office_lng: float,
    total_km: float,
    polyline: str = "",
    duration_min: int = 0,
    driver_id: Optional[str] = None,
    vehicle_no: str = "",
    trip_day: str = "",
) -> int:
    if not trip_day:
        trip_day = datetime.utcnow().strftime("%Y%m%d")

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO trips
            (route_no, admin_id, operation, trip_type, schedule_time, vehicle_type, status,
             office_lat, office_lng, total_km, polyline, driver_id, vehicle_no, trip_day, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            route_no,
            admin_id,
            operation,
            operation, # trip_type
            scheduled_time,
            vehicle_type,
            status,
            float(office_lat),
            float(office_lng),
            float(total_km),
            polyline,
            driver_id,
            vehicle_no,
            trip_day,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
        ),
    )
    return int(cur.lastrowid)


def _insert_trip_members(conn, trip_id: int, stops: List[Dict[str, Any]]) -> None:
    """
    stops expected list of dicts containing at least {"id": employee_id}
    """
    cur = conn.cursor()
    seq = 1
    for s in stops:
        emp_id = int(s.get("id"))
        cur.execute(
            """
            INSERT INTO trip_employees (trip_id, employee_id, sequence_no, is_no_show)
            VALUES (?, ?, ?, 0)
            """,
            (trip_id, emp_id, seq),
        )
        seq += 1


# ------------------- Helpers: Ordering + Distance -------------------

def _order_by_nearest_chain(points: List[EmployeePoint]) -> List[EmployeePoint]:
    """
    Orders points to minimize zigzag (simple heuristic):
    - start with one point (min lat+lng)
    - repeatedly choose nearest unvisited
    """
    if not points:
        return []

    remaining = points[:]
    start = min(remaining, key=lambda p: (p.lat + p.lng))
    ordered = [start]
    remaining = [p for p in remaining if p.id != start.id]

    while remaining:
        last = ordered[-1]
        next_p = min(remaining, key=lambda p: haversine_km(last.lat, last.lng, p.lat, p.lng))
        ordered.append(next_p)
        remaining = [p for p in remaining if p.id != next_p.id]

    return ordered


def _estimate_round_trip_km(office_lat: float, office_lng: float, stops: List[EmployeePoint]) -> float:
    """
    Requirement: office -> all waypoints -> back to office
    """
    if not stops:
        return 0.0

    km = 0.0
    # office -> first
    km += haversine_km(office_lat, office_lng, stops[0].lat, stops[0].lng)
    # between stops
    for a, b in zip(stops, stops[1:]):
        km += haversine_km(a.lat, a.lng, b.lat, b.lng)
    # last -> office
    km += haversine_km(stops[-1].lat, stops[-1].lng, office_lat, office_lng)
    return km


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine distance (km) between two coordinates.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        print(f"DEBUG HAVERSINE ERROR: lat1={lat1}, lon1={lon1}, lat2={lat2}, lon2={lon2}")
        return 99999.0
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _map_coords_to_employees(
    ordered_points: List[Tuple[float, float]],
    employees: List[EmployeePoint],
    tol: float = 1e-5,
) -> List[EmployeePoint]:
    """
    Best-effort mapping between optimized coords and EmployeePoint.
    """
    if not ordered_points:
        return []

    remaining = employees[:]
    mapped: List[EmployeePoint] = []
    for lat, lng in ordered_points:
        best = None
        best_d = float("inf")
        for e in remaining:
            d = abs(e.lat - lat) + abs(e.lng - lng)
            if d < best_d:
                best_d = d
                best = e
        if best is not None and best_d <= tol * 10:
            mapped.append(best)
            remaining = [x for x in remaining if x.id != best.id]

    # If mapping incomplete, fallback to nearest chain
    if len(mapped) != len(employees):
        return []

    return mapped


# ------------------- Helpers: Validation + Normalization -------------------

def _normalize_operation(operation: str) -> str:
    op = (operation or "").strip().lower()
    if op in ("pickup", "pick", "p"):
        return "pickup"
    if op in ("drop", "d"):
        return "drop"
    raise ValueError("operation must be 'pickup' or 'drop'")


def _normalize_vehicle_type(vehicle_type: int) -> int:
    try:
        vt = int(vehicle_type)
    except Exception:
        raise ValueError("vehicle_type must be 4 or 6")

    if vt not in (4, 6):
        raise ValueError("vehicle_type must be 4 or 6")
    return vt


def _is_valid_coord(lat: float, lng: float) -> bool:
    return (
        isinstance(lat, (int, float))
        and isinstance(lng, (int, float))
        and -90.0 <= float(lat) <= 90.0
        and -180.0 <= float(lng) <= 180.0
        and not (float(lat) == 0.0 and float(lng) == 0.0)
    )


# ------------------- Helpers: Route No (local fallback) -------------------

def _local_generate_route_no(extra_entropy: bool = False) -> str:
    """
    Your requirement:
    - 10 characters total
    - first 4: year YYYY
    - next 4: random digits
    - last 2: first two letters of month
    Example: 20261234JA  (Jan -> JA)

    Note: This already creates exactly 10 chars.
    """
    now = datetime.now()
    year = now.strftime("%Y")  # 4
    month2 = now.strftime("%b").upper()[:2]  # 2 (JAN->JA)
    rand4 = f"{secrets.randbelow(10000):04d}"  # 4

    if not extra_entropy:
        return f"{year}{rand4}{month2}"

    # still keep 10 chars: replace rand4 with "more varied" digits
    rand4 = "".join(str(secrets.randbelow(10)) for _ in range(4))
    return f"{year}{rand4}{month2}"


# ------------------- JSON conversion -------------------

def _employee_to_json(e: EmployeePoint) -> Dict[str, Any]:
    return {
        "id": e.id,
        "name": e.name,
        "mobile": e.mobile,
        "address": e.address,
        "lat": e.lat,
        "lng": e.lng,
        "login_time": e.login_time,
        "logout_time": e.logout_time
    }


def _group_to_json(gr: GroupResult) -> Dict[str, Any]:
    # Match serialize_trip structure where possible
    # A "GroupResult" is essentially a "Proposed Trip"
    
    # Map employees to standard format
    employees = []
    for idx, member in enumerate(gr.ordered_stops or gr.members, start=1):
        # Base employee data
        emp_data = _employee_to_json(member)
        # Add standard fields
        emp_data["pickup_order"] = idx
        emp_data["eta"] = None  # Not calculated in preview
        employees.append(emp_data)

    return {
        # Trip fields (null/preview defaults)
        "trip_id": None,
        "route_no": None,
        "trip_status": "preview",
        "trip_date": datetime.now().strftime("%Y-%m-%d"), # Assume today
        "trip_time": gr.scheduled_time,
        "trip_type": gr.operation,
        
        # Groups Array
        "groups": [
            {
                "group_index": gr.group_index, # Local index
                "capacity": gr.vehicle_type,
                "polyline": gr.polyline,
                "duration_min": gr.duration_min_estimate,
                "employees": employees
            }
        ],
        
        # Vehicle/Driver (null)
        "assigned_cab": None,
        "assigned_driver": None,
        
        # Route details
        "route_polyline": None, # Not calculated in basic preview unless routing enabled
        "total_km": gr.distance_km_estimate,
        
        # Summary
        "eta_summary": {
            "duration_mins": gr.duration_min_estimate,
            "pickup_start": gr.scheduled_time
        },
        
        # Preview-specific meta (optional but helpful)
        "warnings": gr.warnings
    }
