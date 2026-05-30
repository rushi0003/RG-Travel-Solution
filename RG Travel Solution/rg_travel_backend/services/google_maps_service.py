import os
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_directions_polyline_and_distance(origin: Dict[str, float], waypoints: List[Dict[str, float]], destination: Dict[str, float], mode: str = 'driving') -> Dict[str, Any]:
    """
    Call Google Directions API to get overview polyline and total distance in KM.

    origin/destination: {"lat": float, "lng": float}
    waypoints: list of {"lat": float, "lng": float}

    Returns: {"success": bool, "polyline": str, "distance_km": float, "raw": dict}
    """
    api_key = os.environ.get("RG_GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"success": False, "message": "No Google Maps API key configured"}

    try:
        origin_s = f"{origin['lat']},{origin['lng']}"
        dest_s = f"{destination['lat']},{destination['lng']}"

        wp_parts = []
        for w in waypoints:
            wp_parts.append(f"{w['lat']},{w['lng']}")

        params = {
            "origin": origin_s,
            "destination": dest_s,
            "key": api_key,
            "mode": mode,
            "alternatives": "false",
        }

        if wp_parts:
            # Use waypoints with optimize:false since sequence matters (employees order)
            params["waypoints"] = "|".join(wp_parts)

        url = "https://maps.googleapis.com/maps/api/directions/json"
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "OK":
            logger.warning(f"Directions API returned non-OK: {data.get('status')} - {data.get('error_message')}")
            return {"success": False, "message": f"Directions API: {data.get('status')}", "raw": data}

        route = data["routes"][0]
        overview_polyline = route.get("overview_polyline", {}).get("points", "")

        # Sum all legs distances
        total_m = 0
        for leg in route.get("legs", []):
            total_m += leg.get("distance", {}).get("value", 0)

        distance_km = float(total_m) / 1000.0

        return {"success": True, "polyline": overview_polyline, "distance_km": distance_km, "raw": data}

    except Exception as e:
        logger.exception(f"Error fetching directions: {e}")
        return {"success": False, "message": str(e)}
