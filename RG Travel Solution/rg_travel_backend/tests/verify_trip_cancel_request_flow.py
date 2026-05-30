"""
Verify driver -> admin pre-assigned trip cancel-request flow.

Default (safe):
  - Driver creates cancel request
  - Admin sees request
  - Admin rejects request

Approve mode (destructive):
  - Same as above, then creates second request and approves it
  - Verifies trip status becomes cancelled

Run:
  python rg_travel_backend/tests/verify_trip_cancel_request_flow.py
  python rg_travel_backend/tests/verify_trip_cancel_request_flow.py --approve
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


BASE_URL = os.getenv("RG_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def _req(method: str, path: str, **kwargs: Any) -> requests.Response:
    return requests.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _find_preassigned_trip() -> Dict[str, Any]:
    res = _req("GET", "/api/admin/trips/live")
    _require(res.status_code == 200, f"/api/admin/trips/live failed: {res.status_code}")
    data = (res.json() or {}).get("data") or []
    _require(isinstance(data, list), "admin live trips payload is not list")

    for trip in data:
        status = str(trip.get("status") or "").strip().lower()
        if not bool(trip.get("is_preassigned")):
            continue
        if status in ("cancelled", "completed"):
            continue
        if not trip.get("driver_id"):
            continue
        return trip

    raise AssertionError("No eligible pre-assigned trip found in live trips.")


def _create_cancel_request(driver_id: str, trip_id: int, reason: str) -> Tuple[int, Dict[str, Any]]:
    res = _req(
        "POST",
        f"/api/driver/{driver_id}/trip/{trip_id}/cancel-request",
        json={"reason": reason},
    )
    payload = res.json() if res.content else {}

    # If one pending request already exists, backend returns 409.
    if res.status_code == 409:
        return 409, payload

    _require(res.status_code == 200, f"cancel-request create failed: {res.status_code} {payload}")
    return 200, payload


def _find_pending_request(trip_id: int, driver_id: str) -> Dict[str, Any]:
    res = _req("GET", "/api/admin/trip-cancel-requests")
    _require(res.status_code == 200, f"/api/admin/trip-cancel-requests failed: {res.status_code}")
    rows: List[Dict[str, Any]] = ((res.json() or {}).get("data") or [])
    _require(isinstance(rows, list), "trip-cancel-requests payload is not list")

    for r in rows:
        status = str(r.get("status") or "").strip().lower()
        if status != "pending":
            continue
        if int(r.get("trip_id") or 0) != trip_id:
            continue
        if str(r.get("driver_id") or "").strip() != str(driver_id):
            continue
        return r

    raise AssertionError("Pending cancel request not found in admin queue.")


def _assert_driver_assigned_reflects_request(driver_id: str, trip_id: int) -> None:
    res = _req("GET", f"/api/driver/{driver_id}/assigned-trip")
    _require(res.status_code == 200, f"driver assigned-trip failed: {res.status_code}")
    trip = ((res.json() or {}).get("data") or {})
    _require(int(trip.get("id") or 0) == trip_id, "assigned-trip ID mismatch after cancel request")
    status = str(trip.get("cancel_request_status") or "").strip().lower()
    _require(status in ("pending", "rejected", "approved"), "cancel_request_status missing in assigned-trip")


def _reject_request(req_id: int) -> None:
    res = _req(
        "POST",
        f"/api/admin/trip-cancel-requests/{req_id}/reject",
        json={"note": "Rejected by verifier"},
    )
    _require(res.status_code == 200, f"reject request failed: {res.status_code} {res.text}")


def _approve_request(req_id: int) -> None:
    res = _req(
        "POST",
        f"/api/admin/trip-cancel-requests/{req_id}/approve",
        json={"note": "Approved by verifier"},
    )
    _require(res.status_code == 200, f"approve request failed: {res.status_code} {res.text}")


def _assert_trip_cancelled(trip_id: int) -> None:
    # Pull from admin live and fallback to history route if needed.
    live = _req("GET", "/api/admin/trips/live")
    _require(live.status_code == 200, f"admin live fetch failed while asserting cancel: {live.status_code}")
    trips: List[Dict[str, Any]] = ((live.json() or {}).get("data") or [])
    for t in trips:
        if int(t.get("id") or 0) == trip_id:
            _require(str(t.get("status") or "").strip().lower() == "cancelled", "trip status is not cancelled")
            return

    hist = _req("GET", "/api/admin/trips/history")
    _require(hist.status_code == 200, f"admin history fetch failed while asserting cancel: {hist.status_code}")
    rows: List[Dict[str, Any]] = ((hist.json() or {}).get("data") or [])
    for t in rows:
        if int(t.get("id") or t.get("trip_id") or 0) == trip_id:
            _require(str(t.get("status") or "").strip().lower() == "cancelled", "trip status in history is not cancelled")
            return
    raise AssertionError("trip not found while asserting cancelled status")


def main() -> int:
    approve_mode = "--approve" in sys.argv
    print("=== verify_trip_cancel_request_flow ===")
    print(f"BASE_URL={BASE_URL}")
    print(f"MODE={'approve+reject' if approve_mode else 'safe-reject-only'}")

    trip = _find_preassigned_trip()
    trip_id = int(trip["id"])
    driver_id = str(trip["driver_id"])
    print(f"Picked trip: id={trip_id}, driver_id={driver_id}, route_no={trip.get('route_no')}")

    reason = f"Verifier cancel request {datetime.now(timezone.utc).isoformat()}"
    code, payload = _create_cancel_request(driver_id, trip_id, reason)
    if code == 409:
        print("Create request returned 409 (pending already exists). Using existing pending request.")
    else:
        print("Driver cancel request created.")

    pending = _find_pending_request(trip_id, driver_id)
    req_id = int(pending["id"])
    print(f"Admin queue has pending request id={req_id}")

    _assert_driver_assigned_reflects_request(driver_id, trip_id)
    print("Driver assigned-trip reflects cancel request metadata.")

    _reject_request(req_id)
    print("Admin rejected cancel request: PASS")

    if not approve_mode:
        print("RESULT: PASS (safe mode)")
        return 0

    # Approve path: create a fresh request and approve it.
    reason2 = f"Verifier approve path {datetime.now(timezone.utc).isoformat()}"
    code2, _ = _create_cancel_request(driver_id, trip_id, reason2)
    _require(code2 == 200, "Could not create second cancel request for approve path.")
    pending2 = _find_pending_request(trip_id, driver_id)
    req_id2 = int(pending2["id"])
    _approve_request(req_id2)
    print(f"Admin approved request id={req_id2}")
    _assert_trip_cancelled(trip_id)
    print("Trip cancelled after approval: PASS")
    print("RESULT: PASS (approve mode)")
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
