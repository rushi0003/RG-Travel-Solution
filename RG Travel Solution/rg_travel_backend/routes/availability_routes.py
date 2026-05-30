# backend/routes/availability_routes.py
# RG Travel Solution - Availability API Routes
# STEP 3: Cab and driver availability scanning endpoints

from flask import Blueprint, request, jsonify
from services.availability_service import scan_cab_availability

availability_bp = Blueprint("availability", __name__, url_prefix="/api/admin/availability")


@availability_bp.route("/scan", methods=["GET"])
def get_availability():
    """
    GET /api/admin/availability/scan
    
    Scan available cabs and approved drivers.
    
    Query Parameters:
        - vehicle_type (optional): "4" or "6" to filter by seating capacity
        - include_offline (optional): "true" to include offline drivers (default: false)
    
    Returns:
        200: {
            "success": true,
            "data": {
                "available4Count": int,
                "available6Count": int,
                "totalAvailable": int,
                "drivers": [...],
                "unavailable_drivers": [...],
                "summary": {...}
            }
        }
        
        400: {
            "success": false,
            "message": "No available cabs found",
            "data": {
                "reasons": [...],
                "suggestions": [...]
            }
        }
    """
    vehicle_type = request.args.get("vehicle_type")  # "4" or "6"
    include_offline_str = request.args.get("include_offline", "false").lower()
    include_offline = include_offline_str in ("true", "1", "yes")
    
    result = scan_cab_availability(
        vehicle_type=vehicle_type,
        include_offline=include_offline
    )
    
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code
