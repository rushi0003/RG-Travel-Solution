# rg_travel_backend/services/routing_service.py
"""
RG Travel Solution — routing_service.py
======================================

This service handles **Google Maps multi-stop route planning** and **trip KM calculation**
for your commute system.

✅ Project requirements covered:
1) For each cab (group of 4 or 6), plan a route with multiple stops.
2) Supports Pickup/Drop trips (same routing logic; route display differs).
3) Calculates total KM (your required total):
     office -> all waypoints (stops) -> office
4) Returns:
   - ordered stops (if optimize=True)
   - polyline (for drawing route in Flutter)
   - legs distances + total_km
5) Fallback:
   - If Google Maps API fails / key missing, returns local estimate using Haversine.

--------------------------------------------------------------------
Expected config
--------------------------------------------------------------------
- GOOGLE_MAPS_API_KEY should be available in one of these:
    a) rg_travel_backend/config/keys.py -> GOOGLE_MAPS_API_KEY
    b) rg_travel_backend/config/settings.py -> GOOGLE_MAPS_API_KEY
    c) environment variable: GOOGLE_MAPS_API_KEY

--------------------------------------------------------------------
Public APIs (routes can call)
--------------------------------------------------------------------
Core:
- build_multi_stop_route(origin, stops, destination, optimize=True) -> dict
- compute_round_trip_km(origin, stops, destination=None, optimize=True) -> dict
- geocode_address(address) -> dict  (optional helper)
- reverse_geocode(lat, lng) -> dict (optional helper)

Route-ready wrappers:
- api_build_route(payload: dict) -> dict
    payload:
      {
        "origin": {"lat":..,"lng":..},
        "stops": [{"lat":..,"lng":..}, ...],
        "destination": {"lat":..,"lng":..},   # optional (defaults origin)
        "optimize": true
      }

Notes:
- Google Directions API has waypoint limits (standard is limited; ensure your use fits).
- This module is built to be stable and debuggable (clear errors in response).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import os
import math
import requests

# ------------------- API Key Loader (package or flat) -------------------
def _load_google_key() -> str:
    # Try project config modules first
    try:
        from ..config.keys import GOOGLE_MAPS_API_KEY  # type: ignore
        if GOOGLE_MAPS_API_KEY:
            return str(GOOGLE_MAPS_API_KEY)
    except Exception:
        pass

    try:
        from ..config.settings import GOOGLE_MAPS_API_KEY  # type: ignore
        if GOOGLE_MAPS_API_KEY:
            return str(GOOGLE_MAPS_API_KEY)
    except Exception:
        pass

    # Environment fallback
    return str(os.getenv("GOOGLE_MAPS_API_KEY", "")).strip()


GOOGLE_MAPS_API_KEY = _load_google_key()

# ------------------- Google endpoints -------------------
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


# ============================================================
# Core: Build Multi-stop route (Directions API)
# ============================================================

def build_multi_stop_route(
    origin: Tuple[float, float],
    stops: List[Tuple[float, float]],
    destination: Optional[Tuple[float, float]] = None,
    optimize: bool = True,
    timeout_sec: int = 15,
) -> Dict[str, Any]:
    """
    Calls Google Directions API and returns route details for:
      origin -> stops (waypoints) -> destination
    If destination is None, it uses origin (round-trip pattern).

    Returns dict:
    {
      "success": True/False,
      "source": "google"|"fallback",
      "origin": (lat,lng),
      "destination": (lat,lng),
      "requested_stops": [...],
      "ordered_points": [(lat,lng), ...],      # ordered stops if optimize returned
      "waypoint_order": [..],                  # google waypoint order
      "legs": [ { "distance_km":.., "duration_min":.. }, ... ],
      "total_km": float,
      "total_duration_min": int,
      "polyline": "....",
      "raw": {...optional...},
      "error": "...optional..."
    }
    """
    if destination is None:
        destination = origin

    if not stops:
        return {
            "success": True,
            "source": "fallback",
            "origin": origin,
            "destination": destination,
            "requested_stops": [],
            "ordered_points": [],
            "waypoint_order": [],
            "legs": [],
            "total_km": 0.0,
            "total_duration_min": 0,
            "eta_min": 0,
            "polyline": "",
            "warning": "No stops provided.",
        }

    # If no key, fallback
    if not GOOGLE_MAPS_API_KEY:
        return _fallback_route(origin, stops, destination)

    try:
        params = _build_directions_params(origin, stops, destination, optimize)
        resp = requests.get(DIRECTIONS_URL, params=params, timeout=timeout_sec)
        data = resp.json()

        status = data.get("status", "")
        if status != "OK":
            # handle common statuses: REQUEST_DENIED, ZERO_RESULTS, OVER_QUERY_LIMIT
            return _fallback_route(
                origin, stops, destination,
                error=f"Google Directions status={status}, message={data.get('error_message')}"
            )

        route0 = data["routes"][0]
        legs = route0.get("legs", [])
        polyline = (route0.get("overview_polyline") or {}).get("points", "") or ""

        # total km + duration
        leg_summaries: List[Dict[str, Any]] = []
        total_m = 0
        total_sec = 0
        for leg in legs:
            dist_m = int((leg.get("distance") or {}).get("value") or 0)
            dur_s = int((leg.get("duration") or {}).get("value") or 0)
            total_m += dist_m
            total_sec += dur_s
            leg_summaries.append(
                {
                    "distance_km": round(dist_m / 1000.0, 3),
                    "duration_min": int(round(dur_s / 60.0)),
                }
            )

        waypoint_order = route0.get("waypoint_order", []) or []
        ordered_points = _apply_waypoint_order(stops, waypoint_order, optimize=optimize)

        return {
            "success": True,
            "source": "google",
            "origin": origin,
            "destination": destination,
            "requested_stops": stops,
            "ordered_points": ordered_points,
            "waypoint_order": waypoint_order,
            "legs": leg_summaries,
            "total_km": round(total_m / 1000.0, 2),
            "total_duration_min": int(round(total_sec / 60.0)),
            "eta_min": int(round(total_sec / 60.0)),
            "polyline": polyline,
            # keep minimal raw for debugging (safe to remove in production)
            "raw_status": status,
        }

    except Exception as e:
        return _fallback_route(origin, stops, destination, error=f"Directions exception: {e}")


def compute_round_trip_km(
    origin: Tuple[float, float],
    stops: List[Tuple[float, float]],
    destination: Optional[Tuple[float, float]] = None,
    optimize: bool = True,
) -> Dict[str, Any]:
    """
    Your requirement specifically wants total KM:
      office -> all waypoints -> office

    This function returns the route with total_km.
    """
    if destination is None:
        destination = origin
    return build_multi_stop_route(origin, stops, destination, optimize=optimize)


# ============================================================
# Optional: Geocoding helpers (address -> lat/lng)
# ============================================================

def geocode_address(address: str, timeout_sec: int = 12) -> Dict[str, Any]:
    """
    Convert text address to lat/lng using Google Geocoding API.
    """
    address = (address or "").strip()
    if not address:
        return {"success": False, "message": "Address required."}
    if not GOOGLE_MAPS_API_KEY:
        return {"success": False, "message": "GOOGLE_MAPS_API_KEY missing."}

    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"address": address, "key": GOOGLE_MAPS_API_KEY},
            timeout=timeout_sec,
        )
        data = resp.json()
        if data.get("status") != "OK":
            return {"success": False, "message": f"Geocode failed: {data.get('status')}", "error": data.get("error_message")}
        result = data["results"][0]
        loc = result["geometry"]["location"]
        return {
            "success": True,
            "data": {
                "lat": float(loc["lat"]),
                "lng": float(loc["lng"]),
                "formatted_address": result.get("formatted_address", ""),
            },
        }
    except Exception as e:
        return {"success": False, "message": f"Geocode exception: {e}"}


def reverse_geocode(lat: float, lng: float, timeout_sec: int = 12) -> Dict[str, Any]:
    """
    Convert lat/lng to human-readable address.
    """
    if not GOOGLE_MAPS_API_KEY:
        return {"success": False, "message": "GOOGLE_MAPS_API_KEY missing."}

    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"latlng": f"{lat},{lng}", "key": GOOGLE_MAPS_API_KEY},
            timeout=timeout_sec,
        )
        data = resp.json()
        if data.get("status") != "OK":
            return {"success": False, "message": f"Reverse geocode failed: {data.get('status')}", "error": data.get("error_message")}
        result = data["results"][0]
        return {"success": True, "data": {"formatted_address": result.get("formatted_address", "")}}
    except Exception as e:
        return {"success": False, "message": f"Reverse geocode exception: {e}"}


# ============================================================
# Route-ready API wrapper (routes can call directly)
# ============================================================

def api_build_route(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    This function is routes-friendly. Admin/Driver can call:
      POST /api/admin/route/build
      Body:
        {
          "origin": {"lat":..,"lng":..},
          "stops": [{"lat":..,"lng":..}, ...],
          "destination": {"lat":..,"lng":..},   # optional
          "optimize": true
        }
    """
    try:
        origin = payload.get("origin") or {}
        stops = payload.get("stops") or []
        destination = payload.get("destination")

        org = (float(origin["lat"]), float(origin["lng"]))
        stps = [(float(s["lat"]), float(s["lng"])) for s in stops]

        dest_tuple: Optional[Tuple[float, float]] = None
        if destination:
            dest_tuple = (float(destination["lat"]), float(destination["lng"]))

        optimize = bool(payload.get("optimize", True))

        route = build_multi_stop_route(org, stps, dest_tuple, optimize=optimize)
        return {"success": True, "data": route}
    except Exception as e:
        return {"success": False, "message": f"Invalid payload: {e}"}


