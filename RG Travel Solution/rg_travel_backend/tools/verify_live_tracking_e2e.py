"""
Step 4 - Live Tracking End-to-End Verifier

What this verifies:
1) Driver can POST /api/driver/location for an assigned active route.
2) Same route returns data from GET /api/tracking/route/<route_no>/latest.
3) Route history is returned by GET /api/tracking/route/<route_no>/history.
4) Admin can access GET /api/admin/drivers/online.
5) Unauthorized driver cannot read another driver's route tracking.
6) Optional: Socket room receives `driver_location_update`.

Run from `rg_travel_backend`:
  python tools/verify_live_tracking_e2e.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    BACKEND_ROOT = Path(__file__).resolve().parents[1]
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from utils.security import create_token
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "Failed to import utils.security.create_token. Run this script from rg_travel_backend."
    ) from exc


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_test_data(db_path: Path) -> Dict[str, Any]:
    suffix = uuid.uuid4().hex[:8]
    now = _now_iso()
    trip_day = datetime.now().strftime("%Y%m%d")

    admin_id = f"adm_e2e_{suffix}"
    driver_id = f"drv_e2e_{suffix}"
    other_driver_id = f"drv_e2e_other_{suffix}"
    route_no = f"E2E_ROUTE_{suffix}".upper()

    conn = _db_connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    # Minimal admin row (not used for login, only for relations).
    cur.execute(
        """
        INSERT OR REPLACE INTO admins (
            id, name, mobile, email, office_name, office_location, office_address,
            password_salt, password_hash, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            admin_id,
            f"E2E Admin {suffix}",
            f"91{suffix[:8]}",
            f"e2e_admin_{suffix}@example.com",
            "E2E Office",
            "18.5204,73.8567",
            "Pune",
            "salt",
            "hash",
            now,
            now,
        ),
    )

    # Assigned test driver.
    cur.execute(
        """
        INSERT OR REPLACE INTO drivers (
            id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town,
            is_approved, password_salt, password_hash, is_online, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0, ?, ?)
        """,
        (
            driver_id,
            f"E2E Driver {suffix}",
            f"92{suffix[:8]}",
            f"DL{suffix.upper()}A",
            f"MH12{suffix[:4].upper()}",
            "4",
            "Pune",
            "salt",
            "hash",
            now,
            now,
        ),
    )

    # Unauthorized driver (negative RBAC test).
    cur.execute(
        """
        INSERT OR REPLACE INTO drivers (
            id, name, mobile, dl_no, vehicle_no, vehicle_type, home_town,
            is_approved, password_salt, password_hash, is_online, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0, ?, ?)
        """,
        (
            other_driver_id,
            f"E2E Other Driver {suffix}",
            f"93{suffix[:8]}",
            f"DL{suffix.upper()}B",
            f"MH14{suffix[:4].upper()}",
            "4",
            "Pune",
            "salt",
            "hash",
            now,
            now,
        ),
    )

    # Active trip assigned to test driver.
    cur.execute(
        """
        INSERT OR REPLACE INTO trips (
            route_no, trip_day, operation, trip_type, schedule_time, status,
            admin_id, driver_id, vehicle_type, created_at, updated_at
        ) VALUES (?, ?, 'pickup', 'pickup', '09:00', 'started', ?, ?, '4', ?, ?)
        """,
        (route_no, trip_day, admin_id, driver_id, now, now),
    )

    conn.commit()
    conn.close()

    admin_token = create_token(user_id=admin_id, role="admin", ttl_minutes=120)["token"]
    driver_token = create_token(user_id=driver_id, role="driver", ttl_minutes=120)["token"]
    other_driver_token = create_token(user_id=other_driver_id, role="driver", ttl_minutes=120)["token"]

    return {
        "admin_id": admin_id,
        "driver_id": driver_id,
        "other_driver_id": other_driver_id,
        "route_no": route_no,
        "admin_token": admin_token,
        "driver_token": driver_token,
        "other_driver_token": other_driver_token,
    }


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _record(checks: List[CheckResult], name: str, ok: bool, details: str) -> None:
    checks.append(CheckResult(name=name, passed=ok, details=details))
    mark = "[PASS]" if ok else "[FAIL]"
    print(f"{mark} {name}: {details}")


