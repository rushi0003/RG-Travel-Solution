"""
Verify pre-assigned start-lock flow end-to-end against running backend.

Run:
  python rg_travel_backend/tests/verify_preassign_start_gate_flow.py
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests


BASE_URL = os.getenv("RG_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def _req(method: str, path: str, **kwargs: Any) -> requests.Response:
    return requests.request(method, f"{BASE_URL}{path}", timeout=10, **kwargs)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _pick_preassigned_trip() -> Optional[Dict[str, Any]]:
    res = _req("GET", "/api/admin/trips/live")
    _require(res.status_code == 200, f"admin live failed: {res.status_code}")
    payload = res.json()
    trips = payload.get("data") or []
    _require(isinstance(trips, list), "admin live payload is not list")

    for t in trips:
        if bool(t.get("is_preassigned")) and not bool(t.get("can_start_now")):
            return t
    return None


def _assert_gate_keys(obj: Dict[str, Any], label: str) -> None:
    required = [
        "is_preassigned",
        "can_start_now",
        "start_allowed_after",
        "seconds_until_start",
        "server_now",
    ]
    for k in required:
        _require(k in obj, f"{label} missing key: {k}")


def main() -> int:
    print("=== verify_preassign_start_gate_flow ===")
    trip = _pick_preassigned_trip()
    _require(trip is not None, "No pre-assigned trip found in /api/admin/trips/live")
    trip_id = int(trip["id"])
    driver_id = str(trip.get("driver_id") or "")
    _require(driver_id != "", "pre-assigned trip missing driver_id")
    _assert_gate_keys(trip, "admin.live.trip")
    _require(int(trip.get("seconds_until_start") or 0) > 0, "seconds_until_start should be > 0")
    print(f"Picked pre-assigned trip: id={trip_id}, driver_id={driver_id}")

    # Driver assigned-trip should carry gate metadata for the same trip.
    assigned = _req("GET", f"/api/driver/{driver_id}/assigned-trip")
    _require(assigned.status_code == 200, f"driver assigned-trip failed: {assigned.status_code}")
    assigned_data = (assigned.json() or {}).get("data") or {}
    _require(int(assigned_data.get("id") or 0) == trip_id, "assigned-trip id mismatch")
    _assert_gate_keys(assigned_data, "driver.assigned_trip")
    _require(bool(assigned_data.get("is_preassigned")), "assigned-trip is_preassigned should be true")
    _require(not bool(assigned_data.get("can_start_now")), "assigned-trip can_start_now should be false")
    print("Driver assigned-trip metadata: PASS")

    # Driver start endpoint should block.
    dstart = _req("POST", f"/api/driver/{driver_id}/trip/{trip_id}/start", json={})
    _require(dstart.status_code == 400, f"driver start expected 400, got {dstart.status_code}")
    dbody = dstart.json() or {}
    ddata = dbody.get("data") or {}
    _require(
        (ddata.get("error_code") == "TRIP_NOT_STARTED_YET"),
        f"driver start error_code mismatch: {ddata}",
    )
    _require(bool(ddata.get("start_allowed_after")), "driver start missing start_allowed_after")
    _require(int(ddata.get("seconds_until_start") or 0) > 0, "driver start seconds_until_start should be > 0")
    _require(bool(ddata.get("server_now")), "driver start missing server_now")
    print("Driver start lock: PASS")

    # V2 start endpoint should also block for same trip.
    v2 = _req("POST", f"/api/v2/trips/{trip_id}/start", json={})
    _require(v2.status_code == 400, f"v2 start expected 400, got {v2.status_code}")
    v2body = v2.json() or {}
    _require(v2body.get("error_code") == "TRIP_NOT_STARTED_YET", f"v2 error_code mismatch: {v2body}")
    v2data = v2body.get("data") or {}
    _require(bool(v2data.get("start_allowed_after")), "v2 start missing start_allowed_after")
    _require(int(v2data.get("seconds_until_start") or 0) > 0, "v2 start seconds_until_start should be > 0")
    _require(bool(v2data.get("server_now")), "v2 start missing server_now")
    print("V2 start lock: PASS")

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESULT: FAIL - {exc}")
        raise SystemExit(1)
