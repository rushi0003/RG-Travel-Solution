# backend/config/keys.py
"""
RG Travel Solution - Keys / Secrets Config

✅ Path: backend/config/keys.py
✅ Structure: backend/config/

Purpose:
- Central place for ALL secret keys / API keys / security config
- Safe loading from environment variables (recommended)
- Provides optional API endpoints to validate configuration (dev only)
- Avoid hardcoding keys in code (important for security)

This file supports your project features:
- Google Maps API key (routing, distance, geocoding)
- OTP expiry settings
- Token/session expiry settings
- Optional "admin reset" / "db reset" protection flags

✅ Optional Dev Endpoints (if you register routes):
- GET  /api/config/health           (returns which keys are configured, NOT the key values)
- GET  /api/config/runtime          (returns non-sensitive runtime config)
- POST /api/config/reload           (reloads env based config; dev only)

IMPORTANT SECURITY RULE:
- These endpoints NEVER return actual secrets, only booleans (configured or not).

How to set env vars on Windows (PowerShell):
  $env:RG_GOOGLE_MAPS_API_KEY="YOUR_KEY"
  $env:RG_SECRET_KEY="some-long-random"
  $env:RG_ENABLE_CONFIG_API="1"

How to set env vars on Linux/Mac:
  export RG_GOOGLE_MAPS_API_KEY="YOUR_KEY"
  export RG_SECRET_KEY="some-long-random"
  export RG_ENABLE_CONFIG_API="1"
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, jsonify, request


# =========================================================
# Helpers
# =========================================================
def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    if v is None or v == "":
        return default
    return v


def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v)
    except Exception:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _mask(s: str, keep: int = 4) -> str:
    """
    Mask for logs (NOT used in API output).
    """
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return "*" * (len(s) - keep) + s[-keep:]


# =========================================================
# Config dataclass
# =========================================================
@dataclass
class KeysConfig:
    # Flask app secret (sessions/cookies if you ever use them)
    SECRET_KEY: str

    # Google Maps / Routes
    GOOGLE_MAPS_API_KEY: str

    # OTP settings
    OTP_EXPIRY_MINUTES: int

    # Token sessions TTL
    TOKEN_TTL_MINUTES: int

    # Optional safety flags
    ALLOW_DB_RESET: bool
    ENABLE_CONFIG_API: bool


# =========================================================
# Load config
# =========================================================
def load_keys_config() -> KeysConfig:
    """
    Loads config from env vars (preferred).
    Provides safe defaults for development only.
    """
    # For dev convenience: if missing SECRET_KEY, generate a random one each run.
    secret_key = _env("RG_SECRET_KEY") or secrets.token_urlsafe(48)

    google_maps = _env("RG_GOOGLE_MAPS_API_KEY", "") or ""

    otp_exp = _env_int("RG_OTP_EXPIRY_MINUTES", 5)
    token_ttl = _env_int("RG_TOKEN_TTL_MINUTES", 60 * 24)  # default 24 hours

    allow_db_reset = _env_bool("RG_ALLOW_DB_RESET", False)
    enable_config_api = _env_bool("RG_ENABLE_CONFIG_API", False)

    return KeysConfig(
        SECRET_KEY=secret_key,
        GOOGLE_MAPS_API_KEY=google_maps,
        OTP_EXPIRY_MINUTES=otp_exp,
        TOKEN_TTL_MINUTES=token_ttl,
        ALLOW_DB_RESET=allow_db_reset,
        ENABLE_CONFIG_API=enable_config_api,
    )


# Keep module-level loaded config (used by rest of backend)
CONFIG: KeysConfig = load_keys_config()


def reload_keys_config() -> KeysConfig:
    """
    Reload env config into module-level CONFIG.
    """
    global CONFIG
    CONFIG = load_keys_config()
    return CONFIG


# =========================================================
# Convenience getters (use these everywhere)
# =========================================================
def get_secret_key() -> str:
    return CONFIG.SECRET_KEY


def get_google_maps_api_key() -> str:
    return CONFIG.GOOGLE_MAPS_API_KEY


def get_otp_expiry_minutes() -> int:
    return int(CONFIG.OTP_EXPIRY_MINUTES)


def get_token_ttl_minutes() -> int:
    return int(CONFIG.TOKEN_TTL_MINUTES)


def is_db_reset_allowed() -> bool:
    return bool(CONFIG.ALLOW_DB_RESET)


# =========================================================
# Optional API endpoints (DEV ONLY)
# =========================================================
config_bp = Blueprint("config", __name__, url_prefix="/api/config")


def _success(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _error(message="Error", status=400, code="ERROR", data=None):
    return jsonify({"success": False, "message": message, "error": {"code": code}, "data": data}), status


def _api_enabled() -> bool:
    """
    Enable config API only when RG_ENABLE_CONFIG_API=1.
    """
    return bool(CONFIG.ENABLE_CONFIG_API)


@config_bp.route("/health", methods=["GET"])
def api_health():
    """
    Shows which keys are configured (no secrets returned).
    """
    if not _api_enabled():
        return _error("Config API disabled", 403, "DISABLED")

    return _success(
        {
            "SECRET_KEY_configured": bool(CONFIG.SECRET_KEY),
            "GOOGLE_MAPS_API_KEY_configured": bool(CONFIG.GOOGLE_MAPS_API_KEY),
            "OTP_EXPIRY_MINUTES": CONFIG.OTP_EXPIRY_MINUTES,
            "TOKEN_TTL_MINUTES": CONFIG.TOKEN_TTL_MINUTES,
            "ALLOW_DB_RESET": CONFIG.ALLOW_DB_RESET,
        },
        "OK",
    )


@config_bp.route("/runtime", methods=["GET"])
def api_runtime():
    """
    Returns non-sensitive runtime info (no actual secret values).
    """
    if not _api_enabled():
        return _error("Config API disabled", 403, "DISABLED")

    return _success(
        {
            "otp_expiry_minutes": CONFIG.OTP_EXPIRY_MINUTES,
            "token_ttl_minutes": CONFIG.TOKEN_TTL_MINUTES,
            "db_reset_allowed": CONFIG.ALLOW_DB_RESET,
            "google_maps_key_present": bool(CONFIG.GOOGLE_MAPS_API_KEY),
        },
        "OK",
    )


@config_bp.route("/reload", methods=["POST"])
def api_reload():
    """
    Reload env vars (dev).
    """
    if not _api_enabled():
        return _error("Config API disabled", 403, "DISABLED")

    reload_keys_config()
    return _success(
        {
            "reloaded": True,
            "SECRET_KEY_configured": bool(CONFIG.SECRET_KEY),
            "GOOGLE_MAPS_API_KEY_configured": bool(CONFIG.GOOGLE_MAPS_API_KEY),
            "OTP_EXPIRY_MINUTES": CONFIG.OTP_EXPIRY_MINUTES,
            "TOKEN_TTL_MINUTES": CONFIG.TOKEN_TTL_MINUTES,
            "ALLOW_DB_RESET": CONFIG.ALLOW_DB_RESET,
        },
        "Config reloaded",
    )


def register_config_routes(app: Any) -> None:
    """
    Register /api/config endpoints from app.py

    app.py:
        from config.keys import register_config_routes
        register_config_routes(app)
    """
    app.register_blueprint(config_bp)


__all__ = [
    "CONFIG",
    "reload_keys_config",
    "get_secret_key",
    "get_google_maps_api_key",
    "get_otp_expiry_minutes",
    "get_token_ttl_minutes",
    "is_db_reset_allowed",
    "register_config_routes",
]
