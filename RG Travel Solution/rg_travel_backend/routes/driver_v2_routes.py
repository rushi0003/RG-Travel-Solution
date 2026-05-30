from __future__ import annotations

from flask import Blueprint, request, jsonify

from db import get_db

driver_v2_bp = Blueprint("driver_v2_bp", __name__, url_prefix="/api/v2/drivers")


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # Lightweight distance estimate good enough for nearest-trip ranking.
    from math import cos, radians, sqrt

    km_per_deg_lat = 111.32
    km_per_deg_lng = 111.32 * cos(radians((lat1 + lat2) / 2.0))
    dlat = (lat2 - lat1) * km_per_deg_lat
    dlng = (lng2 - lng1) * km_per_deg_lng
    return sqrt(dlat * dlat + dlng * dlng)


@driver_v2_bp.route("/go-home-requests", methods=["GET"])
def list_go_home_requests():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(drivers)")
        driver_cols = {str(r[1]) for r in cur.fetchall()}
        lat_expr = (
            "COALESCE(d.hometown_lat, d.home_lat, 0)"
            if ("hometown_lat" in driver_cols and "home_lat" in driver_cols)
            else ("COALESCE(d.hometown_lat, 0)" if "hometown_lat" in driver_cols else "0")
        )
        lng_expr = (
            "COALESCE(d.hometown_lng, d.home_lng, 0)"
            if ("hometown_lng" in driver_cols and "home_lng" in driver_cols)
            else ("COALESCE(d.hometown_lng, 0)" if "hometown_lng" in driver_cols else "0")
        )

        cur.execute(
            f"""
            SELECT r.id, r.driver_id, d.name, d.mobile, r.requested_home_town, r.status, r.created_at,
                   {lat_expr} AS home_lat,
                   {lng_expr} AS home_lng
            FROM driver_hometown_requests r
            JOIN drivers d ON d.id = r.driver_id
            WHERE r.status = 'pending'
               OR (
                    r.status = 'approved'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM trips t
                        WHERE CAST(t.driver_id AS TEXT) = CAST(r.driver_id AS TEXT)
                          AND LOWER(COALESCE(t.status, 'created')) IN
                              ('created','assigned','started','active','in_progress','live','completed')
                          AND datetime(COALESCE(t.created_at, t.updated_at, '1970-01-01')) >=
                              datetime(COALESCE(r.updated_at, r.created_at, '1970-01-01'))
                    )
               )
            ORDER BY r.created_at DESC
            """
        )
        rows = cur.fetchall()
        data = [
            {
                "id": r[0],
                "request_id": r[0],
                "driver_id": r[1],
                "driver_name": r[2],
                "mobile": r[3],
                "home_town": r[4],
                "status": r[5],
                "date": r[6],
                "home_lat": float(r[7] or 0),
                "home_lng": float(r[8] or 0),
                "home_location_lat": float(r[7] or 0),
                "home_location_lng": float(r[8] or 0),
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@driver_v2_bp.route("/go-home-requests/<int:request_id>/approve", methods=["POST"])
def approve_go_home_request(request_id: int):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM driver_hometown_requests WHERE id = ?", (request_id,))
        if not cur.fetchone():
            return jsonify({"success": False, "message": "Request not found"}), 404

        cur.execute(
            "UPDATE driver_hometown_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        conn.commit()
        return jsonify({"success": True, "message": "Request approved"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@driver_v2_bp.route("/go-home-requests/<int:request_id>/reject", methods=["POST"])
def reject_go_home_request(request_id: int):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM driver_hometown_requests WHERE id = ?", (request_id,))
        if not cur.fetchone():
            return jsonify({"success": False, "message": "Request not found"}), 404

        cur.execute(
            "UPDATE driver_hometown_requests SET status = 'rejected', updated_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        conn.commit()
        return jsonify({"success": True, "message": "Request rejected"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@driver_v2_bp.route("/<driver_id>/find-nearest-trip", methods=["POST"])
def find_nearest_trip(driver_id: str):
    data = request.get_json(silent=True) or {}
    home_lat = data.get("home_lat")
    home_lng = data.get("home_lng")
    trip_type = str(data.get("trip_type", "")).strip().lower()
    max_distance_km = float(data.get("max_distance_km", 20))
    exclude_trip_ids = data.get("exclude_trip_ids", []) or []

    if home_lat is None or home_lng is None:
        return jsonify({"success": False, "message": "home_lat and home_lng are required"}), 400
    if trip_type not in ("pickup", "drop"):
        return jsonify({"success": False, "message": "trip_type must be pickup or drop"}), 400

    try:
        home_lat = float(home_lat)
        home_lng = float(home_lng)
    except Exception:
        return jsonify({"success": False, "message": "Invalid home coordinates"}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        placeholders = ",".join(["?"] * len(exclude_trip_ids)) if exclude_trip_ids else ""
        sql = """
            SELECT id, route_no, office_lat, office_lng, schedule_time
            FROM trips
            WHERE trip_type = ?
              AND status IN ('created', 'assigned', 'started', 'active', 'in_progress')
              AND office_lat IS NOT NULL
              AND office_lng IS NOT NULL
        """
        params = [trip_type]
        if exclude_trip_ids:
            sql += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_trip_ids)
        sql += " ORDER BY updated_at DESC LIMIT 200"

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

        best = None
        for r in rows:
            trip_id, route_no, lat, lng, schedule_time = r
            dist = _distance_km(home_lat, home_lng, float(lat), float(lng))
            if dist <= max_distance_km and (best is None or dist < best["distance_km"]):
                best = {
                    "trip_id": trip_id,
                    "route_no": route_no,
                    "schedule_time": schedule_time,
                    "distance_km": round(dist, 2),
                }

        if not best:
            return jsonify({"success": False, "message": "No nearby trip found"}), 404

        return jsonify({"success": True, "data": best}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@driver_v2_bp.route("/<driver_id>/assign-go-home-trip", methods=["POST"])
def assign_go_home_trip(driver_id: str):
    data = request.get_json(silent=True) or {}
    request_id = data.get("go_home_request_id")
    trip_id = data.get("trip_id")

    if request_id is None or trip_id is None:
        return jsonify({"success": False, "message": "go_home_request_id and trip_id are required"}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, driver_id FROM driver_hometown_requests WHERE id = ?",
            (request_id,),
        )
        req = cur.fetchone()
        if not req:
            return jsonify({"success": False, "message": "Go-home request not found"}), 404
        if str(req[1]) != str(driver_id):
            return jsonify({"success": False, "message": "Request does not belong to driver"}), 400

        cur.execute("SELECT id FROM trips WHERE id = ?", (trip_id,))
        if not cur.fetchone():
            return jsonify({"success": False, "message": "Trip not found"}), 404

        cur.execute(
            "UPDATE trips SET driver_id = ?, status = CASE WHEN status = 'created' THEN 'assigned' ELSE status END, updated_at = datetime('now') WHERE id = ?",
            (driver_id, trip_id),
        )
        cur.execute(
            "UPDATE driver_hometown_requests SET status = 'approved', updated_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        conn.commit()

        return jsonify(
            {
                "success": True,
                "message": "Trip assigned to go-home driver",
                "data": {"driver_id": driver_id, "trip_id": int(trip_id), "go_home_request_id": int(request_id)},
            }
        ), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()
