# backend/services/auto_grouping_service.py
# RG Travel Solution - Full Auto-Grouping Integration Service
# STEP 9: Complete integration of Steps 4-9

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


def create_auto_grouped_trips(
    db_conn,
    admin_id: str,
    operation: str,
    schedule_time: str,
    vehicle_type: int,
    employee_ids: List[int],
    office_lat: float,
    office_lng: float
) -> Dict[str, Any]:
    """
    Full auto-grouping pipeline: Steps 4-9.
    
    Algorithm:
        1. Fetch employee data
        2. Get cab availability
        3. Optimize capacity (Step 4)
        4. Rebalance group sizes (Step 5)
        5. Cluster by proximity (Step 6)
        6. Generate routes (Step 7)
        7. Assign drivers (Step 8)
        8. Create trips with route nos. + OTPs (Step 9)
    
    Args:
        db_conn: Database connection
        admin_id: Admin ID creating trips
        operation: "pickup" or "drop"
        schedule_time: HH:MM format
        vehicle_type: 4 or 6
        employee_ids: List of employee IDs
        office_lat, office_lng: Office coordinates
    
    Returns:
        {
            "success": True,
            "message": "Created 3 trips with auto-grouping",
            "data": {
                "trips": [
                    {
                        "route_no": "20264821FE",
                        "trip_id": 123,
                        "driver_id": "drv_abc",
                        "driver_name": "John Doe",
                        "vehicle_no": "MH12AB1234",
                        "employee_count": 4,
                        "employees": [...],
                        "route_summary": {...},
                        "otps": {...}
                    },
                    ...
                ]
            }
        }
    """
    try:
        # STEP 1: Fetch employees
        from db.database import query
        
        placeholders = ','.join(['?' for _ in employee_ids])
        sql = f"""
            SELECT id, name, mobile, email,
                   home_lat, home_lng, home_address,
                   pickup_lat, pickup_lng, pickup_address
            FROM employees
            WHERE id IN ({placeholders})
        """
        
        employee_rows = query(db_conn, sql, employee_ids)
        
        if len(employee_rows) < len(employee_ids):
            return {
                "success": False,
                "message": f"Some employees not found: requested {len(employee_ids)}, found {len(employee_rows)}"
            }
        
        # Convert to EmployeePoint objects for clustering
        from services.grouping_service import EmployeePoint
        
        employees = []
        for row in employee_rows:
            # Use pickup coordinates for pickup trips, home for drop trips
            if operation == "pickup":
                lat = row.get("pickup_lat") or row.get("home_lat")
                lng = row.get("pickup_lng") or row.get("home_lng")
                address = row.get("pickup_address") or row.get("home_address") or ""
            else:  # drop
                lat = row.get("home_lat")
                lng = row.get("home_lng")
                address = row.get("home_address") or ""
            
            if not lat or not lng:
                logger.warning(f"Employee {row['id']} missing coordinates, skipping")
                continue
            
            employees.append(EmployeePoint(
                id=row["id"],
                name=row["name"],
                lat=float(lat),
                lng=float(lng),
                address=address
            ))
        
        if not employees:
            return {
                "success": False,
                "message": "No employees with valid coordinates"
            }
        
        # STEP 2: Get availability
        from services.availability_service import scan_cab_availability
        availability = scan_cab_availability(db_conn)
        
        # STEP 3: Optimize capacity (Step 4)
        from services.capacity_optimizer import optimize_cab_capacity
        optimization = optimize_cab_capacity(
            num_employees=len(employees),
            available_4_seaters=availability["available4Count"],
            available_6_seaters=availability["available6Count"]
        )
        
        if not optimization["success"]:
            return optimization  # Return error
        
        # STEP 4: Rebalance group sizes (Step 5)
        from services.capacity_optimizer import rebalance_group_sizes
        group_sizes = rebalance_group_sizes(
            num_employees=len(employees),
            group_capacity=vehicle_type
        )
        
        logger.info(f"Group sizes after rebalancing: {group_sizes}")
        
        # STEP 5: Cluster by proximity (Step 6)
        from services.geo_clustering import cluster_employees_by_proximity
        employee_groups = cluster_employees_by_proximity(
            employees=employees,
            group_sizes=group_sizes,
            office_lat=office_lat,
            office_lng=office_lng
        )
        
        logger.info(f"Created {len(employee_groups)} groups after clustering")
        
        # STEP 6: Generate routes (Step 7)
        from services.route_planning import get_optimized_route, calculate_stop_etas
        
        routes = []
        for group in employee_groups:
            waypoints = [(emp.lat, emp.lng) for emp in group]
            route_result = get_optimized_route(
                office_lat=office_lat,
                office_lng=office_lng,
                waypoints=waypoints,
                return_to_office=True
            )
            
            if route_result["success"]:
                routes.append(route_result["data"])
            else:
                logger.error(f"Route generation failed: {route_result.get('message')}")
                return route_result
        
        # STEP 7: Assign drivers (Step 8)
        from services.driver_assignment import assign_drivers_to_groups, calculate_route_area
        
        today = datetime.now().strftime("%Y%m%d")
        
        try:
            assignments = assign_drivers_to_groups(
                db_conn=db_conn,
                groups=[[{"lat": e.lat, "lng": e.lng, "address": e.home_address} for e in group] for group in employee_groups],
                vehicle_type=vehicle_type,
                operation=operation,
                trip_day=today
            )
        except ValueError as e:
            return {
                "success": False,
                "message": str(e)
            }
        
        # STEP 8: Create trips (Step 9)
        from services.trip_service import (
            generate_route_no, create_trip_otps, create_trip_record,
            assign_employee_to_trip, record_driver_assignment
        )
        
        trips = []
        
        for group_idx, (group, route, assignment) in enumerate(zip(employee_groups, routes, assignments)):
            # Generate route number
            route_no = generate_route_no(db_conn)
            
            # Generate OTPs
            otps = create_trip_otps(
                start_validity_minutes=30,
                end_validity_minutes=120
            )
            
            # Calculate route area for tracking
            route_area = calculate_route_area(
                [{"lat": e.lat, "lng": e.lng, "pickup_lat": e.lat, "home_lat": e.lat} for e in group],
                operation
            )
            
            # Add route_area to assignment data
            assignment["route_area"] = route_area
            
            # Create trip record
            trip_id = create_trip_record(
                db_conn=db_conn,
                route_no=route_no,
                admin_id=admin_id,
                driver_id=assignment["driver_id"],
                operation=operation,
                schedule_time=schedule_time,
                vehicle_type=vehicle_type,
                route_data=route,
                assignment_data=assignment,
                otps=otps
            )
            
            # Assign employees to trip with stop sequence and ETA
            # Reorder employees based on optimized waypoint order
            optimized_order = route.get("optimized_waypoint_order", list(range(len(group))))
            ordered_employees = [group[i] for i in optimized_order]
            
            etas = calculate_stop_etas(schedule_time, route["legs"][:-1])  # Exclude return to office
            
            for stop_idx, (emp, eta) in enumerate(zip(ordered_employees, etas), 1):
                assign_employee_to_trip(
                    db_conn=db_conn,
                    trip_id=trip_id,
                    employee_id=emp.id,
                    stop_sequence=stop_idx,
                    estimated_arrival_time=eta
                )
            
            # Record driver assignment history
            record_driver_assignment(
                db_conn=db_conn,
                driver_id=assignment["driver_id"],
                trip_id=trip_id,
                route_area=route_area,
                trip_distance_km=route.get("total_distance_km", 0),
                workload_score=assignment["workload_score"],
                assignment_reason=assignment["assignment_reason"]
            )
            
            # Helper to get driver details
            driver_phone = ""
            try:
                driver_res = query(db_conn, "SELECT mobile FROM drivers WHERE id = ?", [assignment["driver_id"]])
                if driver_res:
                    driver_phone = driver_res[0]["mobile"]
            except Exception:
                pass

            # Build trip response
            employee_details = []
            for stop_idx, (emp, eta) in enumerate(zip(ordered_employees, etas), 1):
                employee_details.append({
                    "id": emp.id,
                    "name": emp.name,
                    "stop_sequence": stop_idx,
                    "eta": eta,
                    "address": emp.address
                })
            
            trip_response_data = {
                "route_no": route_no,
                "trip_id": trip_id,
                "driver_id": assignment["driver_id"],
                "driver_name": assignment["driver_name"],
                "vehicle_no": assignment["vehicle_no"],
                "vehicle_type": vehicle_type,
                "employee_count": len(group),
                "employees": employee_details,
                "route_summary": {
                    "total_distance_km": route.get("total_distance_km", 0),
                    "total_duration_minutes": route.get("total_duration_minutes", 0),
                    "polyline": route.get("polyline", ""),
                    "source": route.get("source", "unknown")
                },
                "assignment_details": {
                    "workload_score": assignment["workload_score"],
                    "assignment_reason": assignment["assignment_reason"],
                    "weekly_trips": assignment.get("weekly_trips", 0)
                },
                "otps": {
                    "start_otp": otps["start_otp_plain"],
                    "start_otp_expiry": otps["start_otp_expiry"],
                    "end_otp": otps["end_otp_plain"],
                    "end_otp_expiry": otps["end_otp_expiry"]
                }
            }
            trips.append(trip_response_data)
            
            # Broadcast assignment notification
            from services.socket_service import broadcast_trip_assignment
            
            broadcast_trip_assignment(
                route_no=route_no,
                trip_data={
                    "trip_id": trip_id,
                    "driver_name": assignment["driver_name"],
                    "driver_phone": driver_phone,
                    "vehicle_no": assignment["vehicle_no"],
                    "schedule_time": schedule_time,
                    "operation": operation,
                    "employees": employee_details,
                    "route_summary": trip_response_data["route_summary"],
                    "otps": trip_response_data["otps"]
                }
            )
        
        # Commit transaction
        db_conn.commit()
        
        logger.info(f"Successfully created {len(trips)} trips with auto-grouping")
        
        return {
            "success": True,
            "message": f"Created {len(trips)} trips with auto-grouping",
            "data": {
                "trips": trips,
                "summary": {
                    "total_trips": len(trips),
                    "total_employees": len(employees),
                    "vehicle_type": vehicle_type,
                    "operation": operation
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Auto-grouping failed: {e}", exc_info=True)
        db_conn.rollback()
        return {
            "success": False,
            "message": f"Auto-grouping failed: {str(e)}"
        }
