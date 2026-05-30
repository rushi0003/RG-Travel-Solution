# backend/utils/security.py
"""
RG Travel Solution - Security Utilities (Auth + OTP helpers + Token sessions)

✅ Path: backend/utils/security.py

This module is designed to work with your Flask + SQLite backend and Flutter frontend.

What it provides (usable across Admin / Driver / Employee):
1) Password hashing + verification
2) Simple token-based sessions (Bearer token)
3) OTP generation + verification (for trip start/end)
4) Standard auth decorator to protect endpoints

✅ Optional Dev/Test Endpoints (if you register routes):
- GET  /api/security/ping
- POST /api/security/hash            (dev: hash a password)
- POST /api/security/verify          (dev: verify password)
- POST /api/security/token/create    (dev: create token for user_id/role)
- POST /api/security/token/verify    (dev: verify token)
- POST /api/security/otp/generate    (dev: generate otp + hash)
- POST /api/security/otp/verify      (dev: verify otp)

IMPORTANT:
- This is a "lite" security layer suitable for your project/demo.
- For production, use JWT (pyjwt) or Flask-Login + refresh tokens, bcrypt/argon2, HTTPS, etc.

Assumes:
- backend/db.py has get_db()
- You have (or want) a sessions table for tokens
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Callable, List

from flask import Blueprint, request, g, jsonify

# ---------------------------------------------------------
# Safe import of get_db
# ---------------------------------------------------------
def _import_get_db():
    try:
        from ..db import get_db  # type: ignore
        return get_db
    except Exception:
        pass

    try:
        from db import get_db  # type: ignore
        return get_db
    except Exception as e:
        raise ImportError(
            "Could not import get_db(). Ensure backend/db.py has get_db() and app.py run path is correct."
        ) from e


get_db = _import_get_db()


# ---------------------------------------------------------
# Safe import of standard responses (optional but recommended)
# ---------------------------------------------------------
def _import_responses():
    try:
        from .response import success_response, error_response, APIError  # type: ignore
        return success_response, error_response, APIError
    except Exception:
        # If response.py not used, fallback to basic jsonify
        def success_response(data=None, message="OK", status_code=200, meta=None):
            payload = {"success": True, "message": message, "data": data}
            if meta is not None:
                payload["meta"] = meta
            return jsonify(payload), status_code

        def error_response(message="Error", status_code=400, code="ERROR", data=None, debug=None):
            payload = {"success": False, "message": message, "error": {"code": code}, "data": data}
            if debug is not None:
                payload["debug"] = debug
            return jsonify(payload), status_code

        @dataclass
        class APIError(Exception):
            message: str
            status_code: int = 400
            code: str = "BAD_REQUEST"
            data: Optional[Dict[str, Any]] = None

        return success_response, error_response, APIError


success_response, error_response, APIError = _import_responses()


# ==========================
# Config (tune as needed)
# ==========================
DEFAULT_TOKEN_TTL_MINUTES = 60 * 24  # 24 hours
DEFAULT_OTP_EXPIRY_MINUTES = 5       # trip start/end OTP validity


def _now() -> datetime:
    return datetime.now()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


# ==========================
# Password hashing
# ==========================
def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Returns (salt, hash) using sha256(salt + password).
    For production: use bcrypt/argon2.
    """
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, pwd_hash


def verify_password(password: str, salt: str, pwd_hash: str) -> bool:
    calc = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    # constant-time compare
    return hmac.compare_digest(calc, pwd_hash)


# ==========================
# Token Session Storage
# ==========================
def ensure_session_tables() -> None:
    """
    Stores user sessions (token based).
    role: 'admin'/'driver'/'employee'
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_token(user_id: str, role: str, ttl_minutes: int = DEFAULT_TOKEN_TTL_MINUTES) -> Dict[str, Any]:
    ensure_session_tables()
    # Create a signed JWT and store it server-side so we can support logout/revocation.
    from .jwt_utils import create_jwt as _create_jwt

    jwt_obj = _create_jwt(user_id=str(user_id), role=str(role), ttl_minutes=ttl_minutes)
    token = jwt_obj.get("token")
    expires_at = jwt_obj.get("expires_at")
    sess_id = f"sess_{secrets.token_hex(8)}"

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sessions (id, user_id, role, token, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sess_id, user_id, role, token, expires_at, _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    return {"session_id": sess_id, "token": token, "expires_at": expires_at, "role": role, "user_id": user_id}


def _get_session_by_token(token: str) -> Optional[Dict[str, Any]]:
    ensure_session_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, role, token, expires_at, created_at
            FROM sessions
            WHERE token = ?
            """,
            (token,),
        )
        row = cur.fetchone()
        if not row:
            return None

        # row_factory may be dict-like; support both
        if isinstance(row, (tuple, list)):
            return {
                "id": row[0],
                "user_id": row[1],
                "role": row[2],
                "token": row[3],
                "expires_at": row[4],
                "created_at": row[5],
            }
        return dict(row)
    finally:
        conn.close()


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    sess = _get_session_by_token(token)
    if not sess:
        return None
    try:
        exp = datetime.fromisoformat(sess["expires_at"])
    except Exception:
        return None
    # Compare in UTC to avoid local-time skew invalidating fresh tokens.
    if exp.tzinfo is None:
        now_ref = datetime.utcnow()
    else:
        now_ref = datetime.now(exp.tzinfo)
    if exp < now_ref:
        return None
    return sess


