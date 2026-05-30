# backend/services/route_planning.py
# RG Travel Solution - Route Planning with Google Maps Directions API
# STEP 7: Multi-stop route optimization and distance/duration calculation

import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests library not available, using fallback mode only")

# Import haversine from geo_clustering for fallback
try:
    from services.geo_clustering import haversine_distance
except ImportError:
    # Fallback haversine if geo_clustering not available
    import math
    def haversine_distance(lat1, lng1, lat2, lng2):
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return round(R * c, 3)


# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
ROUTE_PLANNING_ENABLED = bool(GOOGLE_MAPS_API_KEY) and REQUESTS_AVAILABLE
ROUTE_OPTIMIZATION_TIMEOUT_SECONDS = 10
FALLBACK_TO_SIMPLE_ESTIMATION = True

logger = logging.getLogger(__name__)


def get_optimized_route(
    office_lat: float,
    office_lng: float,
    waypoints: List[Tuple[float, float]],
    return_to_office: bool = True,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get optimized multi-stop route from Google Maps Directions API.
    
    Algorithm:
        1. Call Google Maps Directions API with waypoint optimization
        2. Parse response: polyline, distance, duration, optimized order
        3. If API fails, fallback to simple Haversine estimation
    
    Args:
        office_lat, office_lng: Starting point (office coordinates)
        waypoints: List of employee coordinates [(lat, lng), ...]
        return_to_office: If True, round trip; else end at last waypoint
        api_key: Google Maps API key (optional, uses env var if not provided)
    
    Returns:
        {
            "success": True,
            "data": {
                "optimized_waypoint_order": [2, 0, 1, 3],
                "total_distance_meters": 15420,
                "total_distance_km": 15.42,
                "total_duration_seconds": 1820,
                "total_duration_minutes": 30,
                "polyline": "encoded_polyline_string",
                "legs": [
                    {
                        "start_lat": 19.076,
                        "start_lng": 72.877,
                        "end_lat": 19.1,
                        "end_lng": 72.9,
                        "distance_meters": 5420,
                        "duration_seconds": 780
                    },
                    ...
                ]
            }
        }
    
    Example:
        waypoints = [(19.1, 72.9), (19.2, 72.8), (19.15, 72.85)]
        result = get_optimized_route(19.0, 72.9, waypoints)
        → Optimized route with reordered waypoints
    """
    if not waypoints:
        return {
            "success": False,
            "message": "No waypoints provided",
            "data": {}
        }
    
    # Check if API is available
    if not ROUTE_PLANNING_ENABLED or not REQUESTS_AVAILABLE:
        if FALLBACK_TO_SIMPLE_ESTIMATION:
            logger.info("Google Maps API not available, using fallback estimation")
            return _fallback_route_estimation(office_lat, office_lng, waypoints, return_to_office)
        else:
            return {
                "success": False,
                "message": "Route planning not enabled (missing API key or requests library)",
                "data": {}
            }
    
    try:
        # Call Google Maps API
        result = _call_google_maps_api(
            office_lat, office_lng, waypoints, return_to_office, api_key
        )
        
        if result["success"]:
            return result
        
        # API failed, use fallback if enabled
        if FALLBACK_TO_SIMPLE_ESTIMATION:
            logger.warning(f"Google Maps API failed: {result.get('message')}, using fallback")
            return _fallback_route_estimation(office_lat, office_lng, waypoints, return_to_office)
        
        return result
        
    except Exception as e:
        logger.error(f"Route planning error: {e}")
        
        if FALLBACK_TO_SIMPLE_ESTIMATION:
            return _fallback_route_estimation(office_lat, office_lng, waypoints, return_to_office)
        
        return {
            "success": False,
            "message": f"Route planning failed: {str(e)}",
            "data": {}
        }


def _call_google_maps_api(
    office_lat: float,
    office_lng: float,
    waypoints: List[Tuple[float, float]],
    return_to_office: bool,
    api_key: Optional[str]
) -> Dict[str, Any]:
    """Call Google Maps Directions API with waypoint optimization."""
    
    # Build waypoints string with optimization flag
    waypoint_coords = [f"{lat},{lng}" for lat, lng in waypoints]
    waypoint_str = "optimize:true|" + "|".join(waypoint_coords)
    
    # Determine destination
    if return_to_office:
        destination = f"{office_lat},{office_lng}"
    else:
        # End at last waypoint (remove it from waypoints)
        destination = waypoint_coords[-1]
        waypoint_str = "optimize:true|" + "|".join(waypoint_coords[:-1])
    
    # API request
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{office_lat},{office_lng}",
        "destination": destination,
        "waypoints": waypoint_str,
        "mode": "driving",
        "departure_time": "now",  # For traffic-aware routing
        "key": api_key or GOOGLE_MAPS_API_KEY
    }
    
    response = requests.get(url, params=params, timeout=ROUTE_OPTIMIZATION_TIMEOUT_SECONDS)
    data = response.json()
    
    # Check API response status
    if data.get("status") != "OK":
        error_msg = data.get("error_message", data.get("status", "Unknown error"))
        return {
            "success": False,
            "message": f"Google Maps API error: {error_msg}",
            "data": {}
        }
    
    # Parse route data
    route = data["routes"][0]
    legs = route["legs"]
    waypoint_order = route.get("waypoint_order", list(range(len(waypoints))))
    
    # Calculate totals
    total_distance_meters = sum(leg["distance"]["value"] for leg in legs)
    total_duration_seconds = sum(leg["duration"]["value"] for leg in legs)
    
    # Parse legs
    parsed_legs = []
    for leg in legs:
        parsed_legs.append({
            "start_lat": leg["start_location"]["lat"],
            "start_lng": leg["start_location"]["lng"],
            "end_lat": leg["end_location"]["lat"],
            "end_lng": leg["end_location"]["lng"],
            "distance_meters": leg["distance"]["value"],
            "duration_seconds": leg["duration"]["value"],
            "distance_text": leg["distance"]["text"],
            "duration_text": leg["duration"]["text"]
        })
    
    return {
        "success": True,
        "data": {
            "optimized_waypoint_order": waypoint_order,
            "total_distance_meters": total_distance_meters,
            "total_distance_km": round(total_distance_meters / 1000, 2),
            "total_duration_seconds": total_duration_seconds,
            "total_duration_minutes": round(total_duration_seconds / 60),
            "polyline": route["overview_polyline"]["points"],
            "legs": parsed_legs,
            "source": "google_maps_api"
        }
    }


def _fallback_route_estimation(
    office_lat: float,
    office_lng: float,
    waypoints: List[Tuple[float, float]],
    return_to_office: bool
) -> Dict[str, Any]:
    """
    Simple distance estimation without Google Maps API.
    Uses Haversine formula for straight-line distances.
    
    Assumes:
        - Average speed: 30 km/h in city traffic
        - No waypoint optimization (uses given order)
    """
    total_distance_km = 0
    legs = []
    
    # Start from office
    prev_lat, prev_lng = office_lat, office_lng
    
    # Go through each waypoint
    for lat, lng in waypoints:
        dist_km = haversine_distance(prev_lat, prev_lng, lat, lng)
        total_distance_km += dist_km
        
        # Assume 30 km/h average speed (2 minutes per km)
        duration_seconds = int(dist_km * 120)
        
        legs.append({
            "start_lat": prev_lat,
            "start_lng": prev_lng,
            "end_lat": lat,
            "end_lng": lng,
            "distance_meters": int(dist_km * 1000),
            "duration_seconds": duration_seconds,
            "distance_text": f"{dist_km:.1f} km",
            "duration_text": f"{duration_seconds // 60} mins"
        })
        
        prev_lat, prev_lng = lat, lng
    
    # Return to office if required
    if return_to_office:
        dist_km = haversine_distance(prev_lat, prev_lng, office_lat, office_lng)
        total_distance_km += dist_km
        duration_seconds = int(dist_km * 120)
        
        legs.append({
            "start_lat": prev_lat,
            "start_lng": prev_lng,
            "end_lat": office_lat,
            "end_lng": office_lng,
            "distance_meters": int(dist_km * 1000),
            "duration_seconds": duration_seconds,
            "distance_text": f"{dist_km:.1f} km",
            "duration_text": f"{duration_seconds // 60} mins"
        })
    
    total_duration_seconds = sum(leg["duration_seconds"] for leg in legs)
    
    return {
        "success": True,
        "data": {
            "optimized_waypoint_order": list(range(len(waypoints))),  # No optimization
            "total_distance_meters": int(total_distance_km * 1000),
            "total_distance_km": round(total_distance_km, 2),
            "total_duration_seconds": total_duration_seconds,
            "total_duration_minutes": round(total_duration_seconds / 60),
            "polyline": "",  # No polyline in fallback mode
            "legs": legs,
            "source": "fallback_estimation"
        }
    }


def calculate_stop_etas(
    scheduled_time: str,
    legs: List[Dict[str, Any]]
) -> List[str]:
    """
    Calculate estimated arrival time at each stop.
    
    Args:
        scheduled_time: Trip start time (ISO format or HH:MM)
        legs: List of route legs with duration_seconds
    
    Returns:
        List of ISO timestamp strings for each stop
    
    Example:
        scheduled_time = "09:00"
        legs = [{"duration_seconds": 600}, {"duration_seconds": 480}, ...]
        → ["2026-02-17T09:10:00", "2026-02-17T09:18:00", ...]
    """
    # Parse scheduled time
    try:
        if "T" in scheduled_time:
            # ISO format
            base_time = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
        else:
            # HH:MM format - use today's date
            today = datetime.now().date()
            hour, minute = map(int, scheduled_time.split(":"))
            base_time = datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)
    except Exception as e:
        logger.error(f"Error parsing scheduled_time '{scheduled_time}': {e}")
        # Fallback: use current time
        base_time = datetime.now()
    
    # Calculate ETAs
    etas = []
    cumulative_duration = 0
    
    for leg in legs:
        cumulative_duration += leg.get("duration_seconds", 0)
        eta = base_time + timedelta(seconds=cumulative_duration)
        etas.append(eta.isoformat())
    
    return etas