# ============================================================
# Internal helpers
# ============================================================

def _build_directions_params(
    origin: Tuple[float, float],
    stops: List[Tuple[float, float]],
    destination: Tuple[float, float],
    optimize: bool,
) -> Dict[str, str]:
    """
    Build query params for Directions API.

    waypoints format:
      optimize:true|false| + lat,lng|lat,lng|...
    """
    origin_str = f"{origin[0]},{origin[1]}"
    dest_str = f"{destination[0]},{destination[1]}"

    wp = "|".join([f"{lat},{lng}" for (lat, lng) in stops])
    if optimize:
        wp = "optimize:true|" + wp

    return {
        "origin": origin_str,
        "destination": dest_str,
        "waypoints": wp,
        "key": GOOGLE_MAPS_API_KEY,
    }


def _apply_waypoint_order(
    stops: List[Tuple[float, float]],
    waypoint_order: List[int],
    optimize: bool,
) -> List[Tuple[float, float]]:
    """
    Google returns waypoint_order only when waypoints are present.
    If optimize=True, reorder stops based on waypoint_order.
    """
    if not optimize:
        return stops
    if not waypoint_order:
        return stops
    try:
        return [stops[i] for i in waypoint_order]
    except Exception:
        return stops


def _fallback_route(
    origin: Tuple[float, float],
    stops: List[Tuple[float, float]],
    destination: Tuple[float, float],
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fallback route using local ordering (nearest-chain) + Haversine distance.
    Returns same structure as Google, but without polyline.
    """
    ordered = _nearest_chain_order(origin, stops)

    # Compute round trip: origin -> ordered -> destination
    total_km = 0.0
    legs: List[Dict[str, Any]] = []

    prev = origin
    for pt in ordered:
        d = _haversine_km(prev[0], prev[1], pt[0], pt[1])
        total_km += d
        legs.append({"distance_km": round(d, 3), "duration_min": int(round(d * 2.2))})
        prev = pt

    # last -> destination
    d = _haversine_km(prev[0], prev[1], destination[0], destination[1])
    total_km += d
    legs.append({"distance_km": round(d, 3), "duration_min": int(round(d * 2.2))})

    total_duration = sum(int(x["duration_min"]) for x in legs)

    return {
        "success": True,
        "source": "fallback",
        "origin": origin,
        "destination": destination,
        "requested_stops": stops,
        "ordered_points": ordered,
        "waypoint_order": [],
        "legs": legs,
        "total_km": round(total_km, 2),
        "total_duration_min": int(total_duration),
        "eta_min": int(total_duration),
        "polyline": "",
        "error": error,
        "warning": "Google route not available; returned haversine estimate.",
    }


def _nearest_chain_order(origin: Tuple[float, float], stops: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Simple nearest-neighbor order starting from origin.
    """
    remaining = stops[:]
    ordered: List[Tuple[float, float]] = []
    current = origin
    while remaining:
        nxt = min(remaining, key=lambda p: _haversine_km(current[0], current[1], p[0], p[1]))
        ordered.append(nxt)
        remaining.remove(nxt)
        current = nxt
    return ordered


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
