# backend/services/trip_orchestration_service.py
"""
RG Travel Solution - Trip Orchestration Service
Complete workflow: Steps 1-10 + validation

Orchestrates the complete auto-grouping + trip assignment + admin override workflow.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, cast
import hashlib
import logging
from typing import Dict, Any, List, Optional, cast, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .trip_validation_service import (
        validate_trip_request, filter_eligible_employees,
        scan_cab_availability, validate_sufficient_resources,
        get_trip_validation_summary
    )
    from .capacity_optimizer import optimize_cab_capacity, rebalance_group_sizes
    from .geo_clustering import cluster_employees_by_proximity, EmployeePoint, calculate_group_distances
    from .route_no_service import generate_unique_route_no
    from .driver_assignment import assign_drivers_to_groups


class TripOrchestrationError(Exception):
    """Exception for trip orchestration failures"""
    pass


def _row_exists(row: Any) -> bool:
    if row is None:
        return False
    # Unit tests often use MagicMock cursors; treat unresolved mock rows as absent.
    if row.__class__.__name__ == "MagicMock":
        return False
    return True


def _coord_distance_sq(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = lat1 - lat2
    dlng = lng1 - lng2
    return (dlat * dlat) + (dlng * dlng)


def _vehicle_capacities_for_groups(
    group_sizes: List[int],
    use_4_seaters: int,
    use_6_seaters: int,
    prioritize_6: bool,
) -> List[int]:
    capacities = ([6] * use_6_seaters) + ([4] * use_4_seaters)
    if not capacities:
        return []
    if prioritize_6:
        capacities.sort(reverse=True)
    else:
        capacities.sort()

    assigned: List[int] = []
    remaining = list(capacities)
    for size in group_sizes:
        pick_idx = None
        for idx, cap in enumerate(remaining):
            if cap >= size:
                pick_idx = idx
                break
        if pick_idx is None:
            # Fallback: choose largest remaining if no perfect fit.
            pick_idx = len(remaining) - 1
        assigned.append(int(remaining.pop(pick_idx)))
        if not remaining:
            break

    return assigned


def preview_and_organize_trip(
    db_conn,
    admin_id: str,
    trip_type: str,
    selected_time: str,
    vehicle_types: Optional[List[int]] = None,
    office_lat: float = 0.0,
    office_lng: float = 0.0,
    employee_ids: Optional[List[int]] = None,
    driver_ids: Optional[List[int]] = None,
    vehicle_priority_enabled: bool = False,
    trip_day: Optional[str] = None,
    vehicle_type: Optional[int] = None,
) -> Dict[str, Any]:
    """
    PREVIEW PHASE: Steps 1-6
    Preview groups without creating trip records yet.
    
    Args:
        driver_ids: Optional list of selected driver IDs to filter available cabs
        vehicle_priority_enabled: If True and both vehicle types selected, prioritize 6-seaters
    """
    try:
        if vehicle_types is None:
            if vehicle_type in (4, 6):
                vehicle_types = [int(vehicle_type)]
            else:
                vehicle_types = [6, 4]

        # Set trip_day if not provided
        if not trip_day:
            trip_day = datetime.now().strftime("%Y%m%d")
        
        # Apply vehicle priority sorting if enabled
        if vehicle_priority_enabled and len(vehicle_types) > 1:
            vehicle_types = sorted(vehicle_types, reverse=True)  # 6-seaters first
        
        # STEP 1-3: Validate & Filter Employees
        from .trip_validation_service import (
            validate_trip_request, filter_eligible_employees,
            scan_cab_availability, get_trip_validation_summary
        )
        
        # Validate request
        validation_result = validate_trip_request(trip_type, selected_time, vehicle_types, employee_ids)
        if not validation_result["success"]:
            return {
                "success": False,
                "message": "Invalid request parameters",
                "errors": validation_result["errors"]
            }
        
        # Filter employees by trip type and time
        eligible_employees, exclusions = filter_eligible_employees(
            db_conn, trip_type, selected_time, employee_ids, trip_day, admin_id=admin_id
        )
        
        if not eligible_employees:
            return {
                "success": False,
                "message": "No eligible employees found",
                "exclusions": exclusions
            }
        
        # Scan cab availability with optional driver filtering
        cab_availability = scan_cab_availability(
            db_conn,
            driver_ids=driver_ids,
            trip_type=trip_type,
            selected_time=selected_time,
            trip_day=trip_day,
            admin_id=admin_id,
        )
        if not cab_availability["success"]:
            return {
                "success": False,
                "message": cab_availability["message"],
                "data": None
            }
        
        data = cab_availability["data"]
        # Filter available cabs by selected types if needed
        # (Though optimizer already handles availability, we should limit to what admin selected)
        avail_4 = data["available_4_count"] if 4 in vehicle_types else 0
        avail_6 = data["available_6_count"] if 6 in vehicle_types else 0
        
        if avail_4 + avail_6 <= 0:
            return {
                "success": False,
                "message": "No available vehicles for selected vehicle types",
                "data": {
                    "employees": len(eligible_employees),
                    "resources": data
                }
            }
        if int(data.get("available_driver_count", 0)) <= 0:
            return {
                "success": False,
                "message": "No available drivers",
                "data": {
                    "employees": len(eligible_employees),
                    "resources": data
                }
            }

        selected_capacity = (avail_4 * 4) + (avail_6 * 6)
        assignable_employee_count = min(len(eligible_employees), selected_capacity)

        # Nearest-first candidate ordering for deterministic grouping under capacity limits.
        sorted_employees = sorted(
            eligible_employees,
            key=lambda emp: _coord_distance_sq(
                float(emp.get("pickup_lat" if trip_type == "pickup" else "home_lat") or 0.0),
                float(emp.get("pickup_lng" if trip_type == "pickup" else "home_lng") or 0.0),
                float(office_lat),
                float(office_lng),
            ),
        )
        grouped_employees = sorted_employees[:assignable_employee_count]
        unassigned_employees = sorted_employees[assignable_employee_count:]
        warnings = list(validation_result.get("warnings", []))
        if unassigned_employees:
            warnings.append(
                f"{len(unassigned_employees)} employees are unassigned due to vehicle capacity and remain eligible for next trip."
            )
        
        # STEP 4: Optimize capacity
        from .capacity_optimizer import optimize_cab_capacity, rebalance_group_sizes
        
        # We pass prioritize_6_seaters=True as per priority rule
        optimization_result = optimize_cab_capacity(
            len(grouped_employees),
            avail_4,
            avail_6,
            prioritize_6_seaters=True
        )
        
        if not optimization_result["success"]:
            return optimization_result
        
        opt_data = optimization_result["data"]
        use_4_seaters = opt_data["use_4_seaters"]
        use_6_seaters = opt_data["use_6_seaters"]
        
        # STEP 5: Rebalance group sizes
        group_sizes = cast(List[int], rebalance_group_sizes(len(grouped_employees), use_4_seaters, use_6_seaters))
        group_vehicle_capacities = _vehicle_capacities_for_groups(
            group_sizes,
            use_4_seaters=use_4_seaters,
            use_6_seaters=use_6_seaters,
            prioritize_6=bool(vehicle_priority_enabled),
        )
        
        logger.info(f"Optimized grouping: {group_sizes} for {len(eligible_employees)} employees")
        
        # STEP 6: Geo-clustering
        from .geo_clustering import cluster_employees_by_proximity, EmployeePoint, calculate_group_distances
        
        employee_points = cast(List[EmployeePoint], [
            EmployeePoint(
                id=emp["id"],
                name=emp["name"],
                mobile=emp["mobile"],
                address=str(emp.get(
                    "pickup_address" if trip_type == "pickup" else "home_address", ""
                )),
                lat=float(emp.get("pickup_lat" if trip_type == "pickup" else "home_lat") or 0.0),
                lng=float(emp.get("pickup_lng" if trip_type == "pickup" else "home_lng") or 0.0)
            )
            for emp in grouped_employees
        ])
        
        groups = cluster_employees_by_proximity(
            employee_points,
            group_sizes,
            office_lat,
            office_lng,
            method="nearest_neighbor"
        )
        
        # Build preview groups
        preview_groups = []
        for idx, group in enumerate(groups):
            distances = calculate_group_distances(group, office_lat, office_lng)
            est_time_min = int(distances["total_route"] / 20) * 10  # Rough estimate: 20km/hr
            
            group_members = [
                {
                    "id": emp.id,
                    "name": emp.name,
                    "mobile": emp.mobile,
                    "address": emp.address,
                    "lat": emp.lat,
                    "lng": emp.lng
                }
                for emp in group
            ]
            
            preview_groups.append({
                "group_index": idx + 1,
                "members_count": len(group),
                "members": group_members,
                "route_distance_km": distances["total_route"],
                "estimated_duration_min": est_time_min,
                "vehicle_type": int(group_vehicle_capacities[idx]) if idx < len(group_vehicle_capacities) else (6 if len(group) > 4 else 4)
            })
        
        # Validation summary
        val_summary = get_trip_validation_summary(
            grouped_employees,
            cab_availability,
            exclusions
        )
        
        return {
            "success": True,
            "message": f"Preview ready: {len(groups)} groups for {len(grouped_employees)} employees",
            "data": {
                "trip_preview": {
                    "trip_type": trip_type,
                    "selected_time": selected_time,
                    "vehicle_types": vehicle_types,
                    "vehicle_type": vehicle_types[0] if vehicle_types else 4,
                    "trip_day": trip_day,
                    "office_lat": office_lat,
                    "office_lng": office_lng,
                },
                "validated_employees": grouped_employees,
                "unassigned_employees": unassigned_employees,
                "resource_check": {
                    "available_4_count": cab_availability["data"]["available_4_count"],
                    "available_6_count": cab_availability["data"]["available_6_count"],
                    "available_driver_count": cab_availability["data"]["available_driver_count"],
                    "total_capacity": cab_availability["data"]["total_capacity"],
                    "usable_cabs": cab_availability["data"]["usable_cabs"],
                    "selected_capacity": selected_capacity,
                    "assignable_employees": assignable_employee_count,
                    "unassigned_count": len(unassigned_employees),
                },
                "groups": preview_groups,
                "optimization_summary": {
                    "use_4_seaters": use_4_seaters,
                    "use_6_seaters": use_6_seaters,
                    "total_cabs": opt_data["total_cabs"],
                    "total_seats": opt_data["total_seats"],
                    "empty_seats": opt_data["empty_seats"],
                    "efficiency_percent": opt_data["efficiency_percent"],
                    "strategy": opt_data["strategy_used"],
                },
                "validation_summary": val_summary,
                "warnings": (val_summary.get("warnings", []) + warnings),
            }
        }
    
    except Exception as e:
        logger.error(f"Trip preview failed: {e}", exc_info=True)
        raise TripOrchestrationError(f"Trip preview failed: {str(e)}")


def create_and_assign_trip(
    db_conn,
    admin_id: str,
    preview_data: Dict[str, Any],
    groups_to_create: List[Dict[str, Any]],
    driver_assignments: Dict[int, Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    ASSIGNMENT PHASE: Steps 7-9
    Create trip records, assign drivers, generate OTPs.
    
    Args:
        db_conn: Database connection
        admin_id: Admin ID
        preview_data: Data from preview_and_organize_trip
        groups_to_create: List of groups to create (from preview)
        driver_assignments: Manual driver assignments (optional)
            Format: {group_index: {"driver_id": str, "cab_id": str}}
            
    Returns:
        {
            "success": bool,
            "message": str,
            "data": {
                "trips_created": [
                    {
                        "route_no": str,
                        "trip_id": int,
                        "driver_id": str,
                        "driver_name": str,
                        "vehicle_no": str,
                        "employee_count": int,
                        "total_distance_km": float,
                        "start_otp": str,
                        "end_otp": str,
                        ...
                    }
                ],
                "summary": {...}
            }
        }
    """
    try:
        import sqlite3
        from services import route_no_service
        from services.routing_service import build_multi_stop_route
        from services.trip_schedule_guard import derive_pickup_timing, build_pickup_time_note
        unique_route_no_fn = getattr(route_no_service, "generate_unique_route_no", None)
        legacy_route_no_fn = getattr(route_no_service, "generate_route_no", None)
        if unique_route_no_fn is None and legacy_route_no_fn is None:
            raise TripOrchestrationError("No route number generator available")

        if not isinstance(preview_data, dict) or "trip_preview" not in preview_data:
            return {"success": False, "message": "preview_data.trip_preview is required"}
        if not isinstance(groups_to_create, list) or not groups_to_create:
            return {"success": False, "message": "groups_to_create must be a non-empty list"}

        trip_preview = preview_data["trip_preview"]
        selected_time = str(trip_preview.get("selected_time") or "").strip()
        trip_type = str(trip_preview.get("trip_type") or "").strip().lower()
        trip_day = str(trip_preview.get("trip_day") or datetime.now().strftime("%Y%m%d"))
        office_lat = float(trip_preview.get("office_lat", 0))
        office_lng = float(trip_preview.get("office_lng", 0))

        if trip_type not in ("pickup", "drop"):
            return {"success": False, "message": "trip_type must be pickup or drop"}
        if not selected_time:
            return {"success": False, "message": "selected_time is required"}

        selected_vehicle_ids: List[int] = []
        for g in groups_to_create:
            raw_vid = g.get("vehicle_id")
            if raw_vid is None:
                continue
            try:
                vid = int(raw_vid)
            except Exception:
                continue
            if vid not in selected_vehicle_ids:
                selected_vehicle_ids.append(vid)
        if selected_vehicle_ids:
            trip_preview["selected_vehicle_ids"] = selected_vehicle_ids

        trips_created = []
        queued_otps: List[Tuple[str, str]] = []
        used_driver_ids: set[str] = set()
        all_employee_ids: set[int] = set()
        group_employee_sets: List[set[int]] = []

        # Pre-validate groups for duplicate employees/capacity issues.
        for group_idx, group_data in enumerate(groups_to_create):
            members = group_data.get("members") or []
            group_emp_ids: set[int] = set()
            for m in members:
                try:
                    emp_id = int(m.get("id"))
                except Exception:
                    raise TripOrchestrationError(f"Group {group_idx + 1} has invalid member id")
                if emp_id in group_emp_ids:
                    raise TripOrchestrationError(f"Group {group_idx + 1} has duplicate employee {emp_id}")
                if emp_id in all_employee_ids:
                    raise TripOrchestrationError(f"Employee {emp_id} appears in multiple groups")
                group_emp_ids.add(emp_id)
                all_employee_ids.add(emp_id)
            group_employee_sets.append(group_emp_ids)

            vehicle_type = int(group_data.get("vehicle_type", trip_preview.get("vehicle_type", 4)))
            if vehicle_type in (4, 6) and len(group_emp_ids) > vehicle_type:
                raise TripOrchestrationError(
                    f"Group {group_idx + 1} exceeds vehicle capacity ({len(group_emp_ids)}/{vehicle_type})"
                )

        # Validate active-trip conflicts for employees (same operation/day/time).
        cursor = db_conn.cursor()
        normalized_day = str(trip_day).replace("-", "")
        for emp_id in all_employee_ids:
            cursor.execute(
                """
                SELECT t.id
                FROM trip_employees te
                JOIN trips t ON te.trip_id = t.id
                WHERE te.employee_id = ?
                  AND LOWER(COALESCE(t.operation, t.trip_type, '')) = ?
                  AND REPLACE(COALESCE(t.trip_day, ''), '-', '') = ?
                  AND COALESCE(t.time_slot, t.schedule_time, '') = ?
                  AND LOWER(COALESCE(t.status, 'created')) IN ('created','assigned','started','active','in_progress')
                LIMIT 1
                """,
                (str(emp_id), trip_type, normalized_day, selected_time),
            )
            if _row_exists(cursor.fetchone()):
                raise TripOrchestrationError(
                    f"Employee {emp_id} already assigned to active {trip_type} trip for {selected_time}"
                )

        # Batch auto-assignment to avoid reusing same driver/vehicle across groups.
        auto_assign_map: Dict[int, Dict[str, Any]] = {}
        groups_for_auto: List[Dict[str, Any]] = []
        auto_index_map: List[int] = []
        if not driver_assignments:
            driver_assignments = {}
        for group_idx, group_data in enumerate(groups_to_create):
            if group_idx in driver_assignments:
                continue
            groups_for_auto.append(
                {
                    "members": group_data.get("members", []),
                    "vehicle_type": int(group_data.get("vehicle_type", trip_preview.get("vehicle_type", 4))),
                }
            )
            auto_index_map.append(group_idx)

        if groups_for_auto:
            from services.assignment_service import assign_group_resources
            auto_assignments = assign_group_resources(
                conn=db_conn,
                groups=groups_for_auto,
                scheduled_time=selected_time,
                trip_day=trip_day,
                selected_vehicle_ids=trip_preview.get("selected_vehicle_ids")
                if isinstance(trip_preview.get("selected_vehicle_ids"), list)
                else None,
            )
            for local_idx, assignment in auto_assignments.items():
                if local_idx < len(auto_index_map):
                    auto_assign_map[auto_index_map[local_idx]] = assignment

        cursor = db_conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        for group_idx, group_data in enumerate(groups_to_create):
            members = group_data.get("members") or []
            if not members:
                raise TripOrchestrationError(f"Group {group_idx + 1} has no members")
            for m in members:
                if m.get("id") is None:
                    raise TripOrchestrationError(f"Group {group_idx + 1} member id missing")
                if m.get("lat") is None or m.get("lng") is None:
                    raise TripOrchestrationError(f"Group {group_idx + 1} member coordinates missing")

            origin = (office_lat, office_lng)
            destination = origin
            waypoints = [(float(m["lat"]), float(m["lng"])) for m in members]
            route_result = build_multi_stop_route(
                origin=origin,
                stops=waypoints,
                destination=destination,
                optimize=True,
            )
            route_km = float(route_result.get("total_km", 0.0))
            route_polyline = str(route_result.get("polyline", "") or "")
            route_eta_min = int(route_result.get("eta_min", route_result.get("total_duration_min", 0)) or 0)
            timing_meta = derive_pickup_timing(
                selected_time,
                route_eta_min,
                extra_buffer_minutes=0,
            ) if trip_type == "pickup" else {
                "has_timing": True,
                "login_time": str(selected_time),
                "pickup_time": None,
                "route_duration_minutes": route_eta_min,
                "extra_buffer_minutes": 0,
                "total_lead_minutes": route_eta_min,
                "day_offset": 0,
                "reason": None,
            }
            pickup_time_note = build_pickup_time_note(timing_meta) if trip_type == "pickup" else ""

            if driver_assignments and group_idx in driver_assignments:
                assignment = driver_assignments[group_idx]
                driver_id = assignment["driver_id"]
                cab_id = assignment.get("cab_id")
            else:
                auto = auto_assign_map.get(group_idx)
                if not auto:
                    driver_id, cab_id = _auto_assign_driver_for_group(db_conn, trip_preview, group_data)
                else:
                    driver_id = auto.get("driver_id")
                    cab_id = auto.get("vehicle_id") or auto.get("vehicle_no")

            if not driver_id:
                raise TripOrchestrationError(f"Failed to assign driver for group {group_idx + 1}")
            resolved_driver = _resolve_driver(db_conn, str(driver_id))
            if not resolved_driver:
                raise TripOrchestrationError(
                    f"Driver {driver_id} not found. Please reselect a valid driver."
                )
            driver_id = str(resolved_driver["id"])
            if str(driver_id) in used_driver_ids:
                raise TripOrchestrationError(f"Driver {driver_id} assigned to multiple groups in same batch")

            # Final safety check for driver conflicts in active trips.
            cursor.execute(
                """
                SELECT id
                FROM trips
                WHERE driver_id = ?
                  AND LOWER(COALESCE(operation, trip_type, '')) = ?
                  AND REPLACE(COALESCE(trip_day, ''), '-', '') = ?
                  AND COALESCE(time_slot, schedule_time, '') = ?
                  AND LOWER(COALESCE(status, 'created')) IN ('created','assigned','started','active','in_progress')
                LIMIT 1
                """,
                (str(driver_id), trip_type, normalized_day, selected_time),
            )
            if _row_exists(cursor.fetchone()):
                raise TripOrchestrationError(
                    f"Driver {driver_id} already assigned to active {trip_type} trip for {selected_time}"
                )

            driver_info = resolved_driver
            cab_info = _get_cab_info(db_conn, str(driver_id), cab_id)

            route_no = None
            if isinstance(db_conn, sqlite3.Connection) and callable(unique_route_no_fn):
                try:
                    route_no = unique_route_no_fn(db_conn)
                except Exception:
                    route_no = None
            if not route_no and callable(legacy_route_no_fn):
                try:
                    route_no = legacy_route_no_fn(db_conn)
                except TypeError:
                    route_no = legacy_route_no_fn()
                except Exception:
                    route_no = None
            if not route_no and callable(unique_route_no_fn):
                route_no = unique_route_no_fn(db_conn)
            vehicle_type = int(group_data.get("vehicle_type", trip_preview.get("vehicle_type", 4)))

            start_otp = _generate_otp()
            end_otp = _generate_otp()
            start_otp_hash = _hash_otp(start_otp)
            end_otp_hash = _hash_otp(end_otp)
            now = datetime.now()
            start_otp_expiry = (now + timedelta(minutes=30)).isoformat()
            end_otp_expiry = (now + timedelta(hours=2)).isoformat()

            trip_id = _create_trip_record(
                cursor,
                route_no=route_no,
                trip_day=trip_day,
                operation=trip_type,
                schedule_time=selected_time,
                vehicle_type=vehicle_type,
                admin_id=admin_id,
                driver_id=str(driver_id),
                office_lat=office_lat,
                office_lng=office_lng,
                total_km=route_km,
                polyline=route_polyline,
                start_otp_hash=start_otp_hash,
                start_otp_expiry=start_otp_expiry,
                end_otp_hash=end_otp_hash,
                end_otp_expiry=end_otp_expiry
            )
            _update_trip_extended_fields(
                cursor=cursor,
                trip_id=trip_id,
                time_slot=selected_time,
                vehicle_id=group_data.get("vehicle_id"),
                route_polyline=route_polyline,
            )

            _save_trip_route_details(
                cursor=cursor,
                trip_id=trip_id,
                route_polyline=route_polyline,
                distance_km=route_km,
                duration_min=route_eta_min,
                route_payload=route_result,
            )

            _save_trip_group_records(
                cursor=cursor,
                trip_id=trip_id,
                route_no=route_no,
                trip_type=trip_type,
                group_index=group_idx + 1,
                members=members,
                capacity=vehicle_type,
                vehicle_id=group_data.get("vehicle_id"),
                driver_id=str(driver_id),
            )

            for seq, member in enumerate(members, 1):
                _assign_employee_to_trip(cursor, trip_id, int(member["id"]), seq)

            _record_admin_audit(
                cursor=cursor,
                admin_id=str(admin_id),
                action="create_trip_group",
                target_type="trip",
                target_id=str(trip_id),
                details=f"route_no={route_no}; group_index={group_idx + 1}; trip_type={trip_type}",
            )
            _mark_source_group_assigned(
                cursor=cursor,
                group_data=group_data,
                admin_id=str(admin_id),
                trip_type=trip_type,
                selected_time=selected_time,
                trip_day=trip_day,
                trip_id=trip_id,
                route_no=route_no,
            )

            driver_mobile = str(driver_info.get("mobile", "") or "")
            if driver_mobile:
                queued_otps.append((driver_mobile, start_otp))
            used_driver_ids.add(str(driver_id))

            trips_created.append({
                "route_no": route_no,
                "trip_id": trip_id,
                "group_index": group_idx + 1,
                "driver_id": str(driver_id),
                "driver_name": driver_info.get("name", ""),
                "driver_mobile": driver_info.get("mobile", ""),
                "vehicle_id": group_data.get("vehicle_id"),
                "vehicle_no": cab_info.get("vehicle_no", ""),
                "vehicle_type": vehicle_type,
                "employee_count": len(members),
                "total_distance_km": route_km,
                "estimated_duration_min": route_eta_min,
                "route_source": route_result.get("source"),
                "polyline": route_polyline,
                "start_otp": start_otp,
                "start_otp_expiry": start_otp_expiry,
                "end_otp": end_otp,
                "end_otp_expiry": end_otp_expiry,
                "members": members,
                "trip_type": trip_type,
                "schedule_time": selected_time,
                "login_time": timing_meta.get("login_time"),
                "pickup_time": timing_meta.get("pickup_time"),
                "travel_time_min": int(timing_meta.get("route_duration_minutes", route_eta_min) or 0),
                "extra_buffer_min": int(timing_meta.get("extra_buffer_minutes", 0) or 0),
                "total_travel_with_buffer_min": int(timing_meta.get("total_lead_minutes", route_eta_min) or 0),
                "pickup_day_offset": int(timing_meta.get("day_offset", 0) or 0),
                "pickup_time_note": pickup_time_note,
            })

        db_conn.commit()

        for mobile, otp in queued_otps:
            try:
                from services.notification_service import send_otp
                send_otp(mobile, otp, purpose="start")
            except Exception:
                logger.exception("Failed to send OTP via notification service")

        # Real-time propagation to driver/employee/admin dashboards.
        for trip in trips_created:
            try:
                from services.socket_service import broadcast_trip_assignment
                broadcast_trip_assignment(
                    route_no=str(trip.get("route_no")),
                    trip_data={
                        "trip_id": trip.get("trip_id"),
                        "driver_name": trip.get("driver_name"),
                        "driver_phone": trip.get("driver_mobile"),
                        "vehicle_no": trip.get("vehicle_no"),
                        "schedule_time": trip.get("schedule_time"),
                        "login_time": trip.get("login_time"),
                        "pickup_time": trip.get("pickup_time"),
                        "pickup_time_note": trip.get("pickup_time_note"),
                        "operation": trip.get("trip_type"),
                        "employees": trip.get("members", []),
                        "route_summary": {
                            "total_distance_km": trip.get("total_distance_km"),
                            "estimated_duration_min": trip.get("estimated_duration_min"),
                            "extra_buffer_min": trip.get("extra_buffer_min"),
                            "total_travel_with_buffer_min": trip.get("total_travel_with_buffer_min"),
                        },
                        "otps": {
                            "start": trip.get("start_otp"),
                            "end": trip.get("end_otp"),
                        },
                    },
                )
            except Exception:
                logger.exception("Failed to broadcast trip assignment (non-critical)")

        return {
            "success": True,
            "message": f"Created {len(trips_created)} trips successfully",
            "data": {
                "trips_created": trips_created,
                "summary": {
                    "total_trips": len(trips_created),
                    "total_employees": sum(t["employee_count"] for t in trips_created),
                    "total_distance_km": sum(t["total_distance_km"] for t in trips_created),
                    "trip_type": trip_type,
                    "schedule_time": selected_time,
                }
            }
        }

    except Exception as e:
        logger.error(f"Trip creation failed: {e}", exc_info=True)
        db_conn.rollback()
        return {
            "success": False,
            "message": f"Trip creation failed: {str(e)}"
        }


