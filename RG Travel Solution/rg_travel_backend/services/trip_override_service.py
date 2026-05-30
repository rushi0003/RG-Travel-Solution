# backend/services/trip_override_service.py
# RG Travel Solution - Admin Override Operations Service
# STEP 10: Manual trip modifications with validation and audit trail

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def _table_exists(db_conn, table_name: str) -> bool:
    cur = db_conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return cur.fetchone() is not None


def _columns(db_conn, table_name: str) -> set:
    cur = db_conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return {r[1] for r in cur.fetchall()}


def _trip_employee_sequence_col(db_conn) -> str:
    cols = _columns(db_conn, "trip_employees")
    if "sequence_no" in cols:
        return "sequence_no"
    if "stop_sequence" in cols:
        return "stop_sequence"
    return "id"


def get_trip_by_id(db_conn, trip_id: int) -> Optional[Dict[str, Any]]:
    """Fetch trip by ID."""
    from db.database import query
    
    result = query(db_conn, "SELECT * FROM trips WHERE id = ?", [trip_id])
    return dict(result[0]) if result else None


def get_trip_employees(db_conn, trip_id: int) -> List[Dict[str, Any]]:
    """Get list of employees in a trip."""
    from db.database import query
    
    seq_col = _trip_employee_sequence_col(db_conn)
    rows = query(
        db_conn,
        f"""SELECT te.*, e.name, e.mobile
            FROM trip_employees te
            JOIN employees e ON te.employee_id = e.id
            WHERE te.trip_id = ?
            ORDER BY te.{seq_col}""",
        [trip_id],
    )
    return [dict(r) for r in rows]


def get_trip_employees_with_coords(
    db_conn,
    trip_id: int,
    operation: str
) -> List[Dict[str, Any]]:
    """Get employees with coordinates for route calculation."""
    from db.database import query
    
    sql = """
        SELECT 
            te.employee_id, e.name, e.mobile,
            e.home_lat, e.home_lng, e.home_address,
            e.pickup_lat, e.pickup_lng, e.pickup_address
        FROM trip_employees te
        JOIN employees e ON te.employee_id = e.id
        WHERE te.trip_id = ?
    """
    
    employees = [dict(r) for r in query(db_conn, sql, [trip_id])]
    
    # Extract appropriate coordinates based on operation
    result = []
    for emp in employees:
        if operation == "pickup":
            lat = emp.get("pickup_lat") or emp.get("home_lat")
            lng = emp.get("pickup_lng") or emp.get("home_lng")
        else:  # drop
            lat = emp.get("home_lat")
            lng = emp.get("home_lng")
        
        if lat and lng:
            result.append({
                "employee_id": emp["employee_id"],
                "name": emp["name"],
                "lat": float(lat),
                "lng": float(lng)
            })
    
    return result