def _verify_socket(base_url: str, route_no: str, driver_token: str) -> Tuple[bool, str]:
    try:
        import socketio
    except Exception:
        return True, "Skipped (python-socketio not installed)"

    sio = socketio.Client(logger=False, engineio_logger=False)
    received: Dict[str, Any] = {"ok": False, "payload": None}

    @sio.on("driver_location_update")
    def _on_loc(data):
        received["ok"] = True
        received["payload"] = data

    try:
        sio.connect(base_url, headers={"Authorization": f"Bearer {driver_token}"}, wait_timeout=8)
        sio.emit("join_route", {"routeNo": route_no, "token": driver_token})
        time.sleep(0.8)
        return False, "Connected to socket, ready for broadcast assertion"
    except Exception as exc:
        return False, f"Socket connection failed: {exc}"
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass


def run(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    db_path = Path(args.db_path).resolve()
    checks: List[CheckResult] = []

    if not db_path.exists():
        _record(checks, "DB_PATH", False, f"DB not found: {db_path}")
        return 1

    try:
        ping = requests.get(f"{base_url}/api/health", timeout=5)
        if ping.status_code >= 500:
            _record(checks, "BACKEND_HEALTH", False, f"/api/health status={ping.status_code}")
            return 1
    except Exception as exc:
        _record(checks, "BACKEND_HEALTH", False, f"Cannot connect to backend at {base_url}: {exc}")
        return 1

    test = _ensure_test_data(db_path)
    route_no = test["route_no"]
    driver_token = test["driver_token"]
    admin_token = test["admin_token"]
    other_driver_token = test["other_driver_token"]
    driver_id = test["driver_id"]

    # 1) Driver location update
    payload = {
        "routeNo": route_no,
        "lat": 18.52043,
        "lng": 73.85674,
        "speed": 10.5,
        "heading": 135.0,
        "accuracy": 5.0,
        "deviceTime": _now_iso(),
    }
    try:
        r = requests.post(
            f"{base_url}/api/driver/location",
            headers=_headers(driver_token),
            json=payload,
            timeout=15,
        )
    except Exception as exc:
        _record(checks, "POST /api/driver/location", False, f"request failed: {exc}")
        print("\n=== SUMMARY ===")
        print(f"Passed: {sum(1 for c in checks if c.passed)}/{len(checks)}")
        print("Overall: FAIL")
        return 1
    ok = r.status_code == 200 and r.json().get("success") is True
    _record(checks, "POST /api/driver/location", ok, f"status={r.status_code}, body={r.text[:180]}")

    # 2) Route latest contract check
    r = requests.get(f"{base_url}/api/tracking/route/{route_no}/latest", headers=_headers(driver_token), timeout=15)
    body = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
    latest_ok = (
        r.status_code == 200
        and body.get("success") is True
        and isinstance(body.get("location"), dict)
        and body["location"].get("latitude") is not None
        and body["location"].get("longitude") is not None
        and isinstance(body.get("data"), dict)
        and body["data"].get("lat") is not None
        and body["data"].get("lng") is not None
    )
    _record(checks, "GET /api/tracking/route/<route>/latest", latest_ok, f"status={r.status_code}")

    # 3) Route history check
    r = requests.get(
        f"{base_url}/api/tracking/route/{route_no}/history?duration=30",
        headers=_headers(driver_token),
        timeout=15,
    )
    body = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
    points = body.get("points") if isinstance(body, dict) else None
    history_ok = r.status_code == 200 and body.get("success") is True and isinstance(points, list) and len(points) >= 1
    _record(
        checks,
        "GET /api/tracking/route/<route>/history",
        history_ok,
        f"status={r.status_code}, points={len(points) if isinstance(points, list) else 'n/a'}",
    )

    # 4) Admin online drivers
    r = requests.get(f"{base_url}/api/admin/drivers/online", headers=_headers(admin_token), timeout=15)
    body = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
    online_list = ((body.get("data") or {}).get("online_drivers") or []) if isinstance(body, dict) else []
    in_online = any(str(d.get("driver_id")) == str(driver_id) for d in online_list if isinstance(d, dict))
    online_ok = r.status_code == 200 and body.get("success") is True and in_online
    _record(checks, "GET /api/admin/drivers/online", online_ok, f"status={r.status_code}, includes_driver={in_online}")

    # 5) Unauthorized driver cannot read route latest
    r = requests.get(f"{base_url}/api/tracking/route/{route_no}/latest", headers=_headers(other_driver_token), timeout=15)
    unauthorized_ok = r.status_code == 403
    _record(checks, "RBAC negative check (other driver route access)", unauthorized_ok, f"status={r.status_code}")

    # 6) Optional socket check
    if args.check_socket:
        try:
            import socketio

            sio = socketio.Client(logger=False, engineio_logger=False)
            received: Dict[str, Any] = {"ok": False}
            joined: Dict[str, Any] = {"ok": False}
            join_err: Dict[str, Any] = {"message": ""}

            @sio.on("driver_location_update")
            def _on_update(data):
                if isinstance(data, dict) and data.get("routeNo") == route_no:
                    received["ok"] = True

            @sio.on("joined_route")
            def _on_joined(data):
                if isinstance(data, dict) and data.get("routeNo") == route_no:
                    joined["ok"] = True

            @sio.on("tracking_error")
            def _on_track_error(data):
                join_err["message"] = str(data)

            sio.connect(base_url, headers={"Authorization": f"Bearer {driver_token}"}, wait_timeout=8)
            sio.emit("join_route", {"routeNo": route_no, "token": driver_token})
            wait_start = time.time()
            while time.time() - wait_start < 5.0 and not joined["ok"] and not join_err["message"]:
                time.sleep(0.1)

            if not joined["ok"]:
                _record(
                    checks,
                    "Socket broadcast driver_location_update",
                    False,
                    f"join_route failed: {join_err['message'] or 'timeout waiting joined_route'}",
                )
                return 1

            # Respect backend min 2-second rate limit between updates.
            time.sleep(2.2)
            payload["lat"] = 18.52099
            payload["lng"] = 73.85711
            payload["deviceTime"] = _now_iso()
            post_resp = requests.post(
                f"{base_url}/api/driver/location",
                headers=_headers(driver_token),
                json=payload,
                timeout=15,
            )
            if post_resp.status_code != 200:
                _record(
                    checks,
                    "Socket broadcast driver_location_update",
                    False,
                    f"driver location update for socket check failed status={post_resp.status_code}",
                )
                return 1
            time.sleep(2.0)
            socket_ok = bool(received["ok"])
            _record(checks, "Socket broadcast driver_location_update", socket_ok, "event received" if socket_ok else "event not received")
        except Exception as exc:
            _record(checks, "Socket broadcast driver_location_update", False, str(exc))
        finally:
            try:
                sio.disconnect()
            except Exception:
                pass
    else:
        _record(checks, "Socket broadcast driver_location_update", True, "Skipped (--check-socket not enabled)")

    passed = sum(1 for c in checks if c.passed)
    total = len(checks)
    print("\n=== SUMMARY ===")
    print(f"Passed: {passed}/{total}")
    if passed != total:
        print("Overall: FAIL")
        return 1
    print("Overall: PASS")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify live tracking end-to-end flow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Backend base URL")
    parser.add_argument(
        "--db-path",
        default=str((Path(__file__).resolve().parents[1] / "rg_travel.db")),
        help="SQLite DB path used by backend",
    )
    parser.add_argument(
        "--check-socket",
        action="store_true",
        help="Also verify socket room broadcast (requires python-socketio)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
