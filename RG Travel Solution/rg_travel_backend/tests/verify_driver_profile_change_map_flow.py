"""
Smoke test: driver profile-change request with map coordinates.

Flow:
1) Create driver via signup-request + admin approval.
2) Driver sends profile change request with new home_town + home_lat/home_lng.
3) Admin approves driver-change request.
4) Driver profile reflects updated coordinates.

Run:
  python rg_travel_backend/tests/verify_driver_profile_change_map_flow.py
"""

from __future__ import annotations

import os
import random
import string
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests


BASE_URL = os.getenv("RG_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def _req(method: str, path: str, **kwargs: Any) -> requests.Response:
    return requests.request(method, f"{BASE_URL}{path}", timeout=20, **kwargs)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _rand_digits(n: int) -> str:
    return "".join(random.choice(string.digits) for _ in range(n))


def _make_seed_driver_payload() -> Dict[str, Any]:
    return {
        "name": f"Map Change Driver {_rand_digits(4)}",
        "mobile": f"9{_rand_digits(9)}",
        "dl_no": f"MH{_rand_digits(13)}",
        "cab_no": f"MH{_rand_digits(2)}CD{_rand_digits(4)}",
        "vehicle_type": 4,
        "home_town": "Pune Camp",
        "home_lat": 18.5204,
        "home_lng": 73.8567,
    }


def _find_request_id(path: str, mobile: str) -> int:
    res = _req("GET", path)
    _require(res.status_code == 200, f"{path} failed: {res.status_code}")
    rows: List[Dict[str, Any]] = ((res.json() or {}).get("data") or [])
    for row in rows:
        if str(row.get("mobile") or "").strip() == mobile:
            return int(row["id"])
    raise AssertionError(f"Request for mobile={mobile} not found in {path}")


def _create_driver_and_approve() -> str:
    payload = _make_seed_driver_payload()
    r1 = _req("POST", "/api/auth/driver/signup-request", json=payload)
    _require(r1.status_code == 200, f"driver signup-request failed: {r1.status_code} {r1.text}")
    req_id = _find_request_id("/api/admin/driver-requests", str(payload["mobile"]))
    r2 = _req("POST", f"/api/admin/driver-requests/{req_id}/approve", json={})
    _require(r2.status_code == 200, f"approve driver request failed: {r2.status_code} {r2.text}")
    data = (r2.json() or {}).get("data") or {}
    driver_id = str(data.get("driver_id") or "").strip()
    _require(driver_id, "approve response missing driver_id")
    return driver_id


def _submit_profile_change(driver_id: str, mobile: str) -> int:
    new_lat = 18.5312
    new_lng = 73.8445
    body = {
        "name": f"Updated Driver {_rand_digits(3)}",
        "mobile": mobile,
        "dl_no": f"MH{_rand_digits(13)}",
        "cab_no": f"MH{_rand_digits(2)}EF{_rand_digits(4)}",
        "hometown": "Shivaji Nagar Pune",
        "home_lat": new_lat,
        "home_lng": new_lng,
    }
    r = _req("POST", f"/api/driver/profile/{driver_id}/change-request", json=body)
    _require(r.status_code == 200, f"driver change-request failed: {r.status_code} {r.text}")
    # find request by mobile from admin queue
    req_id = _find_request_id("/api/admin/driver-change-requests", mobile)
    return req_id


def _approve_profile_change(req_id: int) -> None:
    r = _req("POST", f"/api/admin/driver-change-requests/{req_id}/approve", json={})
    _require(r.status_code == 200, f"approve driver-change failed: {r.status_code} {r.text}")


def _assert_driver_coords(driver_id: str, expected_lat: float, expected_lng: float) -> None:
    r = _req("GET", f"/api/driver/profile/{driver_id}")
    _require(r.status_code == 200, f"driver profile fetch failed: {r.status_code} {r.text}")
    p = (r.json() or {}).get("data") or {}
    lat = p.get("home_lat")
    lng = p.get("home_lng")
    _require(lat is not None and lng is not None, "driver profile missing home_lat/home_lng")
    _require(abs(float(lat) - expected_lat) < 0.0005, f"home_lat mismatch: {lat}")
    _require(abs(float(lng) - expected_lng) < 0.0005, f"home_lng mismatch: {lng}")


def main() -> int:
    print("=== verify_driver_profile_change_map_flow ===")
    print(f"BASE_URL={BASE_URL}")

    driver_id = _create_driver_and_approve()
    print(f"Created driver: {driver_id}")

    profile = _req("GET", f"/api/driver/profile/{driver_id}")
    _require(profile.status_code == 200, "initial driver profile fetch failed")
    current_mobile = str(((profile.json() or {}).get("data") or {}).get("mobile") or "").strip()
    _require(current_mobile, "driver mobile missing")

    req_id = _submit_profile_change(driver_id, current_mobile)
    print(f"Driver profile-change request id: {req_id}")

    _approve_profile_change(req_id)
    print("Admin approved profile change request.")

    _assert_driver_coords(driver_id, 18.5312, 73.8445)
    print("Driver profile updated coordinates verified.")
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