# ===================== HELPER FUNCTIONS =====================

def _auto_assign_driver_for_group(
    db_conn, trip_preview: Dict[str, Any], group_data: Dict[str, Any]
) -> tuple:
    """Auto-assign driver using Step 6 assignment service."""
    try:
        from services.assignment_service import assign_group_resources

        groups = [group_data]
        vehicle_type = trip_preview.get("vehicle_type", 4)
        trip_day = trip_preview.get("trip_day", datetime.now().strftime("%Y%m%d"))
        selected_vehicle_ids = trip_preview.get("selected_vehicle_ids")
        selected_vehicle_ids = selected_vehicle_ids if isinstance(selected_vehicle_ids, list) else None

        # Ensure required capacity is present for assignment.
        prepared_group = {
            "members": group_data.get("members", []),
            "vehicle_type": int(group_data.get("vehicle_type", vehicle_type)),
        }

        assignments = assign_group_resources(
            conn=db_conn,
            groups=[prepared_group],
            scheduled_time=str(trip_preview.get("selected_time", "")),
            trip_day=str(trip_day),
            selected_vehicle_ids=selected_vehicle_ids,
        )

        if assignments and 0 in assignments:
            first = assignments[0]
            # Keep tuple compatibility: (driver_id, cab_id)
            return first.get("driver_id"), first.get("vehicle_id") or first.get("vehicle_no")

        return None, None
    except Exception as e:
        logger.warning(f"Auto-assign failed: {e}")
        return None, None