def record_audit_log(
    db_conn,
    trip_id: int,
    route_no: str,
    revision_number: int,
    action_type: str,
    performed_by: str,
    old_state: str,
    new_state: str,
    reason: str = ""
) -> None:
    """Record audit log entry."""
    from db.database import execute
    
    now = datetime.now()
    
    if _table_exists(db_conn, "trip_audit_log"):
        sql = """
            INSERT INTO trip_audit_log (
                trip_id, route_no, revision_number,
                action_type, performed_by, performed_at,
                old_state, new_state, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        execute(
            db_conn,
            sql,
            [
                trip_id,
                route_no,
                revision_number,
                action_type,
                performed_by,
                now.isoformat(),
                old_state,
                new_state,
                reason,
                now.isoformat(),
            ],
        )
    elif _table_exists(db_conn, "admin_audit"):
        execute(
            db_conn,
            """
            INSERT INTO admin_audit (admin_id, action, target_type, target_id, details, created_at)
            VALUES (?, ?, 'trip', ?, ?, ?)
            """,
            [performed_by, action_type, str(trip_id), reason or new_state, now.isoformat()],
        )
    
    logger.info(f"Recorded audit log: {action_type} for trip {trip_id} (v{revision_number})")


def recalculate_trip_route(
    db_conn,
    trip_id: int,
    admin_id: str
) -> Dict[str, Any]:
    """
    Recalculate route for a trip after employee changes.
    
    Steps:
        1. Get current trip employees with coordinates
        2. Get office coordinates
        3. Call route planning service
        4. Update trip with new route data
        5. Update employee stop sequences and ETAs
        6. Increment route_revision
    
    Returns:
        Updated trip data
    """
    from db.database import query, execute
    from services.route_planning import get_optimized_route, calculate_stop_etas
    
    # Get trip details
    trip = get_trip_by_id(db_conn, trip_id)
    if not trip:
        raise ValueError(f"Trip {trip_id} not found")
    
    employees = get_trip_employees_with_coords(db_conn, trip_id, trip["operation"])
    
    if not employees:
        raise ValueError(f"No employees with valid coordinates in trip {trip_id}")
    
    # Get office coordinates (from admin)
    admin_data = query(db_conn, 
        "SELECT office_location FROM admins WHERE id = ?",
        [trip["admin_id"]]
    )
    
    if not admin_data or not admin_data[0].get("office_location"):
        # Fallback to default coordinates
        office_lat, office_lng = 19.0760, 72.8777
    else:
        office_loc = admin_data[0]["office_location"]
        try:
            # Try to parse "lat,lng" format
            parts = office_loc.split(",")
            office_lat = float(parts[0].strip())
            office_lng = float(parts[1].strip())
        except:
            office_lat, office_lng = 19.0760, 72.8777
    
    # Generate new route
    waypoints = [(emp["lat"], emp["lng"]) for emp in employees]
    route_result = get_optimized_route(
        office_lat=office_lat,
        office_lng=office_lng,
        waypoints=waypoints,
        return_to_office=True
    )
    
    if not route_result["success"]:
        raise Exception(f"Route recalculation failed: {route_result.get('message')}")
    
    route_data = route_result["data"]
    
    # Update trip
    new_revision = trip.get("route_revision", 1) + 1
    now = datetime.now()
    
    trip_cols = _columns(db_conn, "trips")
    updates = []
    params = []
    if "total_km" in trip_cols:
        updates.append("total_km = ?")
        params.append(route_data.get("total_distance_km", route_data.get("total_km", 0)))
    if "total_duration_minutes" in trip_cols:
        updates.append("total_duration_minutes = ?")
        params.append(route_data.get("total_duration_minutes", 0))
    if "polyline" in trip_cols:
        updates.append("polyline = ?")
        params.append(route_data.get("polyline", ""))
    if "route_json" in trip_cols:
        updates.append("route_json = ?")
        params.append(json.dumps(route_data))
    if "optimized_waypoint_order" in trip_cols:
        updates.append("optimized_waypoint_order = ?")
        params.append(json.dumps(route_data.get("optimized_waypoint_order", [])))
    if "route_revision" in trip_cols:
        updates.append("route_revision = ?")
        params.append(new_revision)
    if "last_modified_by" in trip_cols:
        updates.append("last_modified_by = ?")
        params.append(admin_id)
    if "last_modified_at" in trip_cols:
        updates.append("last_modified_at = ?")
        params.append(now.isoformat())
    if "updated_at" in trip_cols:
        updates.append("updated_at = ?")
        params.append(now.isoformat())
    if updates:
        params.append(trip_id)
        execute(db_conn, f"UPDATE trips SET {', '.join(updates)} WHERE id = ?", params)
    
    # Update employee stop sequences and ETAs
    optimized_order = route_data.get("optimized_waypoint_order", list(range(len(employees))))
    ordered_employees = [employees[i] for i in optimized_order]
    
    # Calculate ETAs (exclude last leg which is return to office)
    legs = route_data.get("legs", [])
    if legs:
        etas = calculate_stop_etas(trip["schedule_time"], legs[:-1])
    else:
        etas = [""] * len(ordered_employees)
    
    te_cols = _columns(db_conn, "trip_employees")
    seq_col = "sequence_no" if "sequence_no" in te_cols else ("stop_sequence" if "stop_sequence" in te_cols else None)
    eta_col = "estimated_arrival_time" if "estimated_arrival_time" in te_cols else None
    for stop_idx, (emp, eta) in enumerate(zip(ordered_employees, etas), 1):
        updates = []
        params = []
        if seq_col:
            updates.append(f"{seq_col} = ?")
            params.append(stop_idx)
        if eta_col:
            updates.append(f"{eta_col} = ?")
            params.append(eta)
        if not updates:
            continue
        params.extend([trip_id, str(emp["employee_id"])])
        execute(
            db_conn,
            f"UPDATE trip_employees SET {', '.join(updates)} WHERE trip_id = ? AND employee_id = ?",
            params,
        )
    
    logger.info(f"Recalculated route for trip {trip_id}, new revision: v{new_revision}")
    
    return get_trip_by_id(db_conn, trip_id)


def move_employee_between_trips(
    db_conn,
    employee_id: int,
    source_trip_id: int,
    destination_trip_id: int,
    admin_id: str,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Move employee from one trip to another.
    
    Validations:
        - Both trips exist and have same operation/schedule_time
        - Destination has capacity available
        - Employee is in source trip
        - Trips are editable (status: created/assigned)
    
    Steps:
        1. Validate all conditions
        2. Remove from source trip
        3. Add to destination trip
        4. Recalculate routes for both trips
        5. Increment route_revision for both
        6. Record audit log
    
    Returns:
        {
            "success": True,
            "message": "Employee moved successfully",
            "data": {
                "source_trip": {...},
                "destination_trip": {...}
            }
        }
    """
    from db.database import execute
    
    try:
        # STEP 1: Fetch both trips
        source_trip = get_trip_by_id(db_conn, source_trip_id)
        dest_trip = get_trip_by_id(db_conn, destination_trip_id)
        
        # STEP 2: Validations
        if not source_trip or not dest_trip:
            return {"success": False, "message": "Trip not found"}
        
        if source_trip["operation"] != dest_trip["operation"]:
            return {
                "success": False,
                "message": f"Trips must have same operation type (source: {source_trip['operation']}, dest: {dest_trip['operation']})"
            }
        
        if source_trip["schedule_time"] != dest_trip["schedule_time"]:
            return {
                "success": False,
                "message": f"Trips must have same schedule time (source: {source_trip['schedule_time']}, dest: {dest_trip['schedule_time']})"
            }
        
        if source_trip["status"] not in ["created", "assigned"]:
            return {
                "success": False,
                "message": f"Source trip status '{source_trip['status']}' not editable (must be 'created' or 'assigned')"
            }
        
        if dest_trip["status"] not in ["created", "assigned"]:
            return {
                "success": False,
                "message": f"Destination trip status '{dest_trip['status']}' not editable (must be 'created' or 'assigned')"
            }
        
        # Check employee is in source trip
        source_employees = get_trip_employees(db_conn, source_trip_id)
        employee_ids = [int(e["employee_id"]) for e in source_employees]
        
        if employee_id not in employee_ids:
            return {"success": False, "message": "Employee not in source trip"}
        
        # Check destination capacity
        dest_employees = get_trip_employees(db_conn, destination_trip_id)
        vehicle_capacity = int(dest_trip["vehicle_type"])
        
        if len(dest_employees) >= vehicle_capacity:
            return {
                "success": False,
                "message": f"Destination trip at capacity ({len(dest_employees)}/{vehicle_capacity})"
            }
        
        # STEP 3: Record old state for audit
        old_source_state = {
            "trip_id": source_trip_id,
            "employee_ids": employee_ids,
            "route_revision": source_trip.get("route_revision", 1)
        }
        
        old_dest_state = {
            "trip_id": destination_trip_id,
            "employee_ids": [int(e["employee_id"]) for e in dest_employees],
            "route_revision": dest_trip.get("route_revision", 1)
        }
        
        # STEP 4: Remove from source
        execute(db_conn,
            "DELETE FROM trip_employees WHERE trip_id = ? AND employee_id = ?",
            [source_trip_id, str(employee_id)]
        )
        
        # STEP 5: Add to destination
        now = datetime.now()
        seq_col = _trip_employee_sequence_col(db_conn)
        if seq_col in ("sequence_no", "stop_sequence"):
            max_seq_rows = get_trip_employees(db_conn, destination_trip_id)
            next_seq = (len(max_seq_rows) + 1)
            execute(
                db_conn,
                f"""INSERT INTO trip_employees (trip_id, employee_id, {seq_col}, created_at)
                    VALUES (?, ?, ?, ?)""",
                [destination_trip_id, str(employee_id), next_seq, now.isoformat()],
            )
        else:
            execute(
                db_conn,
                """INSERT INTO trip_employees (trip_id, employee_id, created_at)
                   VALUES (?, ?, ?)""",
                [destination_trip_id, str(employee_id), now.isoformat()],
            )
        
        # STEP 6: Recalculate routes for both trips (best effort)
        try:
            source_updated = recalculate_trip_route(db_conn, source_trip_id, admin_id)
        except Exception as recalc_err:
            logger.warning(f"Source route recalculation skipped: {recalc_err}")
            source_updated = get_trip_by_id(db_conn, source_trip_id) or source_trip
        try:
            dest_updated = recalculate_trip_route(db_conn, destination_trip_id, admin_id)
        except Exception as recalc_err:
            logger.warning(f"Destination route recalculation skipped: {recalc_err}")
            dest_updated = get_trip_by_id(db_conn, destination_trip_id) or dest_trip
        
        # STEP 7: Record audit log for both trips
        record_audit_log(
            db_conn,
            trip_id=source_trip_id,
            route_no=source_trip["route_no"],
            revision_number=source_updated["route_revision"],
            action_type="move_employee_out",
            performed_by=admin_id,
            old_state=json.dumps(old_source_state),
            new_state=json.dumps({
                "trip_id": source_trip_id,
                "employee_ids": [e for e in employee_ids if e != employee_id],
                "route_revision": source_updated["route_revision"]
            }),
            reason=reason
        )
        
        record_audit_log(
            db_conn,
            trip_id=destination_trip_id,
            route_no=dest_trip["route_no"],
            revision_number=dest_updated["route_revision"],
            action_type="move_employee_in",
            performed_by=admin_id,
            old_state=json.dumps(old_dest_state),
            new_state=json.dumps({
                "trip_id": destination_trip_id,
                "employee_ids": old_dest_state["employee_ids"] + [employee_id],
                "route_revision": dest_updated["route_revision"]
            }),
            reason=reason
        )
        
        db_conn.commit()
        
        logger.info(f"Moved employee {employee_id} from trip {source_trip_id} to {destination_trip_id}")
        
        # Broadcast updates to both routes
        try:
            from services.socket_service import broadcast_trip_update

            # Broadcast source trip update
            broadcast_trip_update(
                route_no=source_trip["route_no"],
                update_type="employee_moved",
                trip_data={
                    "trip_id": source_trip_id,
                    "status": source_trip["status"],
                    "route_revision": source_updated.get("route_revision", source_trip.get("route_revision", 1)),
                    "employees": get_trip_employees(db_conn, source_trip_id),
                    "route_summary": json.loads(source_updated.get("route_json", "{}")),
                },
            )

            # Broadcast destination trip update
            broadcast_trip_update(
                route_no=dest_trip["route_no"],
                update_type="employee_moved",
                trip_data={
                    "trip_id": destination_trip_id,
                    "status": dest_trip["status"],
                    "route_revision": dest_updated.get("route_revision", dest_trip.get("route_revision", 1)),
                    "employees": get_trip_employees(db_conn, destination_trip_id),
                    "route_summary": json.loads(dest_updated.get("route_json", "{}")),
                },
            )
        except Exception:
            logger.exception("Socket broadcast failed for move_employee_between_trips")
        
        return {
            "success": True,
            "message": "Employee moved successfully",
            "data": {
                "source_trip": {
                    "trip_id": source_trip_id,
                    "route_no": source_trip["route_no"],
                    "route_revision": source_updated["route_revision"],
                    "employee_count": len([e for e in employee_ids if e != employee_id])
                },
                "destination_trip": {
                    "trip_id": destination_trip_id,
                    "route_no": dest_trip["route_no"],
                    "route_revision": dest_updated["route_revision"],
                    "employee_count": len(old_dest_state["employee_ids"]) + 1
                }
            }
        }
    
    except Exception as e:
        db_conn.rollback()
        logger.error(f"Error moving employee: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to move employee: {str(e)}"
        }


