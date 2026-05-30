# backend/utils/response.py
"""
RG Travel Solution - Standard API Response Helpers

✅ Path: backend/utils/response.py

Goal:
- Keep ALL backend endpoints returning the SAME response format
- Reduce repeated jsonify/try-except code
- Works with Flask Blueprints across Admin / Driver / Employee / Trips / OTP

This file provides:
1) success_response(...)  -> consistent success JSON
2) error_response(...)    -> consistent error JSON
3) api_exception_handler(...) decorator for clean endpoints
4) register_utils_routes(app) -> optional health/test endpoints (dev)

Standard Response Format:
{
  "success": true/false,
  "message": "text",
  "data": {...} | [...] | null,
  "meta": {...} (optional)
}

✅ Optional Dev Endpoints (if you register routes):
- GET /api/utils/ping
- GET /api/utils/health
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, Union

from flask import Blueprint, jsonify, request


JSONType = Union[Dict[str, Any], list, str, int, float, bool, None]


# ==========================
# Custom API Error
# ==========================
@dataclass
class APIError(Exception):
    """
    Raise this inside endpoints/services to return clean API errors.
    Example:
        raise APIError("Admin not found", status_code=404, code="ADMIN_NOT_FOUND")
    """
    message: str
    status_code: int = 400
    code: str = "BAD_REQUEST"
    data: Optional[Dict[str, Any]] = None


# ==========================
# Response Builders
# ==========================
def success_response(
    data: JSONType = None,
    message: str = "OK",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None,
):
    payload: Dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status_code


def error_response(
    message: str = "Error",
    status_code: int = 400,
    code: str = "ERROR",
    data: Optional[Dict[str, Any]] = None,
    debug: Optional[Dict[str, Any]] = None,
):
    payload: Dict[str, Any] = {
        "success": False,
        "message": message,
        "error": {
            "code": code,
        },
        "data": data,
    }
    if debug is not None:
        payload["debug"] = debug
    return jsonify(payload), status_code


# ==========================
# Helper: Request meta
# ==========================
def request_meta() -> Dict[str, Any]:
    """
    Useful meta for debugging client-server problems.
    Example: host mismatch, wrong endpoint, content-type, etc.
    """
    return {
        "path": request.path,
        "method": request.method,
        "content_type": request.content_type,
        "remote_addr": request.remote_addr,
    }


# ==========================
# Decorator: Exception handling
# ==========================
def api_exception_handler(
    default_message: str = "Something went wrong",
    include_traceback: bool = False,
):
    """
    Wrap any endpoint with clean error handling.

    Usage:
        from utils.response import api_exception_handler, success_response

        @bp.route("/x")
        @api_exception_handler("Failed to fetch x")
        def x():
            ...
            return success_response(data)

    include_traceback:
      - keep False for production
      - True for local debugging
    """

    def decorator(fn: Callable):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)

            except APIError as ae:
                # Controlled business error
                return error_response(
                    message=ae.message,
                    status_code=ae.status_code,
                    code=ae.code,
                    data=ae.data,
                    debug={"meta": request_meta()} if include_traceback else None,
                )

            except ValueError as ve:
                # Common validation errors
                dbg = None
                if include_traceback:
                    dbg = {"trace": traceback.format_exc(), "meta": request_meta()}
                return error_response(
                    message=str(ve),
                    status_code=400,
                    code="VALIDATION_ERROR",
                    data=None,
                    debug=dbg,
                )

            except Exception as e:
                # Unknown errors (DB, server bugs, etc.)
                dbg = None
                if include_traceback:
                    dbg = {"trace": traceback.format_exc(), "meta": request_meta()}
                return error_response(
                    message=default_message,
                    status_code=500,
                    code="INTERNAL_SERVER_ERROR",
                    data={"detail": str(e)} if include_traceback else None,
                    debug=dbg,
                )

        # Flask needs name preserved sometimes
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper

    return decorator


# ==========================
# Optional: Utils endpoints
# ==========================
utils_bp = Blueprint("utils", __name__, url_prefix="/api/utils")


@utils_bp.route("/ping", methods=["GET"])
def ping():
    """
    Simple ping to verify backend is reachable from Flutter.
    """
    return success_response(
        data={"pong": True},
        message="RG Travel Solution backend is reachable.",
        meta=request_meta(),
    )


@utils_bp.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint (extendable).
    """
    return success_response(
        data={
            "status": "healthy",
        },
        message="OK",
        meta=request_meta(),
    )


def register_utils_routes(app: Any) -> None:
    """
    Register /api/utils endpoints from app.py

    app.py:
        from utils.response import register_utils_routes
        register_utils_routes(app)
    """
    app.register_blueprint(utils_bp)


# ==========================
# Simple aliases for convenience
# ==========================
def ok(data: JSONType = None, message: str = "OK", status_code: int = 200):
    """Alias for success_response"""
    return success_response(data=data, message=message, status_code=status_code)


def fail(message: str = "Error", status_code: int = 400):
    """Alias for error_response"""
    return error_response(message=message, status_code=status_code, code="ERROR")


__all__ = [
    "APIError",
    "success_response",
    "error_response",
    "ok",
    "fail",
    "api_exception_handler",
    "register_utils_routes",
]