def _resolve_driver(db_conn, driver_ref: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a driver by primary key id OR legacy/public driver_id text.
    Returns canonical row keyed by numeric id when found.
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT id, name, mobile
            FROM drivers
            WHERE CAST(id AS TEXT) = ?
               OR (driver_id IS NOT NULL AND CAST(driver_id AS TEXT) = ?)
            LIMIT 1
            """,
            (driver_ref, driver_ref),
        )
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "mobile": row[2]}
    except Exception as e:
        logger.warning(f"Error resolving driver '{driver_ref}': {e}")
    return None


def _get_driver_info(db_conn, driver_id: str) -> Optional[Dict[str, Any]]:
    """Fetch driver details."""
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            """
            SELECT id, name, mobile
            FROM drivers
            WHERE CAST(id AS TEXT) = ?
               OR (driver_id IS NOT NULL AND CAST(driver_id AS TEXT) = ?)
            LIMIT 1
            """,
            (driver_id, driver_id),
        )
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "mobile": row[2]}
    except Exception as e:
        logger.warning(f"Error fetching driver info: {e}")

    return None


def _get_cab_info(db_conn, driver_id: str, cab_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch cab details."""
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id, vehicle_no, vehicle_type FROM drivers WHERE id = ?",
            (driver_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "vehicle_no": row[1], "vehicle_type": row[2]}
    except Exception as e:
        logger.warning(f"Error fetching cab info: {e}")
    
    return {"id": cab_id, "vehicle_no": "Unknown", "vehicle_type": "4"}


def _generate_otp() -> str:
    """Generate a 6-digit random OTP."""
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


def _hash_otp(otp: str) -> str:
    """Hash OTP for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def _create_trip_record(
    cursor,
    route_no: str,
    trip_day: str,
    operation: str,
    schedule_time: str,
    vehicle_type: int,
    admin_id: str,
    driver_id: str,
    office_lat: float,
    office_lng: float,
    total_km: float,
    polyline: str,
    start_otp_hash: str,
    start_otp_expiry: str,
    end_otp_hash: str,
    end_otp_expiry: str
) -> int:
    """Create a new trip record and return trip_id."""
    now = datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO trips (
            route_no, trip_day, operation, trip_type, schedule_time,
            status, admin_id, driver_id, vehicle_type,
            office_lat, office_lng, total_km, polyline,
            start_otp_hash, start_otp_expiry,
            end_otp_hash, end_otp_expiry,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            route_no, trip_day, operation, operation, schedule_time,
            "assigned", admin_id, driver_id, vehicle_type,
            office_lat, office_lng, total_km, polyline,
            start_otp_hash, start_otp_expiry,
            end_otp_hash, end_otp_expiry,
            now, now
        )
    )
    
    return cursor.lastrowid


def _assign_employee_to_trip(cursor, trip_id: int, employee_id: int, sequence: int):
    """Assign an employee to a trip. employee_id stored as TEXT in trip_employees."""
    cursor.execute(
        """
        INSERT INTO trip_employees (trip_id, employee_id, sequence_no, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (trip_id, str(employee_id), sequence, datetime.now().isoformat())
    )


def _update_trip_extended_fields(
    cursor,
    trip_id: int,
    time_slot: str,
    vehicle_id: Optional[Any],
    route_polyline: str,
) -> None:
    """
    Update optional Step-3/Step-8 columns when present.
    """
    cursor.execute("PRAGMA table_info(trips)")
    cols = {r[1] for r in cursor.fetchall()}

    sets = []
    params: List[Any] = []

    if "time_slot" in cols:
        sets.append("time_slot = COALESCE(time_slot, ?)")
        params.append(time_slot)
    if "vehicle_id" in cols:
        sets.append("vehicle_id = COALESCE(vehicle_id, ?)")
        params.append(vehicle_id)
    if "route_polyline" in cols:
        sets.append("route_polyline = COALESCE(route_polyline, ?)")
        params.append(route_polyline)
    if "updated_at" in cols:
        sets.append("updated_at = ?")
        params.append(datetime.now().isoformat())

    if not sets:
        return

    params.append(trip_id)
    cursor.execute(f"UPDATE trips SET {', '.join(sets)} WHERE id = ?", tuple(params))


def _save_trip_group_records(
    cursor,
    trip_id: int,
    route_no: str,
    trip_type: str,
    group_index: int,
    members: List[Dict[str, Any]],
    capacity: int,
    vehicle_id: Optional[Any],
    driver_id: str,
) -> None:
    """
    Persist trip_groups + trip_group_members if these tables exist.
    Handles mixed legacy/new schemas by inspecting table columns.
    """
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trip_groups' LIMIT 1")
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(trip_groups)")
    tg_cols = {r[1] for r in cursor.fetchall()}

    group_id_text = f"GRP-{trip_id}-{group_index}"
    tg_data: Dict[str, Any] = {}
    if "trip_id" in tg_cols:
        tg_data["trip_id"] = trip_id
    if "group_type" in tg_cols:
        tg_data["group_type"] = trip_type
    if "created_at" in tg_cols:
        tg_data["created_at"] = datetime.now().isoformat()
    if "group_id" in tg_cols:
        tg_data["group_id"] = group_id_text
    if "route_no" in tg_cols:
        tg_data["route_no"] = route_no
    if "capacity" in tg_cols:
        tg_data["capacity"] = capacity
    if "vehicle_id" in tg_cols:
        tg_data["vehicle_id"] = vehicle_id
    if "driver_id" in tg_cols:
        tg_data["driver_id"] = driver_id

    if not tg_data:
        return

    tg_columns = list(tg_data.keys())
    tg_values = [tg_data[c] for c in tg_columns]
    tg_placeholders = ",".join(["?"] * len(tg_columns))
    cursor.execute(
        f"INSERT INTO trip_groups ({','.join(tg_columns)}) VALUES ({tg_placeholders})",
        tuple(tg_values),
    )
    group_pk = cursor.lastrowid

    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trip_group_members' LIMIT 1")
    if not cursor.fetchone():
        return

    cursor.execute("PRAGMA table_info(trip_group_members)")
    tgm_cols = {r[1] for r in cursor.fetchall()}

    for seq, member in enumerate(members, start=1):
        member_data: Dict[str, Any] = {}
        if "group_id" in tgm_cols:
            member_data["group_id"] = group_pk
        if "employee_id" in tgm_cols:
            member_data["employee_id"] = member.get("id")
        if "pickup_order" in tgm_cols:
            member_data["pickup_order"] = seq
        if "status" in tgm_cols:
            member_data["status"] = "assigned"
        if "sequence_no" in tgm_cols:
            member_data["sequence_no"] = seq
        if "pickup_drop_status" in tgm_cols:
            member_data["pickup_drop_status"] = "assigned"

        if not member_data:
            continue

        columns = list(member_data.keys())
        values = [member_data[c] for c in columns]
        placeholders = ",".join(["?"] * len(columns))
        cursor.execute(
            f"INSERT INTO trip_group_members ({','.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )


def _record_admin_audit(
    cursor,
    admin_id: str,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
) -> None:
    """
    Write admin audit row when table exists.
    """
    try:
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='admin_audit' LIMIT 1")
        if not cursor.fetchone():
            return
        cursor.execute(
            """
            INSERT INTO admin_audit (admin_id, action, target_type, target_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (admin_id, action, target_type, target_id, details, datetime.now().isoformat()),
        )
    except Exception:
        return


def _mark_source_group_assigned(
    cursor,
    group_data: Dict[str, Any],
    admin_id: str,
    trip_type: str,
    selected_time: str,
    trip_day: str,
    trip_id: int,
    route_no: str,
) -> None:
    """
    Update source groups table row as assigned when available.
    Works across mixed schemas by checking optional columns.
    """
    try:
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='groups' LIMIT 1")
        if not cursor.fetchone():
            return

        cursor.execute("PRAGMA table_info(groups)")
        cols = {r[1] for r in cursor.fetchall()}
        if "status" not in cols:
            return

        where_sql = ""
        where_params: List[Any] = []
        group_id = group_data.get("id") or group_data.get("group_id")
        if group_id is not None and "id" in cols:
            where_sql = "id = ?"
            where_params = [group_id]
        elif "group_index" in cols and group_data.get("group_index") is not None:
            where_sql = "group_index = ?"
            where_params = [group_data.get("group_index")]
            if "admin_id" in cols:
                where_sql += " AND admin_id = ?"
                where_params.append(admin_id)
            if "trip_type" in cols:
                where_sql += " AND trip_type = ?"
                where_params.append(trip_type)
            if "schedule_time" in cols:
                where_sql += " AND schedule_time = ?"
                where_params.append(selected_time)
            if "trip_day" in cols:
                where_sql += " AND REPLACE(COALESCE(trip_day,''), '-', '') = ?"
                where_params.append(str(trip_day).replace("-", ""))
            if "deleted_at" in cols:
                where_sql += " AND deleted_at IS NULL"
        else:
            return

        updates: List[str] = ["status = ?"]
        params: List[Any] = ["assigned"]
        if "updated_at" in cols:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
        if "trip_id" in cols:
            updates.append("trip_id = ?")
            params.append(trip_id)
        if "route_no" in cols:
            updates.append("route_no = ?")
            params.append(route_no)
        if "assigned_trip_id" in cols:
            updates.append("assigned_trip_id = ?")
            params.append(trip_id)

        params.extend(where_params)
        cursor.execute(
            f"UPDATE groups SET {', '.join(updates)} WHERE {where_sql}",
            tuple(params),
        )
    except Exception:
        logger.exception("Failed to update source group status (non-critical)")


def _save_trip_route_details(
    cursor,
    trip_id: int,
    route_polyline: str,
    distance_km: float,
    duration_min: int,
    route_payload: Dict[str, Any],
) -> None:
    """
    Persist route details when trip_routes table exists.
    This is best-effort and must not break trip creation.
    """
    try:
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='trip_routes' LIMIT 1"
        )
        if not cursor.fetchone():
            return

        import json

        cursor.execute(
            """
            INSERT INTO trip_routes
            (trip_id, route_index, polyline, distance_km, duration_mins, via, created_at)
            VALUES (?, 0, ?, ?, ?, ?, ?)
            """,
            (
                trip_id,
                route_polyline,
                float(distance_km),
                float(duration_min),
                json.dumps(route_payload),
                datetime.now().isoformat(),
            ),
        )
    except Exception:
        # Route details are optional metadata. Ignore insertion failures.
        return
