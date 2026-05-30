"""
Verify driver go-home request status sync end-to-end on running backend.

Checks:
1) Driver creates go-home request -> status becomes pending.
2) Admin approves latest request -> status becomes approved.
3) Driver second request while approved -> blocked (409).
4) Admin removes approved request (reject endpoint) -> status becomes rejected.
5) Driver can send new request again after removal -> status becomes pending.
6) If assigned-trip exists, embedded go-home status fields are validated too.

Run:
  python rg_travel_backend/tests/verify_go_home_status_sync.py --driver-id <driver_id>
Optional:
  --base-url http://127.0.0.1:5000
  --hometown Kalyan
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Optional

import requests


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _get(base_url: str, path: str) -> Dict[str, Any]:
    r = requests.get(f"{base_url}{path}", timeout=20)
    return {"status": r.status_code, "json": r.json()}


def _post(base_url: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = requests.post(f"{base_url}{path}", json=(body or {}), timeout=20)
    return {"status": r.status_code, "json": r.json()}


def _status_of(base_url: str, driver_id: str) -> Dict[str, Any]:
    res = _get(base_url, f"/api/driver/{driver_id}/hometown-request-status")
    _require(res["status"] == 200, f"status endpoint failed: {res['status']}")
    _require(res["json"].get("success") is True, "status endpoint success=false")
    data = res["json"].get("data")
    _require(isinstance(data, dict), "No hometown request found for driver")
    return data


def _assert_assigned_trip_sync(base_url: str, driver_id: str, expected_status: str) -> None:
    res = _get(base_url, f"/api/driver/{driver_id}/assigned-trip")
    _require(res["status"] == 200, f"assigned-trip failed: {res['status']}")
    _require(res["json"].get("success") is True, "assigned-trip success=false")
    trip = res["json"].get("data")
    if not isinstance(trip, dict):
        print("assigned-trip: no active trip, embedding check skipped")
        return

    embedded_status = str(trip.get("go_home_request_status") or "").strip().lower()
    embedded_obj = trip.get("go_home_request")
    _require(embedded_status == expected_status, f"embedded status mismatch: {embedded_status} != {expected_status}")
    _require(isinstance(embedded_obj, dict), "go_home_request object missing in assigned-trip")
    obj_status = str((embedded_obj or {}).get("status") or "").strip().lower()
    _require(obj_status == expected_status, f"embedded object status mismatch: {obj_status} != {expected_status}")
    print(f"assigned-trip embedding check: {expected_status} OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--driver-id", required=True)
    parser.add_argument("--hometown", default="Kalyan")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    driver_id = str(args.driver_id).strip()
    hometown = str(args.hometown).strip() or "Kalyan"

    print("=== verify_go_home_status_sync ===")
    health = _get(base_url, "/api/health")
    _require(health["status"] == 200, "Backend health endpoint not reachable")
    print("health: OK")

    # Step 1: create request and verify pending
    create1 = _post(base_url, f"/api/driver/{driver_id}/hometown-request", {"home_town": hometown})
    _require(create1["status"] == 200, f"create request failed: {create1['status']}")
    _require(create1["json"].get("success") is True, "create request success=false")
    req1_id = int(((create1["json"].get("data") or {}).get("request_id") or 0))
    _require(req1_id > 0, "request_id missing after create")
    s1 = _status_of(base_url, driver_id)
    _require(str(s1.get("status", "")).lower() == "pending", "status is not pending after create")
    print(f"pending check: OK (request_id={req1_id})")
    _assert_assigned_trip_sync(base_url, driver_id, "pending")

    # Step 2: approve latest request and verify approved
    approve = _post(base_url, f"/api/v2/drivers/go-home-requests/{req1_id}/approve", {})
    _require(approve["status"] == 200, f"approve failed: {approve['status']}")
    _require(approve["json"].get("success") is True, "approve success=false")
    s2 = _status_of(base_url, driver_id)
    _require(str(s2.get("status", "")).lower() == "approved", "status is not approved after approve")
    print("approved check: OK")
    _assert_assigned_trip_sync(base_url, driver_id, "approved")

    # Step 3: second request must be blocked while approved is still valid.
    create_blocked = _post(base_url, f"/api/driver/{driver_id}/hometown-request", {"home_town": hometown})
    _require(create_blocked["status"] == 409, f"second create should be blocked with 409, got {create_blocked['status']}")
    print("second request block check: OK (409)")

    # Step 4: admin removes approved request (reject endpoint) and verify rejected
    reject = _post(base_url, f"/api/v2/drivers/go-home-requests/{req1_id}/reject", {})
    _require(reject["status"] == 200, f"reject failed: {reject['status']}")
    _require(reject["json"].get("success") is True, "reject success=false")
    s4 = _status_of(base_url, driver_id)
    _require(str(s4.get("status", "")).lower() == "rejected", "status is not rejected after admin remove")
    print("admin remove check: OK")
    _assert_assigned_trip_sync(base_url, driver_id, "rejected")

    # Step 5: after reject/remove driver can send a new request.
    create2 = _post(base_url, f"/api/driver/{driver_id}/hometown-request", {"home_town": hometown})
    _require(create2["status"] == 200, f"new create after reject failed: {create2['status']}")
    _require(create2["json"].get("success") is True, "new create after reject success=false")
    req2_id = int(((create2["json"].get("data") or {}).get("request_id") or 0))
    _require(req2_id > 0, "new request_id missing after reject")
    s5 = _status_of(base_url, driver_id)
    _require(str(s5.get("status", "")).lower() == "pending", "status is not pending after re-create")
    print(f"re-create after reject check: OK (request_id={req2_id})")
    _assert_assigned_trip_sync(base_url, driver_id, "pending")

    print("RESULT: PASS")
    print(json.dumps({"driver_id": driver_id, "first_request_id": req1_id, "second_request_id": req2_id}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESULT: FAIL - {exc}")
        raise SystemExit(1)
