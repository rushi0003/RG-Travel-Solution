# backend/config/__init__.py
"""
RG Travel Solution - Config Package Init

✅ Path: backend/config/__init__.py
✅ Structure: backend/config/

Purpose:
- Makes `backend/config/` a Python package
- Provides backward-compatible exports so your existing code can use:
    from config import GOOGLE_MAPS_API_KEY, OTP_EXPIRY_MINUTES
- Central register function to register optional config/settings endpoints:
    - keys.py     -> /api/config/*
    - settings.py -> /api/settings/*

Recommended usage in app.py:
    from config import CONFIG, SETTINGS, apply_flask_config, register_config_routes, register_settings_routes
    apply_flask_config(app)
    register_config_routes(app)      # optional dev only (RG_ENABLE_CONFIG_API=1)
    register_settings_routes(app)    # optional dev only (RG_ENABLE_SETTINGS_API=1)
"""

from __future__ import annotations

from typing import Any

# ---- Safe imports for different run modes (package vs direct) ----
try:
    from .keys import (
        CONFIG,
        reload_keys_config,
        get_secret_key,
        get_google_maps_api_key,
        get_otp_expiry_minutes,
        get_token_ttl_minutes,
        is_db_reset_allowed,
        register_config_routes,
    )
except Exception:
    from keys import (  # type: ignore
        CONFIG,
        reload_keys_config,
        get_secret_key,
        get_google_maps_api_key,
        get_otp_expiry_minutes,
        get_token_ttl_minutes,
        is_db_reset_allowed,
        register_config_routes,
    )

try:
    from .settings import (
        SETTINGS,
        reload_settings,
        apply_flask_config,
        register_settings_routes,
    )
except Exception:
    from settings import (  # type: ignore
        SETTINGS,
        reload_settings,
        apply_flask_config,
        register_settings_routes,
    )


# =========================================================
# Backward-compatible constants (so old imports won’t break)
# =========================================================
# Example old code:
#   from config import GOOGLE_MAPS_API_KEY
# will still work.

GOOGLE_MAPS_API_KEY = get_google_maps_api_key()
OTP_EXPIRY_MINUTES = get_otp_expiry_minutes()
TOKEN_TTL_MINUTES = get_token_ttl_minutes()
SECRET_KEY = get_secret_key()
ALLOW_DB_RESET = is_db_reset_allowed()


# =========================================================
# One-call registration for optional endpoints
# =========================================================
def register_config_all_routes(app: Any) -> None:
    """
    Register all config-related blueprints in one call:
    - /api/config/*     (keys.py)
    - /api/settings/*   (settings.py)

    app.py:
        from config import register_config_all_routes
        register_config_all_routes(app)
    """
    # These endpoints are guarded by env flags:
    #   RG_ENABLE_CONFIG_API=1
    #   RG_ENABLE_SETTINGS_API=1
    register_config_routes(app)
    register_settings_routes(app)


__all__ = [
    # objects
    "CONFIG",
    "SETTINGS",

    # keys helpers
    "reload_keys_config",
    "get_secret_key",
    "get_google_maps_api_key",
    "get_otp_expiry_minutes",
    "get_token_ttl_minutes",
    "is_db_reset_allowed",
    "register_config_routes",

    # settings helpers
    "reload_settings",
    "apply_flask_config",
    "register_settings_routes",

    # backward constants
    "GOOGLE_MAPS_API_KEY",
    "OTP_EXPIRY_MINUTES",
    "TOKEN_TTL_MINUTES",
    "SECRET_KEY",
    "ALLOW_DB_RESET",

    # one-call register
    "register_config_all_routes",
]
