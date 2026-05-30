"""
Verify Group Creation endpoint against running backend.

Run:
  python rg_travel_backend/tests/verify_group_creation.py
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

import requests


BASE_URL = "http://127.0.0.1:5000"


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    r = requests.get(f"{BASE_URL}{path}", params=params, timeout=20)
    return {"status": r.status_code, "json": r.json()}


def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{BASE_URL}{path}", json=body, timeout=30)
    return {"status": r.status_code, "json": r.json()}


def _pick_working_slot(trip_type: str = "pickup") -> str:
    slots_res = _get("/api/admin/time-slots", {"trip_type": trip_type})
    _require(slots_res["status"] == 200, "time-slots endpoint failed")
    _require(slots_res["json"].get("success") is True, "time-slots success=false")
    slots = (slots_res["json"].get("data") or {}).get("slots") or []
    _require(len(slots) > 0, "No time slots available")

    for slot in slots:
        emp_res = _get(
            "/api/admin/available-employees",
            {"trip_type": trip_type, "time_slot": slot},
        )
        if emp_res["status"] != 200 or emp_res["json"].get("success") is not True:
            continue
        employees = (emp_res["json"].get("data") or {}).get("employees") or []
        if employees:
            return str(slot)

    raise AssertionError(f"No slot has available employees for trip_type={trip_type}")


def main() -> int:
    print("=== verify_group_creation ===")

    # 1) Health check
    health = _get("/api/health")
    _require(health["status"] == 200, "Backend health endpoint is not reachable")
    print("health: OK")

    # 2) Discover a usable trip_type + slot and employees
    selected_trip_type = None
    selected_time = None
    for trip_type in ("pickup", "drop"):
        try:
            selected_time = _pick_working_slot(trip_type)
            selected_trip_type = trip_type
            break
        except Exception:
            continue
    _require(selected_trip_type is not None and selected_time is not None, "No slot has available employees")
    trip_type = str(selected_trip_type)
    print(f"time slot: {selected_time}")
    print(f"trip_type: {trip_type}")

    emp_res = _get(
        "/api/admin/available-employees",
        {"trip_type": trip_type, "time_slot": selected_time},
    )
    _require(emp_res["status"] == 200, "available-employees endpoint failed")
    _require(emp_res["json"].get("success") is True, "available-employees success=false")
    employees: List[Dict[str, Any]] = (emp_res["json"].get("data") or {}).get("employees") or []
    _require(len(employees) > 0, "No available employees found")
    employee_ids = [int(e["id"]) for e in employees[: min(6, len(employees))]]
    print(f"selected employees: {employee_ids}")

    # 3) Discover vehicle/driver list
    veh_res = _get(
        "/api/admin/available-vehicles",
        {"vehicle_type": "both", "trip_type": trip_type, "time_slot": selected_time},
    )
    _require(veh_res["status"] == 200, "available-vehicles endpoint failed")
    _require(veh_res["json"].get("success") is True, "available-vehicles success=false")
    vehicles: List[Dict[str, Any]] = (veh_res["json"].get("data") or {}).get("vehicles") or []
    _require(len(vehicles) > 0, "No available vehicles found")

    driver_ids = []
    for v in vehicles:
        drv = v.get("driver") or {}
        if drv.get("driver_id"):
            # createGroups contract currently sends integer IDs in Flutter.
            try:
                driver_ids.append(int(drv["driver_id"]))
            except Exception:
                # non-int driver ids are accepted by backend too; skip conversion if needed
                pass
    print(f"selected driver ids: {driver_ids}")

    # 4) createGroups (must be 200 + success true)
    create_payload = {
        "admin_id": "admin_001",
        "trip_type": trip_type,
        "selected_time": selected_time,
        "vehicle_types": [6, 4],
        "driver_ids": driver_ids,
        "employee_ids": employee_ids,
        "vehicle_priority_enabled": True,
        "office_lat": 19.0760,
        "office_lng": 72.8777,
    }
    create_res = _post("/api/grouping/create", create_payload)
    _require(create_res["status"] == 200, f"/api/grouping/create status={create_res['status']}")
    _require(create_res["json"].get("success") is True, "grouping/create success=false")
    data = create_res["json"].get("data") or {}
    print("grouping/create response:")
    print(json.dumps(data, indent=2))
    print("generated route_no:", data.get("route_no") or data.get("routeNo"))

    # 5) Persist via /api/trips/create so admin trips can be verified
    groups = data.get("groups") or []
    _require(len(groups) > 0, "No groups generated by createGroups")
    save_groups = []
    for g in groups:
        members = g.get("members") or g.get("employees") or []
        save_groups.append(
            {
                "capacity": g.get("capacity", 4),
                "employee_ids": [m["id"] for m in members],
            }
        )

    trips_create = _post(
        "/api/trips/create",
        {
            "trip_type": trip_type,
            "time_slot": selected_time,
            "groups": save_groups,
            "admin_id": "admin_001",
        },
    )
    _require(trips_create["status"] in (200, 201), "/api/trips/create failed")
    _require(trips_create["json"].get("success") is True, "/api/trips/create success=false")

    # 6) Verify via GET /api/admin/trips
    trips_res = _get("/api/admin/trips")
    _require(trips_res["status"] == 200, "/api/admin/trips failed")
    _require(trips_res["json"].get("success") is True, "/api/admin/trips success=false")
    trips_data = trips_res["json"].get("data") or []
    _require(isinstance(trips_data, list) and len(trips_data) > 0, "No trips visible in /api/admin/trips")
    print(f"/api/admin/trips count: {len(trips_data)}")

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESULT: FAIL - {exc}")
        raise SystemExit(1)