def change_trip_driver(
    db_conn,
    trip_id: int,
    new_driver_id: str,
    admin_id: str,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Change driver/cab for a trip.
    
    Validations:
        - New driver exists and is approved
        - Vehicle type matches trip requirement
        - Driver not in another active trip at same time
        - Trip is editable (status: created/assigned)
    
    Steps:
        1. Validate driver
        2. Update trip driver_id, vehicle_no
        3. Increment route_revision
        4. Record audit log
    
    Returns:
        {
            "success": True,
            "message": "Driver changed successfully",
            "data": {...updated trip...}
        }
    """
    from db.database import query, execute
    
    try:
        # STEP 1: Fetch trip
        trip = get_trip_by_id(db_conn, trip_id)
        
        if not trip:
            return {"success": False, "message": "Trip not found"}
        
        if trip["status"] not in ["created", "assigned"]:
            return {
                "success": False,
                "message": f"Trip status '{trip['status']}' not editable (must be 'created' or 'assigned')"
            }
        
        # STEP 2: Fetch new driver
        driver_result = query(db_conn,
            "SELECT * FROM drivers WHERE id = ? AND is_approved = 1",
            [new_driver_id]
        )
        
        if not driver_result:
            return {"success": False, "message": "Driver not found or not approved"}
        
        driver = driver_result[0]
        
        # Validate vehicle type matches
        if driver["vehicle_type"] != trip["vehicle_type"]:
            return {
                "success": False,
                "message": f"Driver vehicle type {driver['vehicle_type']} doesn't match trip requirement {trip['vehicle_type']}"
            }
        
        # Check driver not in another active trip at same time
        conflicts = query(db_conn,
            """SELECT id, route_no FROM trips
               WHERE driver_id = ?
               AND status IN ('assigned', 'started')
               AND schedule_time = ?
               AND id != ?""",
            [new_driver_id, trip["schedule_time"], trip_id]
        )
        
        if conflicts:
            return {
                "success": False,
                "message": f"Driver already assigned to trip {conflicts[0]['route_no']} at this time"
            }
        
        # STEP 3: Record old state
        old_state = {
            "driver_id": trip["driver_id"],
            "vehicle_no": trip.get("vehicle_no"),
            "route_revision": trip.get("route_revision", 1)
        }
        
        # STEP 4: Update trip
        new_revision = trip.get("route_revision", 1) + 1
        now = datetime.now()
        
        execute(db_conn,
            """UPDATE trips
               SET driver_id = ?, route_revision = ?,
                   last_modified_by = ?, last_modified_at = ?
               WHERE id = ?""",
            [new_driver_id, new_revision, admin_id, now.isoformat(), trip_id]
        )
        
        # STEP 5: Record audit log
        record_audit_log(
            db_conn,
            trip_id=trip_id,
            route_no=trip["route_no"],
            revision_number=new_revision,
            action_type="change_driver",
            performed_by=admin_id,
            old_state=json.dumps(old_state),
            new_state=json.dumps({
                "driver_id": new_driver_id,
                "vehicle_no": driver["vehicle_no"],
                "route_revision": new_revision
            }),
            reason=reason
        )
        
        db_conn.commit()
        
        logger.info(f"Changed driver for trip {trip_id} to {new_driver_id}")
        
        # Fetch updated trip
        updated_trip = get_trip_by_id(db_conn, trip_id)
        
        # Broadcast update
        from services.socket_service import broadcast_trip_update
        
        broadcast_trip_update(
            route_no=trip["route_no"],
            update_type="driver_changed",
            trip_data={
                "trip_id": trip_id,
                "status": trip["status"],
                "route_revision": new_revision,
                "driver_name": driver["name"],
                "driver_phone": driver["mobile"],
                "vehicle_no": driver["vehicle_no"]
            }
        )
        
        return {
            "success": True,
            "message": "Driver changed successfully",
            "data": {
                "trip_id": trip_id,
                "route_no": trip["route_no"],
                "route_revision": new_revision,
                "old_driver_id": trip["driver_id"],
                "new_driver_id": new_driver_id,
                "new_driver_name": driver["name"],
                "new_vehicle_no": driver["vehicle_no"]
            }
        }
    
    except Exception as e:
        db_conn.rollback()
        logger.error(f"Error changing driver: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to change driver: {str(e)}"
        }
