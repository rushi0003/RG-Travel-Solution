# backend/utils/__init__.py
"""
RG Travel Solution - Utils Package Init

✅ Path: backend/utils/__init__.py

Purpose:
- Makes `backend/utils/` a Python package
- Provides ONE function to register all optional utility endpoints:
  - response.py  -> /api/utils/*
  - security.py  -> /api/security/*
  - time_utils.py -> /api/time/*

Usage in backend/app.py:

    from utils import register_utils_routes
    register_utils_routes(app)

This keeps your app.py clean and ensures consistent endpoints across backend.
"""

from __future__ import annotations

from typing import Any


def register_utils_routes(app: Any) -> None:
    """
    Registers all utils blueprints (optional test/dev endpoints).

    ✅ app.py:
        from utils import register_utils_routes
        register_utils_routes(app)
    """

    # Import inside function to avoid circular import issues.
    # Also provides fallback imports for different run methods.

    # response utils endpoints: /api/utils/*
    try:
        from .response import register_utils_routes as _register_response_routes  # type: ignore
    except Exception:
        from response import register_utils_routes as _register_response_routes  # type: ignore

    # security endpoints: /api/security/*
    try:
        from .security import register_security_routes as _register_security_routes  # type: ignore
    except Exception:
        from security import register_security_routes as _register_security_routes  # type: ignore

    # time endpoints: /api/time/*
    try:
        from .time_utils import register_time_routes as _register_time_routes  # type: ignore
    except Exception:
        from time_utils import register_time_routes as _register_time_routes  # type: ignore

    # Register all
    _register_response_routes(app)
    _register_security_routes(app)
    _register_time_routes(app)


# Optional convenience exports (so you can import directly from utils)
try:
    from .response import APIError, success_response, error_response, api_exception_handler  # type: ignore
except Exception:
    APIError = None  # type: ignore
    success_response = None  # type: ignore
    error_response = None  # type: ignore
    api_exception_handler = None  # type: ignore

try:
    from .security import require_auth, hash_password, verify_password, create_token, verify_token, delete_token  # type: ignore
except Exception:
    require_auth = None  # type: ignore
    hash_password = None  # type: ignore
    verify_password = None  # type: ignore
    create_token = None  # type: ignore
    verify_token = None  # type: ignore
    delete_token = None  # type: ignore

try:
    from .time_utils import now_ist, today_ist, parse_hhmm, is_valid_hhmm, trip_day_key  # type: ignore
except Exception:
    now_ist = None  # type: ignore
    today_ist = None  # type: ignore
    parse_hhmm = None  # type: ignore
    is_valid_hhmm = None  # type: ignore
    trip_day_key = None  # type: ignore


__all__ = [
    "register_utils_routes",

    # response helpers
    "APIError",
    "success_response",
    "error_response",
    "api_exception_handler",

    # security helpers
    "require_auth",
    "hash_password",
    "verify_password",
    "create_token",
    "verify_token",
    "delete_token",

    # time helpers
    "now_ist",
    "today_ist",
    "parse_hhmm",
    "is_valid_hhmm",
    "trip_day_key",
]
