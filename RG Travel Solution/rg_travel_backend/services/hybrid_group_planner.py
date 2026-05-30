from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


class HybridProviderUnavailable(RuntimeError):
    """Raised when mandatory road provider cannot return distance in strict mode."""


class HybridDistance:
    """
    Hybrid distance scorer:
    1) Base score from haversine (always available)
    2) Optional road distance from OSRM/ORS with short timeout
    3) If road API fails, silently fallback to haversine
    """

    def __init__(self, timeout_sec: Optional[float] = None, strict_required: bool = True) -> None:
        if timeout_sec is None:
            timeout_sec = float(os.getenv("HYBRID_TIMEOUT_SEC", "2.5"))
        self.timeout_sec = timeout_sec
        self.strict_required = strict_required
        configured_provider = str(os.getenv("HYBRID_ROUTE_PROVIDER", "")).strip().lower()
        # Keep strict hybrid behavior, but avoid hard failure when env var is missing.
        # Fallback order: explicit provider -> ORS when key exists -> OSRM default.
        self.provider = configured_provider or ("ors" if str(os.getenv("ORS_API_KEY", "")).strip() else "osrm")
        # Prefer explicit env URL; otherwise prefer local OSRM and keep public URL as backup.
        osrm_env = str(os.getenv("OSRM_TABLE_URL", "")).strip()
        self.osrm_url = osrm_env or "http://127.0.0.1:5001/table/v1/driving"
        self.osrm_fallback_url = str(
            os.getenv("OSRM_FALLBACK_TABLE_URL", "http://router.project-osrm.org/table/v1/driving")
        ).strip()
        self.ors_url = str(
            os.getenv("ORS_MATRIX_URL", "https://api.openrouteservice.org/v2/matrix/driving-car")
        ).strip()
        self.ors_api_key = str(os.getenv("ORS_API_KEY", "")).strip()
        self._cache: Dict[Tuple[float, float, float, float], float] = {}
        self.degraded_edges: int = 0

        if self.provider not in ("osrm", "ors"):
            raise ValueError(
                "HYBRID_ROUTE_PROVIDER must be 'osrm' or 'ors' for mandatory hybrid grouping."
            )
        if self.provider == "ors" and not self.ors_api_key:
            raise ValueError("ORS_API_KEY is required when HYBRID_ROUTE_PROVIDER='ors'.")

    def km(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        cache_key = (round(a[0], 6), round(a[1], 6), round(b[0], 6), round(b[1], 6))
        if cache_key in self._cache:
            return self._cache[cache_key]

        h = haversine_km(a[0], a[1], b[0], b[1])
        road = self._road_km(a, b)
        if road is None:
            self.degraded_edges += 1
            if self.strict_required:
                raise HybridProviderUnavailable(
                    f"Hybrid road distance unavailable for provider '{self.provider}'."
                )
            value = round(h, 3)
            self._cache[cache_key] = value
            return value
        # Stable blend: mostly road distance, small haversine tie stabilizer.
        value = round((road * 0.85) + (h * 0.15), 3)
        self._cache[cache_key] = value
        return value

    def _road_km(self, a: Tuple[float, float], b: Tuple[float, float]) -> Optional[float]:
        try:
            if self.provider == "osrm":
                return self._road_km_osrm(a, b)
            if self.provider == "ors":
                return self._road_km_ors(a, b)
            return None
        except Exception:
            return None

    def _road_km_osrm(self, a: Tuple[float, float], b: Tuple[float, float]) -> Optional[float]:
        # OSRM expects lon,lat order.
        coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"
        url_candidates = [u for u in [self.osrm_url, self.osrm_fallback_url] if str(u or "").strip()]
        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_urls: List[str] = []
        for u in url_candidates:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)

        for base_url in unique_urls:
            url = f"{base_url}/{coords}"
            for _ in range(3):
                try:
                    resp = requests.get(
                        url,
                        params={"sources": "0", "destinations": "1", "annotations": "distance"},
                        timeout=self.timeout_sec,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    d_m = (((data.get("distances") or [[None]])[0] or [None])[0])
                    if d_m is None:
                        continue
                    return float(d_m) / 1000.0
                except Exception:
                    continue
        return None

    def _road_km_ors(self, a: Tuple[float, float], b: Tuple[float, float]) -> Optional[float]:
        if not self.ors_api_key:
            return None
        headers = {"Authorization": self.ors_api_key, "Content-Type": "application/json"}
        payload = {
            "locations": [[a[1], a[0]], [b[1], b[0]]],  # lon,lat
            "sources": [0],
            "destinations": [1],
            "metrics": ["distance"],
            "units": "km",
        }
        for _ in range(2):
            try:
                resp = requests.post(self.ors_url, headers=headers, json=payload, timeout=self.timeout_sec)
                resp.raise_for_status()
                data = resp.json()
                d_km = (((data.get("distances") or [[None]])[0] or [None])[0])
                if d_km is None:
                    continue
                return float(d_km)
            except Exception:
                continue
        return None


@dataclass
class EmployeeNode:
    id: int
    name: str
    mobile: str
    address: str
    lat: float
    lng: float


@dataclass
class VehicleNode:
    driver_id: str
    driver_name: str
    vehicle_no: str
    vehicle_type: int  # 4 or 6
    go_home_approved: bool
    home_lat: float
    home_lng: float


def _nearest_chain(
    points: Sequence[EmployeeNode],
    start: Tuple[float, float],
    dist: HybridDistance,
) -> List[EmployeeNode]:
    rem = list(points)
    out: List[EmployeeNode] = []
    cur = start
    while rem:
        nxt = min(rem, key=lambda p: (dist.km(cur, (p.lat, p.lng)), p.id))
        out.append(nxt)
        rem.remove(nxt)
        cur = (nxt.lat, nxt.lng)
    return out


def _round_trip_km(
    office: Tuple[float, float],
    ordered_members: Sequence[EmployeeNode],
    dist: HybridDistance,
) -> float:
    if not ordered_members:
        return 0.0

    total = 0.0
    prev = office
    for member in ordered_members:
        cur = (member.lat, member.lng)
        total += dist.km(prev, cur)
        prev = cur
    total += dist.km(prev, office)
    return total


def _vehicle_priority_key(v: VehicleNode, prioritize_6: bool) -> Tuple[int, int, int, str]:
    # 1) approved go-home first
    # 2) when both selected, 6-seater first
    # 3) larger capacity first
    return (
        0 if v.go_home_approved else 1,
        0 if (prioritize_6 and v.vehicle_type == 6) else 1,
        -int(v.vehicle_type),
        str(v.driver_id),
    )


def _nearest_employee_distance_km(
    vehicle: VehicleNode,
    employees: Sequence[EmployeeNode],
    dist: HybridDistance,
    office: Tuple[float, float],
) -> float:
    if not employees:
        return float("inf")
    if vehicle.go_home_approved and vehicle.home_lat != 0.0 and vehicle.home_lng != 0.0:
        origin = (vehicle.home_lat, vehicle.home_lng)
    else:
        origin = office
    return min(dist.km(origin, (e.lat, e.lng)) for e in employees)


def _pick_next_vehicle(
    vehicles: Sequence[VehicleNode],
    employees: Sequence[EmployeeNode],
    dist: HybridDistance,
    office: Tuple[float, float],
    prioritize_6: bool,
) -> VehicleNode:
    """
    Selection policy:
    1) First priority: go-home approved vehicles.
    2) Among go-home vehicles, assign the one nearest to remaining employees first.
    3) Second priority (mixed types): 6-seater before 4-seater.
    """
    employees_left = len(employees)
    valid_caps = [int(v.vehicle_type) for v in vehicles if int(v.vehicle_type) in (4, 6)]
    min_cap = min(valid_caps) if valid_caps else 4
    full_fit = [v for v in vehicles if int(v.vehicle_type) in (4, 6) and int(v.vehicle_type) <= employees_left]

    # Capacity-first: keep assigning full groups when possible.
    # Partial group is allowed only when remaining employees are fewer than
    # the minimum available capacity (i.e., final group).
    if full_fit:
        pool = full_fit
    else:
        pool = list(vehicles)

    # Vehicle type priority applies inside chosen pool.
    # When both types are available and at least one 6-seater can be fully filled,
    # keep 6-seater preference.
    if prioritize_6 and employees_left >= 6:
        has_6_full = any(int(v.vehicle_type) == 6 for v in pool)
        if has_6_full:
            pool = [v for v in pool if int(v.vehicle_type) == 6]

    final_partial = employees_left < min_cap

    return min(
        pool,
        key=lambda v: (
            int(v.vehicle_type) if final_partial else 0,
            _nearest_employee_distance_km(v, employees, dist, office),
            0 if (prioritize_6 and v.vehicle_type == 6) else 1,
            -int(v.vehicle_type),
            str(v.driver_id),
        ),
    )


def plan_groups_hybrid(
    employees: List[EmployeeNode],
    vehicles: List[VehicleNode],
    office: Tuple[float, float],
    prioritize_6_when_mixed: bool = True,
    strict_hybrid: bool = True,
    vehicle_batch_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Rule-based planner used for auto-grouping preview.
    - Each selected vehicle gets one group up to its capacity.
    - Vehicle type decides max size (4/6) for each group.
    - Go-home approved vehicles are processed first and seeded near driver home.
    - When both 4/6 are selected, 6-seaters are prioritized after go-home.
    - If vehicles are more than employees, extra vehicles remain unassigned.
    - If employees are more than vehicles, extra employees remain unassigned.
    - Partial group is allowed only for the final usable vehicle (example: 2x4, 6 employees => 4 + 2).
    """
    def _build_plan(strict_mode: bool) -> Dict[str, Any]:
        dist = HybridDistance(strict_required=strict_mode)
        unassigned_emps = list(employees)
        groups: List[Dict[str, Any]] = []
        unassigned_vehicles: List[Dict[str, Any]] = []

        def _append_unassigned_vehicle(vehicle: VehicleNode, reason: str, eligible: bool) -> None:
            unassigned_vehicles.append(
                {
                    "driver_id": vehicle.driver_id,
                    "driver_name": vehicle.driver_name,
                    "vehicle_no": vehicle.vehicle_no,
                    "vehicle_type": int(vehicle.vehicle_type),
                    "reason": reason,
                    "eligible_for_next_group_creation": bool(eligible),
                }
            )

        types = {int(v.vehicle_type) for v in vehicles if int(v.vehicle_type) in (4, 6)}
        prioritize_6 = prioritize_6_when_mixed and (4 in types and 6 in types)
        ordered_vehicles = sorted(vehicles, key=lambda v: _vehicle_priority_key(v, prioritize_6))
        batch_size = int(vehicle_batch_size or 0)
        if batch_size <= 0:
            vehicle_batches: List[List[VehicleNode]] = [ordered_vehicles]
        else:
            vehicle_batches = [
                ordered_vehicles[i : i + batch_size] for i in range(0, len(ordered_vehicles), batch_size)
            ]

        for batch in vehicle_batches:
            remaining_batch = list(batch)
            while remaining_batch:
                vehicle = _pick_next_vehicle(
                    vehicles=remaining_batch,
                    employees=unassigned_emps,
                    dist=dist,
                    office=office,
                    prioritize_6=prioritize_6,
                )
                remaining_batch = [v for v in remaining_batch if v.driver_id != vehicle.driver_id]
                cap = int(vehicle.vehicle_type)
                if cap not in (4, 6):
                    _append_unassigned_vehicle(
                        vehicle,
                        reason="unsupported_vehicle_type",
                        eligible=False,
                    )
                    continue
                employees_left = len(unassigned_emps)
                if employees_left <= 0:
                    _append_unassigned_vehicle(
                        vehicle,
                        reason="no_employees_left",
                        eligible=True,
                    )
                    continue

                # Sequential allocation: fill current vehicle up to capacity.
                # If final remainder is smaller than capacity, create partial group.
                target_size = min(cap, employees_left)

                if vehicle.go_home_approved and vehicle.home_lat != 0.0 and vehicle.home_lng != 0.0:
                    seed_origin = (vehicle.home_lat, vehicle.home_lng)
                else:
                    seed_origin = office

                # Seed nearest to origin.
                seed = min(unassigned_emps, key=lambda e: (dist.km(seed_origin, (e.lat, e.lng)), e.id))
                unassigned_emps.remove(seed)

                # Fill remaining nearest to seed.
                neighbors = sorted(
                    unassigned_emps,
                    key=lambda e: (dist.km((seed.lat, seed.lng), (e.lat, e.lng)), e.id),
                )[: max(0, target_size - 1)]
                chosen_ids = {seed.id, *[n.id for n in neighbors]}
                group_raw = [seed] + neighbors
                unassigned_emps = [e for e in unassigned_emps if e.id not in chosen_ids]

                # Final stop order.
                ordered_members = _nearest_chain(group_raw, seed_origin, dist)
                centroid_lat = sum(x.lat for x in ordered_members) / len(ordered_members)
                centroid_lng = sum(x.lng for x in ordered_members) / len(ordered_members)
                anchor = seed_origin
                anchor_km = dist.km(anchor, (centroid_lat, centroid_lng))
                route_km = _round_trip_km(office=office, ordered_members=ordered_members, dist=dist)

                groups.append(
                    {
                        "driver_id": vehicle.driver_id,
                        "driver_name": vehicle.driver_name,
                        "vehicle_no": vehicle.vehicle_no,
                        "vehicle_type": cap,
                        "go_home_approved": vehicle.go_home_approved,
                        "group_size": len(ordered_members),
                        "anchor_distance_km": round(anchor_km, 2),
                        "route_distance_km": round(route_km, 2),
                        "distance_km_estimate": round(route_km, 2),
                        "members": [
                            {
                                "id": m.id,
                                "name": m.name,
                                "mobile": m.mobile,
                                "address": m.address,
                                "lat": m.lat,
                                "lng": m.lng,
                            }
                            for m in ordered_members
                        ],
                    }
                )

        return {
            "groups": groups,
            "unassigned_employees": [
                {
                    "id": e.id,
                    "name": e.name,
                    "mobile": e.mobile,
                    "address": e.address,
                    "lat": e.lat,
                    "lng": e.lng,
                    "reason": "insufficient_vehicles_or_capacity",
                    "eligible_for_next_trip": True,
                }
                for e in unassigned_emps
            ],
            "unassigned_vehicles": unassigned_vehicles,
            "hybrid_provider": dist.provider,
            "hybrid_strict": strict_mode,
            "hybrid_degraded_edges": int(getattr(dist, "degraded_edges", 0)),
            "vehicle_batch_size": batch_size if batch_size > 0 else None,
            "vehicle_batches": len(vehicle_batches),
            "hybrid_fallback_used": False,
            "hybrid_fallback_reason": None,
        }

    try:
        return _build_plan(strict_hybrid)
    except HybridProviderUnavailable as exc:
        if not strict_hybrid:
            raise
        degraded = _build_plan(False)
        degraded["hybrid_fallback_used"] = True
        degraded["hybrid_fallback_reason"] = str(exc)
        return degraded


def probe_hybrid_provider(timeout_sec: float = 1.2) -> Dict[str, Any]:
    """
    Basic runtime probe for mandatory hybrid provider readiness.
    Returns a diagnostics payload safe to expose in health endpoints.
    """
    try:
        dist = HybridDistance(timeout_sec=timeout_sec, strict_required=True)
    except Exception as exc:
        return {
            "ready": False,
            "provider": str(os.getenv("HYBRID_ROUTE_PROVIDER", "")).strip().lower(),
            "error": str(exc),
        }

    # Short Mumbai sample segment for probe.
    a = (19.0760, 72.8777)
    b = (19.0820, 72.8850)
    try:
        km = dist.km(a, b)
        if int(getattr(dist, "degraded_edges", 0)) > 0:
            return {
                "ready": False,
                "provider": dist.provider,
                "timeout_sec": timeout_sec,
                "error": "Road provider degraded to haversine; strict hybrid requires road distance.",
            }
        return {
            "ready": True,
            "provider": dist.provider,
            "sample_km": km,
            "timeout_sec": timeout_sec,
        }
    except Exception as exc:
        return {
            "ready": False,
            "provider": dist.provider,
            "timeout_sec": timeout_sec,
            "error": str(exc),
        }
