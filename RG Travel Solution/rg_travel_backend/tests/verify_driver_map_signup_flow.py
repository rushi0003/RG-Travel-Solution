"""
Smoke test: driver signup request with map coordinates.

Flow:
1) Driver signup-request sends home_town + home_lat/home_lng.
2) Admin sees pending request and approves it.
3) Driver profile contains saved home_lat/home_lng.

Run:
  python rg_travel_backend/tests/verify_driver_map_signup_flow.py
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
    return requests.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _rand_digits(n: int) -> str:
    return "".join(random.choice(string.digits) for _ in range(n))


def _build_driver_payload() -> Dict[str, Any]:
    mobile = f"9{_rand_digits(9)}"
    dl_no = f"MH{_rand_digits(13)}"
    cab_no = f"MH{_rand_digits(2)}AB{_rand_digits(4)}"
    lat = 18.5204
    lng = 73.8567
    return {
        "name": f"Map Driver {_rand_digits(4)}",
        "mobile": mobile,
        "dl_no": dl_no,
        "cab_no": cab_no,
        "vehicle_type": 4,
        "home_town": "Pune, Maharashtra",
        "home_lat": lat,
        "home_lng": lng,
    }


def _find_driver_request_id(mobile: str) -> int:
    res = _req("GET", "/api/admin/driver-requests")
    _require(res.status_code == 200, f"/api/admin/driver-requests failed: {res.status_code}")
    rows: List[Dict[str, Any]] = ((res.json() or {}).get("data") or [])
    for row in rows:
        if str(row.get("mobile") or "").strip() != mobile:
            continue
        status = str(row.get("status") or "").strip().lower()
        if status in ("pending", "approved", "rejected"):
            return int(row["id"])
    raise AssertionError("New driver request not found in admin list")


def _approve_driver_request(req_id: int) -> str:
    res = _req("POST", f"/api/admin/driver-requests/{req_id}/approve", json={})
    _require(
        res.status_code == 200,
        f"approve driver request failed: {res.status_code} {res.text}",
    )
    data = (res.json() or {}).get("data") or {}
    driver_id = str(data.get("driver_id") or "").strip()
    _require(driver_id, "approve response missing driver_id")
    return driver_id


def _assert_driver_profile_coords(driver_id: str, expected_lat: float, expected_lng: float) -> None:
    res = _req("GET", f"/api/driver/profile/{driver_id}")
    _require(res.status_code == 200, f"driver profile failed: {res.status_code} {res.text}")
    profile = (res.json() or {}).get("data") or {}
    lat = profile.get("home_lat")
    lng = profile.get("home_lng")
    _require(lat is not None and lng is not None, "home_lat/home_lng missing in driver profile")
    dlat = abs(float(lat) - expected_lat)
    dlng = abs(float(lng) - expected_lng)
    _require(dlat < 0.0005 and dlng < 0.0005, f"coordinates mismatch: got ({lat},{lng})")


def main() -> int:
    print("=== verify_driver_map_signup_flow ===")
    print(f"BASE_URL={BASE_URL}")

    payload = _build_driver_payload()
    res = _req("POST", "/api/auth/driver/signup-request", json=payload)
    _require(res.status_code == 200, f"driver signup-request failed: {res.status_code} {res.text}")
    print("Driver signup-request created.")

    req_id = _find_driver_request_id(str(payload["mobile"]))
    print(f"Driver request found: id={req_id}")

    driver_id = _approve_driver_request(req_id)
    print(f"Driver approved: driver_id={driver_id}")

    _assert_driver_profile_coords(driver_id, float(payload["home_lat"]), float(payload["home_lng"]))
    print("Driver profile coordinates verified.")

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

