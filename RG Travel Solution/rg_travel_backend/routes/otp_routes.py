# rg_travel_backend/routes/otp_routes.py
"""
OTP endpoints for trip start/end verification.
Wires services/otp_service.py to HTTP API.
"""

from flask import Blueprint, request, jsonify

# Safe imports
try:
    from db import get_db
    from services.otp_service import (
        create_trip_otps,
        verify_trip_otp_and_update,
        get_trip_otp_status,
        get_or_create_trip_otp_for_employee
    )
except ImportError:
    from db import get_db  # type: ignore
    from services.otp_service import (  # type: ignore
        create_trip_otps,
        verify_trip_otp_and_update,
        get_trip_otp_status,
        get_or_create_trip_otp_for_employee
    )

otp_bp = Blueprint("otp", __name__, url_prefix="/api/trip")


@otp_bp.route("/<route_no>", methods=["GET"])
def get_trip_details_by_route(route_no):
    """
    Get full trip details by route number.
    Used by employee/driver tracking screens.
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT t.id, t.route_no, t.trip_type, t.schedule_time, t.status, t.driver_id,
                   t.vehicle_type, t.total_km, t.office_lat, t.office_lng, t.created_at, t.updated_at,
                   d.name, d.mobile, d.vehicle_no
            FROM trips t
            LEFT JOIN drivers d ON d.id = t.driver_id
            WHERE t.route_no = ?
            LIMIT 1
            """,
            (route_no,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Trip not found"}), 404

        trip_id = row[0]
        cur.execute(
            """
            SELECT te.employee_id, e.name, e.mobile, te.sequence_no, te.is_no_show,
                   COALESCE(e.home_address, e.pickup_address, '') AS address
            FROM trip_employees te
            JOIN employees e ON e.id = te.employee_id
            WHERE te.trip_id = ?
            ORDER BY te.sequence_no ASC
            """,
            (trip_id,),
        )
        employees = [
            {
                "employee_id": r[0],
                "name": r[1],
                "mobile": r[2],
                "sequence_no": r[3],
                "is_no_show": bool(r[4]),
                "address": r[5],
            }
            for r in cur.fetchall()
        ]

        return jsonify(
            {
                "success": True,
                "data": {
                    "trip_id": row[0],
                    "route_no": row[1],
                    "trip_type": row[2],
                    "schedule_time": row[3],
                    "status": row[4],
                    "driver_id": row[5],
                    "vehicle_type": row[6],
                    "total_km": row[7],
                    "office_lat": row[8],
                    "office_lng": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                    "driver_name": row[12],
                    "driver_mobile": row[13],
                    "cab_no": row[14],
                    "employees": employees,
                },
            }
        ), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


@otp_bp.route("/<route_no>/otp", methods=["GET"])
def get_trip_otp(route_no):
    """
    Get OTP for a trip (employee-facing).
    
    Query params:
      - type: 'start' or 'end'
    
    Returns:
      {
        "success": true,
        "data": {
          "trip_id": 123,
          "otp_type": "start",
          "otp": "123456",
          "expires_at": "2026-02-04T12:05:00+00:00"
        }
      }
    """
    try:
        otp_type = request.args.get("type", "start").strip().lower()
        if otp_type not in ("start", "end"):
            return jsonify({"success": False, "message": "type must be 'start' or 'end'"}), 400
        
        conn = get_db()
        cur = conn.cursor()
        
        # Get trip_id from route_no
        cur.execute("SELECT id FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Trip not found"}), 404
        
        trip_id = int(row[0])
        
        # Get or create OTP
        result = get_or_create_trip_otp_for_employee(conn, trip_id, otp_type)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
            conn.close()
        except:
            pass


@otp_bp.route("/<route_no>/otp/verify", methods=["POST"])
def verify_trip_otp(route_no):
    """
    Verify OTP and update trip status.
    
    Body:
      {
        "type": "start" | "end",
        "otp": "123456",
        "driver_id": "drv_xxx"
      }
    
    Returns:
      {
        "success": true,
        "message": "Trip started successfully.",
        "data": {
          "trip_id": 123,
          "status": "started",
          "trip_type": "pickup"
        }
      }
    """
    try:
        data = request.json or {}
        otp_type = data.get("type", "").strip().lower()
        otp_input = data.get("otp", "").strip()
        driver_id = data.get("driver_id")
        
        if not otp_input:
            return jsonify({"success": False, "message": "OTP required"}), 400
        
        conn = get_db()
        cur = conn.cursor()
        
        # Get trip_id from route_no
        cur.execute("SELECT id FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Trip not found"}), 404
        
        trip_id = int(row[0])
        
        # Verify OTP
        result = verify_trip_otp_and_update(conn, trip_id, otp_type, otp_input, driver_id)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
            conn.close()
        except:
            pass


@otp_bp.route("/<route_no>/otp/status", methods=["GET"])
def get_otp_status(route_no):
    """
    Get OTP status for admin/driver UI.
    
    Returns:
      {
        "success": true,
        "data": {
          "trip_id": 123,
          "start": {"exists": true, "is_used": false, "expired": false, "expires_at": "..."},
          "end": {"exists": true, "is_used": false, "expired": false, "expires_at": "..."}
        }
      }
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM trips WHERE route_no = ? LIMIT 1", (route_no,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Trip not found"}), 404
        
        trip_id = int(row[0])
        result = get_trip_otp_status(conn, trip_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        try:
            conn.close()
        except:
            pass
