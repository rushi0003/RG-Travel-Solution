from typing import Any, Dict, Optional, List
import json
from datetime import datetime

try:
    from ..db import get_db
    from ..repositories.trip_repo import TripRepo
    from ..utils.logger import get_logger
except (ImportError, ValueError):
    from db import get_db
    from repositories.trip_repo import TripRepo
    from utils.logger import get_logger

from . import routing_service, notification_service

logger = get_logger(__name__)

class AdminOverrideService:
    def __init__(self):
        # We perform operations in a transaction per method call
        pass

    def _should_close(self, conn) -> bool:
        """
        Avoid closing in-memory DB connections (used by tests).
        """
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA database_list")
            rows = cur.fetchall()
            for r in rows:
                # r[2] is file path; '' or ':memory:' implies in-memory
                if len(r) >= 3 and (r[2] == "" or r[2] == ":memory:"):
                    return False
        except Exception:
            return True
        return True

    def move_employee(self, admin_id: str, employee_id: str, from_trip_id: int, to_trip_id: int) -> Dict[str, Any]:
        """
        Moves an employee from one trip to another.
        Validates capacity and updates routes for both trips.
        """
        conn = get_db()
        repo = TripRepo(conn)

        try:
            # 1. Fetch Trip Info
            from_trip = repo.get_trip_by_id(from_trip_id)
            to_trip = repo.get_trip_by_id(to_trip_id)

            if not from_trip or not to_trip:
                return {"success": False, "message": "Source or destination trip not found."}

            if from_trip["trip_type"] != to_trip["trip_type"]:
                return {"success": False, "message": "Cannot move between different trip types."}

            # 2. Check Capacity
            to_capacity_info = repo.get_trip_capacity_info(to_trip_id)
            current_count = to_capacity_info["member_count"]
            vehicle_capacity = 4 if str(to_trip["vehicle_type"]) == "4" else 6 # Simplified, or fetch from cabs
            
            if current_count >= vehicle_capacity:
                return {"success": False, "message": f"Destination trip is full (Capacity: {vehicle_capacity})."}

            # 3. Validation: Is employee in from_trip?
            from_members = repo.list_trip_members(from_trip_id)
            emp_record = next((m for m in from_members if str(m["employee_id"]) == str(employee_id)), None)
            if not emp_record:
                return {"success": False, "message": "Employee not found in source trip."}

            # 4. Execute Move (Transaction)
            # Remove from 'from_trip'
            # We need to construct the new list for from_trip
            new_from_members_ids = [m["employee_id"] for m in from_members if str(m["employee_id"]) != str(employee_id)]
            repo.add_trip_members(from_trip_id, new_from_members_ids) # This replaces all members

            # Add to 'to_trip'
            to_members = repo.list_trip_members(to_trip_id)
            new_to_members_ids = [m["employee_id"] for m in to_members]
            new_to_members_ids.append(employee_id)
            repo.add_trip_members(to_trip_id, new_to_members_ids)

            # 5. Recalculate Routes (for both)
            self._recalculate_trip_route(repo, from_trip, new_from_members_ids)
            self._recalculate_trip_route(repo, to_trip, new_to_members_ids)

            # 6. Audit Log & Revision
            repo.increment_route_revision(from_trip_id)
            repo.increment_route_revision(to_trip_id)
            
            repo.log_trip_event(
                trip_id=from_trip_id,
                route_no=from_trip["route_no"],
                event_type="override_move_out",
                actor_role="admin",
                actor_id=admin_id,
                payload_json=json.dumps({"employee_id": employee_id, "to_trip": to_trip["route_no"]})
            )
            repo.log_trip_event(
                trip_id=to_trip_id,
                route_no=to_trip["route_no"],
                event_type="override_move_in",
                actor_role="admin",
                actor_id=admin_id,
                payload_json=json.dumps({"employee_id": employee_id, "from_trip": from_trip["route_no"]})
            )

            conn.commit()
            
            # 7. Notification
            notification_service.NotificationService.create_notification(
                admin_id=admin_id,
                title="Trip Updated (Override)",
                message=f"Employee {employee_id} moved from {from_trip['route_no']} to {to_trip['route_no']}.",
                type="info"
            )
            
            return {"success": True, "message": "Employee moved successfully."}

        except Exception as e:
            conn.rollback()
            logger.error(f"move_employee failed: {e}")
            return {"success": False, "message": str(e)}
        finally:
            if self._should_close(conn):
                conn.close()

    def swap_vehicle(self, admin_id: str, trip_id: int, new_vehicle_no: str, new_driver_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Swaps vehicle/driver for a trip.
        """
        conn = get_db()
        repo = TripRepo(conn)
        try:
            trip = repo.get_trip_by_id(trip_id)
            if not trip:
                return {"success": False, "message": "Trip not found."}

            if new_driver_id:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM drivers WHERE id = ? LIMIT 1", (new_driver_id,))
                if not cur.fetchone():
                    new_driver_id = None

            repo.update_trip_assignment(
                trip_id=trip_id,
                vehicle_no=new_vehicle_no,
                driver_id=new_driver_id
            )

            # If trips table doesn't store vehicle_no, update driver's vehicle_no.
            if new_vehicle_no:
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(trips)")
                cols = {row[1] for row in cur.fetchall()}
                if "vehicle_no" not in cols:
                    target_driver = new_driver_id or trip.get("driver_id")
                    if target_driver:
                        cur.execute(
                            "UPDATE drivers SET vehicle_no = ?, updated_at = ? WHERE id = ?",
                            (new_vehicle_no, datetime.utcnow().isoformat(), str(target_driver)),
                        )

            repo.increment_route_revision(trip_id)
            
            repo.log_trip_event(
                trip_id=trip_id,
                route_no=trip["route_no"],
                event_type="override_swap_vehicle",
                actor_role="admin",
                actor_id=admin_id,
                payload_json=json.dumps({
                    "old_vehicle": trip["vehicle_no"],
                    "new_vehicle": new_vehicle_no,
                    "old_driver": trip["driver_id"],
                    "new_driver": new_driver_id
                })
            )
            
            conn.commit()

            # Notification
            notification_service.NotificationService.create_notification(
                admin_id=admin_id,
                title="Trip Updated (Override)",
                message=f"Vehicle for trip {trip['route_no']} swapped to {new_vehicle_no}.",
                type="info"
            )

            return {"success": True, "message": "Vehicle swapped successfully."}

        except Exception as e:
            conn.rollback()
            return {"success": False, "message": str(e)}
        finally:
            if self._should_close(conn):
                conn.close()

    def _recalculate_trip_route(self, repo: TripRepo, trip: Dict[str, Any], member_ids: List[str]) -> None:
        """
        Internal helper to recalculate and update route params.
        """
        if not member_ids:
            # Empty trip
            repo.update_route_data(trip["id"], route_polyline="", stops_json="[]", total_km=0)
            return

        # Fetch member details to get lat/lng
        # We need to query employees table essentially, but repo has list_trip_members.
        # However, list_trip_members joins on trip_members.
        # Since we just updated trip_members in the transaction, list_trip_members SHOULD see the new members 
        # (if we are in the same transaction?).
        # Yes, standard SQL behavior.
        
        current_members = repo.list_trip_members(trip["id"])
        # Map to coords
        stop_coords = []
        for m in current_members:
            if m["home_lat"] and m["home_lng"]:
                 stop_coords.append((float(m["home_lat"]), float(m["home_lng"])))
        
        office_lat = trip.get("office_lat")
        office_lng = trip.get("office_lng")

        if not office_lat or not office_lng:
            # Fallback if office calc missing (shouldn't happen with migration)
            # Maybe use first member as origin?
            # For now, log warning and skip?
            logger.warning(f"Trip {trip['id']} missing office coords. Skipping routing.")
            return

        # Call routing service
        route = routing_service.build_multi_stop_route(
            origin=(float(office_lat), float(office_lng)),
            stops=stop_coords,
            destination=(float(office_lat), float(office_lng)),
            optimize=True
        )

        if route.get("success"):
            repo.update_route_data(
                trip_id=trip["id"],
                route_polyline=route.get("polyline"),
                stops_json=json.dumps(route.get("ordered_points")), # approximate
                total_km=route.get("total_km")
            )
            
            # If validated re-ordering is needed (e.g. updating pickup_order in DB), 
            # we would do it here using route['ordered_points'] matching back to members.
            # For now, we assume optimal order is for ROUTE display.
