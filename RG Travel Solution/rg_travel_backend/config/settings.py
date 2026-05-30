# backend/config/settings.py
"""
RG Travel Solution - App Settings (Flask + API + Features)

✅ Path: backend/config/settings.py
✅ Structure: backend/config/

Purpose:
- Single source of truth for backend configuration:
  - Flask config (DEBUG, CORS, JSON)
  - Database config path
  - API base prefixes and limits
  - Feature flags (seed APIs, config APIs, dev tools)
  - Google Maps + OTP + Token TTL reading (via config/keys.py)
- Optional API endpoints to read safe settings (dev only)

This file is designed to match your project:
- Flutter frontend calls Flask backend (often at http://10.0.2.2:5000)
- Role based modules (admin/driver/employee)
- OTP for trip start/end
- Seeds and DB init used during development

✅ Optional API endpoints (if you register routes):
- GET  /api/settings/health      (safe summary)
- GET  /api/settings/runtime     (safe runtime config, no secrets)
- POST /api/settings/reload      (reload keys/settings - dev only)

Security:
- Never returns secret keys
- Endpoints enabled only when RG_ENABLE_SETTINGS_API=1
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

# Import keys config (safe getters)
try:
    from .keys import (
        CONFIG as KEYS_CONFIG,
        reload_keys_config,
        get_google_maps_api_key,
        get_otp_expiry_minutes,
        get_token_ttl_minutes,
        get_secret_key,
        is_db_reset_allowed,
    )
except Exception:
    # fallback for different run modes
    from keys import (  # type: ignore
        CONFIG as KEYS_CONFIG,
        reload_keys_config,
        get_google_maps_api_key,
        get_otp_expiry_minutes,
        get_token_ttl_minutes,
        get_secret_key,
        is_db_reset_allowed,
    )


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


# =========================================================
# Settings dataclass
# =========================================================
@dataclass
class AppSettings:
    # Flask / server
    DEBUG: bool
    HOST: str
    PORT: int

    # CORS
    CORS_ENABLED: bool
    CORS_ORIGINS: str  # "*" or comma-separated list

    # Database
    DATABASE_PATH: Optional[str]  # if None, db module decides

    # API / Feature flags
    ENABLE_SEED_API: bool
    ENABLE_SETTINGS_API: bool
    ENABLE_CONFIG_API: bool  # mirrors keys.py config API

    # Limits
    MAX_GROUP_SIZE_4: int
    MAX_GROUP_SIZE_6: int
    MAX_EMPLOYEE_PER_TRIP: int

    # Maps / OTP / Token (read via keys.py)
    GOOGLE_MAPS_KEY_PRESENT: bool
    OTP_EXPIRY_MINUTES: int
    TOKEN_TTL_MINUTES: int

    # Dev safety
    ALLOW_DB_RESET: bool


# =========================================================
# Load settings
# =========================================================
def load_settings() -> AppSettings:
    """
    Load settings from environment variables.
    keys.py holds sensitive info (Google Maps key, secret key).
    """
    debug = _env_bool("RG_DEBUG", True)

    host = _env("RG_HOST", "0.0.0.0") or "0.0.0.0"
    port = _env_int("RG_PORT", 5000)

    cors_enabled = _env_bool("RG_CORS_ENABLED", True)
    cors_origins = _env("RG_CORS_ORIGINS", "*") or "*"

    # DB path override (optional). If not provided, db/__init__.py uses default.
    database_path = _env("RG_DB_PATH", None)

    # Feature flags
    enable_seed_api = _env_bool("RG_ENABLE_SEED_API", True)
    enable_settings_api = _env_bool("RG_ENABLE_SETTINGS_API", False)

    # mirrors keys.py flag, but can be overridden here too:
    enable_config_api = _env_bool("RG_ENABLE_CONFIG_API", bool(getattr(KEYS_CONFIG, "ENABLE_CONFIG_API", False)))

    # Grouping sizes (your project: 4 or 6 passengers)
    max_group_size_4 = _env_int("RG_MAX_GROUP_SIZE_4", 4)
    max_group_size_6 = _env_int("RG_MAX_GROUP_SIZE_6", 6)
    max_employee_per_trip = _env_int("RG_MAX_EMPLOYEE_PER_TRIP", 6)

    otp_exp = get_otp_expiry_minutes()
    token_ttl = get_token_ttl_minutes()

    maps_present = bool(get_google_maps_api_key())
    allow_db_reset = bool(is_db_reset_allowed())

    return AppSettings(
        DEBUG=debug,
        HOST=host,
        PORT=port,
        CORS_ENABLED=cors_enabled,
        CORS_ORIGINS=cors_origins,
        DATABASE_PATH=database_path,
        ENABLE_SEED_API=enable_seed_api,
        ENABLE_SETTINGS_API=enable_settings_api,
        ENABLE_CONFIG_API=enable_config_api,
        MAX_GROUP_SIZE_4=max_group_size_4,
        MAX_GROUP_SIZE_6=max_group_size_6,
        MAX_EMPLOYEE_PER_TRIP=max_employee_per_trip,
        GOOGLE_MAPS_KEY_PRESENT=maps_present,
        OTP_EXPIRY_MINUTES=otp_exp,
        TOKEN_TTL_MINUTES=token_ttl,
        ALLOW_DB_RESET=allow_db_reset,
    )


SETTINGS: AppSettings = load_settings()


def reload_settings() -> AppSettings:
    """
    Reload keys + settings from env vars.
    """
    reload_keys_config()
    global SETTINGS
    SETTINGS = load_settings()
    return SETTINGS


# =========================================================
# Apply to Flask app
# =========================================================
def apply_flask_config(app: Any) -> None:
    """
    Apply these settings to a Flask app instance.
    Use in app.py:
        from config.settings import SETTINGS, apply_flask_config
        apply_flask_config(app)
    """
    app.config["DEBUG"] = SETTINGS.DEBUG
    app.config["SECRET_KEY"] = get_secret_key()

    # Database path for db/__init__.py get_db_path() to pick up
    if SETTINGS.DATABASE_PATH:
        app.config["DATABASE"] = SETTINGS.DATABASE_PATH


# =========================================================
# Optional Settings API
# =========================================================
settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


def _success(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _error(message="Error", status=400, code="ERROR", data=None):
    return jsonify({"success": False, "message": message, "error": {"code": code}, "data": data}), status


def _api_enabled() -> bool:
    return bool(SETTINGS.ENABLE_SETTINGS_API)


@settings_bp.route("/health", methods=["GET"])
def api_health():
    """
    Safe summary (no secrets).
    """
    if not _api_enabled():
        return _error("Settings API disabled", 403, "DISABLED")

    return _success(
        {
            "debug": SETTINGS.DEBUG,
            "cors_enabled": SETTINGS.CORS_ENABLED,
            "seed_api_enabled": SETTINGS.ENABLE_SEED_API,
            "settings_api_enabled": SETTINGS.ENABLE_SETTINGS_API,
            "config_api_enabled": SETTINGS.ENABLE_CONFIG_API,
            "google_maps_key_present": SETTINGS.GOOGLE_MAPS_KEY_PRESENT,
            "otp_expiry_minutes": SETTINGS.OTP_EXPIRY_MINUTES,
            "token_ttl_minutes": SETTINGS.TOKEN_TTL_MINUTES,
            "allow_db_reset": SETTINGS.ALLOW_DB_RESET,
        },
        "OK",
    )


@settings_bp.route("/runtime", methods=["GET"])
def api_runtime():
    """
    Detailed but safe runtime config.
    """
    if not _api_enabled():
        return _error("Settings API disabled", 403, "DISABLED")

    return _success(
        {
            "server": {"host": SETTINGS.HOST, "port": SETTINGS.PORT, "debug": SETTINGS.DEBUG},
            "cors": {"enabled": SETTINGS.CORS_ENABLED, "origins": SETTINGS.CORS_ORIGINS},
            "limits": {
                "max_group_size_4": SETTINGS.MAX_GROUP_SIZE_4,
                "max_group_size_6": SETTINGS.MAX_GROUP_SIZE_6,
                "max_employee_per_trip": SETTINGS.MAX_EMPLOYEE_PER_TRIP,
            },
            "features": {
                "seed_api": SETTINGS.ENABLE_SEED_API,
                "settings_api": SETTINGS.ENABLE_SETTINGS_API,
                "config_api": SETTINGS.ENABLE_CONFIG_API,
            },
            "security": {
                "otp_expiry_minutes": SETTINGS.OTP_EXPIRY_MINUTES,
                "token_ttl_minutes": SETTINGS.TOKEN_TTL_MINUTES,
                "google_maps_key_present": SETTINGS.GOOGLE_MAPS_KEY_PRESENT,
                "db_reset_allowed": SETTINGS.ALLOW_DB_RESET,
            },
        },
        "OK",
    )


@settings_bp.route("/reload", methods=["POST"])
def api_reload():
    """
    Reload env vars (dev only).
    """
    if not _api_enabled():
        return _error("Settings API disabled", 403, "DISABLED")

    reload_settings()
    return _success(
        {
            "reloaded": True,
            "debug": SETTINGS.DEBUG,
            "cors_enabled": SETTINGS.CORS_ENABLED,
            "seed_api_enabled": SETTINGS.ENABLE_SEED_API,
            "google_maps_key_present": SETTINGS.GOOGLE_MAPS_KEY_PRESENT,
            "otp_expiry_minutes": SETTINGS.OTP_EXPIRY_MINUTES,
            "token_ttl_minutes": SETTINGS.TOKEN_TTL_MINUTES,
        },
        "Settings reloaded",
    )


def register_settings_routes(app: Any) -> None:
    """
    Register /api/settings endpoints from app.py:

        from config.settings import register_settings_routes
        register_settings_routes(app)
    """
    app.register_blueprint(settings_bp)


__all__ = [
    "SETTINGS",
    "reload_settings",
    "apply_flask_config",
    "register_settings_routes",
]
