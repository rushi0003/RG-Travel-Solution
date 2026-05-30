# backend/routes/health_routes.py
from __future__ import annotations

from flask import Blueprint, request, current_app
from datetime import datetime

from db import get_db
from services.hybrid_group_planner import probe_hybrid_provider
from services.nominatim_geocoding_service import probe_nominatim_provider
from utils.response import ok, fail, error_response

health_bp = Blueprint("health_bp", __name__, url_prefix="/api/health")


# =========================================================
# BASIC HEALTH
# =========================================================
@health_bp.get("")
def health():
    """
    GET /api/health
    Use this to quickly confirm server is running.
    """
    return ok(
        {
            "status": "ok",
            "service": "rg_travel_backend",
            "time_utc": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.path,
        }
    )


# =========================================================
# DB HEALTH
# =========================================================
@health_bp.get("/db")
def health_db():
    """
    GET /api/health/db
    Confirms SQLite DB opens + basic query works + (optional) table presence.
    """
    try:
        conn = get_db()
        cur = conn.cursor()

        # Simple DB query
        cur.execute("SELECT 1 AS one")
        one = cur.fetchone()

        # Optional: check expected tables (adjust if your schema differs)
        expected_tables = [
            "admins",
            "drivers",
            "employees",
            "trips",
            "trip_members",
            "sessions",
        ]

        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )
        tables = [r["name"] for r in cur.fetchall()]
        missing = [t for t in expected_tables if t not in tables]

        conn.close()

        return ok(
            {
                "db": "ok",
                "test_query": dict(one) if one else None,
                "tables_found": tables,
                "expected_tables": expected_tables,
                "missing_tables": missing,
                "time_utc": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        return fail(f"DB health failed: {e}", 500)


# =========================================================
# ECHO (debug fetch issues)
# =========================================================
@health_bp.route("/echo", methods=["GET", "POST"])
def echo():
    """
    /api/health/echo
    Helps debug mobile/web fetch issues.

    GET: returns headers + query params
    POST: returns json/body too
    """
    payload = {
        "status": "ok",
        "time_utc": datetime.utcnow().isoformat(),
        "method": request.method,
        "path": request.path,
        "origin": request.headers.get("Origin"),
        "host": request.headers.get("Host"),
        "user_agent": request.headers.get("User-Agent"),
        "remote_addr": request.remote_addr,
        "headers": {k: v for k, v in request.headers.items()},
        "args": request.args.to_dict(),
    }

    if request.method == "POST":
        try:
            payload["json"] = request.get_json(silent=True)
        except Exception:
            payload["json"] = None

        try:
            payload["data"] = request.get_data(as_text=True)
        except Exception:
            payload["data"] = None

    return ok(payload)


# =========================================================
# ROUTES LIST (optional but useful)
# =========================================================
@health_bp.get("/routes")
def list_routes():
    """
    GET /api/health/routes
    Lists registered routes. Useful to confirm blueprint registration.
    """
    routes = []
    try:
        for rule in current_app.url_map.iter_rules():
            routes.append(
                {
                    "endpoint": rule.endpoint,
                    "methods": sorted(list(rule.methods)),
                    "rule": str(rule),
                }
            )
        routes = sorted(routes, key=lambda x: x["rule"])
        return ok({"count": len(routes), "routes": routes})
    except Exception as e:
        return fail(f"Failed to list routes: {e}", 500)


# =========================================================
# HYBRID PROVIDER HEALTH
# =========================================================
@health_bp.get("/hybrid")
def health_hybrid():
    """
    GET /api/health/hybrid
    Confirms mandatory hybrid route provider readiness (OSRM/ORS).
    """
    diag = probe_hybrid_provider(timeout_sec=1.5)
    if diag.get("ready"):
        return ok({"hybrid": "ok", **diag})
    return error_response(
        message="Hybrid route provider unavailable",
        status_code=503,
        code="HYBRID_PROVIDER_UNAVAILABLE",
        data=diag,
    )


# =========================================================
# GEOCODING PROVIDER HEALTH
# =========================================================
@health_bp.get("/geocoding")
def health_geocoding():
    """
    GET /api/health/geocoding
    Confirms Nominatim geocoding provider readiness.
    """
    diag = probe_nominatim_provider(timeout_sec=2.0)
    if diag.get("ready"):
        return ok({"geocoding": "ok", **diag})
    return error_response(
        message="Geocoding provider unavailable",
        status_code=503,
        code="GEOCODING_PROVIDER_UNAVAILABLE",
        data=diag,
    )