def delete_token(token: str) -> bool:
    ensure_session_tables()
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ==========================
# OTP utilities (trip start/end)
# ==========================
def generate_otp() -> Tuple[str, str]:
    """
    Returns (otp_plain, otp_hash).
    """
    otp = str(secrets.randbelow(900000) + 100000)  # 6 digits
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return otp, otp_hash


def verify_otp(otp_plain: str, otp_hash: str) -> bool:
    calc = hashlib.sha256(otp_plain.encode("utf-8")).hexdigest()
    return hmac.compare_digest(calc, otp_hash)


def otp_expiry_iso(minutes: int = DEFAULT_OTP_EXPIRY_MINUTES) -> str:
    return (_now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")


# ==========================
# Auth Decorator (Bearer token)
# ==========================
def _extract_bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth is None:
        return None, "HEADER_MISSING"
    auth = auth.strip()
    if not auth:
        return None, "HEADER_MISSING"
    parts = auth.split(" ", 1)
    if len(parts) != 2:
        return None, "BAD_FORMAT"
    scheme, token = parts[0].strip(), parts[1].strip()
    if scheme.lower() != "bearer":
        return None, "BAD_FORMAT"
    if not token:
        return None, "TOKEN_MISSING"
    return token, None


def require_auth(roles: Optional[List[str]] = None) -> Callable:
    """
    Protect endpoints using:
      Authorization: Bearer <token>

    Usage:
        @bp.route("/admin/secure")
        @require_auth(roles=["admin"])
        def secure_admin():
            # use g.user_id, g.role
            ...

    roles:
      - None -> any authenticated role allowed
      - ["admin"] -> only admin tokens
      - ["driver","admin"] -> driver or admin
    """
    # Demo token for development/testing (allow Flutter app to work without full auth)
    DEMO_TOKEN = "demo-admin-token-12345"
    
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            token, err = _extract_bearer_token()
            if err == "HEADER_MISSING":
                return error_response("Authorization header missing", 401, "AUTH_REQUIRED")
            if err in ("BAD_FORMAT", "TOKEN_MISSING"):
                return error_response("Bearer token missing", 401, "AUTH_REQUIRED")

            # Check for demo token first (allows Flutter app to work in dev mode)
            if token == DEMO_TOKEN:
                # Demo token grants admin access with synthetic user_id
                g.user_id = 1
                g.role = "admin"
                g.token = token
                return fn(*args, **kwargs)

            # token present — support JWTs and legacy session tokens
            sess = verify_token(token)
            if not sess:
                if token and "." in token:
                    try:
                        from .jwt_utils import decode_jwt

                        payload = decode_jwt(token)
                        sess = {
                            "id": payload.get("jti", ""),
                            "user_id": payload.get("sub"),
                            "role": payload.get("role"),
                            "token": token,
                            "expires_at": datetime.utcfromtimestamp(payload.get("exp")).isoformat(),
                            "created_at": datetime.utcfromtimestamp(payload.get("iat")).isoformat(),
                        }
                    except Exception as e:
                        ename = e.__class__.__name__
                        if ename in ("ExpiredSignatureError", "ExpiredSignature"):
                            return error_response("Token expired", 401, "TOKEN_EXPIRED")
                        return error_response("Invalid token", 401, "INVALID_TOKEN")
                else:
                    return error_response("Invalid token", 401, "INVALID_TOKEN")

            if roles is not None and sess["role"] not in roles:
                return error_response("Forbidden for this role.", 403, "FORBIDDEN_ROLE")

            # attach to flask.g for usage in endpoint
            g.user_id = sess["user_id"]
            g.role = sess["role"]
            g.token = token
            return fn(*args, **kwargs)

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    return decorator


# ==========================
# Optional Security Dev API
# ==========================
security_bp = Blueprint("security", __name__, url_prefix="/api/security")


@security_bp.route("/ping", methods=["GET"])
def security_ping():
    return success_response({"pong": True}, "security ok")


@security_bp.route("/hash", methods=["POST"])
def dev_hash():
    """
    Dev endpoint:
    body: {"password":"abc"}
    """
    body = request.get_json(silent=True) or {}
    pwd = str(body.get("password", "")).strip()
    if len(pwd) < 1:
        return error_response("password required", 400, "VALIDATION_ERROR")
    salt, h = hash_password(pwd)
    return success_response({"salt": salt, "hash": h}, "hashed")


@security_bp.route("/verify", methods=["POST"])
def dev_verify():
    """
    Dev endpoint:
    body: {"password":"abc","salt":"...","hash":"..."}
    """
    body = request.get_json(silent=True) or {}
    pwd = str(body.get("password", "")).strip()
    salt = str(body.get("salt", "")).strip()
    h = str(body.get("hash", "")).strip()
    if not (pwd and salt and h):
        return error_response("password, salt, hash required", 400, "VALIDATION_ERROR")
    ok = verify_password(pwd, salt, h)
    return success_response({"verified": ok}, "verified" if ok else "not verified")


@security_bp.route("/token/create", methods=["POST"])
def dev_token_create():
    """
    Dev endpoint:
    body: {"user_id":"admin_rg_001","role":"admin","ttl_minutes":60}
    """
    body = request.get_json(silent=True) or {}
    user_id = str(body.get("user_id", "")).strip()
    role = str(body.get("role", "")).strip().lower()
    ttl = body.get("ttl_minutes", DEFAULT_TOKEN_TTL_MINUTES)

    if not user_id:
        return error_response("user_id required", 400, "VALIDATION_ERROR")
    if role not in ("admin", "driver", "employee"):
        return error_response("role must be admin/driver/employee", 400, "VALIDATION_ERROR")

    try:
        ttl_int = int(ttl)
        if ttl_int < 1:
            ttl_int = 1
        if ttl_int > 60 * 24 * 30:
            ttl_int = 60 * 24 * 30  # 30 days cap
    except Exception:
        return error_response("ttl_minutes must be integer", 400, "VALIDATION_ERROR")

    tok = create_token(user_id=user_id, role=role, ttl_minutes=ttl_int)
    return success_response(tok, "token created")


@security_bp.route("/token/verify", methods=["POST"])
def dev_token_verify():
    """
    Dev endpoint:
    body: {"token":"..."}
    """
    body = request.get_json(silent=True) or {}
    token = str(body.get("token", "")).strip()
    if not token:
        return error_response("token required", 400, "VALIDATION_ERROR")
    sess = verify_token(token)
    if not sess:
        return error_response("invalid or expired token", 401, "INVALID_TOKEN")
    return success_response(sess, "token valid")


@security_bp.route("/otp/generate", methods=["POST"])
def dev_otp_generate():
    """
    Dev endpoint:
    body: {"expiry_minutes": 5}
    """
    body = request.get_json(silent=True) or {}
    expiry_minutes = body.get("expiry_minutes", DEFAULT_OTP_EXPIRY_MINUTES)
    try:
        expiry_minutes = int(expiry_minutes)
        if expiry_minutes < 1:
            expiry_minutes = 1
        if expiry_minutes > 60:
            expiry_minutes = 60
    except Exception:
        expiry_minutes = DEFAULT_OTP_EXPIRY_MINUTES

    otp, otp_hash = generate_otp()
    return success_response(
        {"otp": otp, "otp_hash": otp_hash, "expires_at": otp_expiry_iso(expiry_minutes)},
        "otp generated",
    )


@security_bp.route("/otp/verify", methods=["POST"])
def dev_otp_verify():
    """
    Dev endpoint:
    body: {"otp":"123456","otp_hash":"..."}
    """
    body = request.get_json(silent=True) or {}
    otp = str(body.get("otp", "")).strip()
    otp_hash = str(body.get("otp_hash", "")).strip()
    if not (otp and otp_hash):
        return error_response("otp and otp_hash required", 400, "VALIDATION_ERROR")
    ok = verify_otp(otp, otp_hash)
    return success_response({"verified": ok}, "otp valid" if ok else "otp invalid")


def register_security_routes(app: Any) -> None:
    """
    Register /api/security endpoints from app.py

    app.py:
        from utils.security import register_security_routes
        register_security_routes(app)
    """
    app.register_blueprint(security_bp)


__all__ = [
    "hash_password",
    "verify_password",
    "create_token",
    "verify_token",
    "delete_token",
    "generate_otp",
    "verify_otp",
    "otp_expiry_iso",
    "require_auth",
    "register_security_routes",
]
