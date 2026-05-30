# backend/wsgi.py
"""
RG Travel Solution - WSGI Entry Point

✅ Path: backend/wsgi.py

Purpose:
- Production WSGI entry for Gunicorn / uWSGI / Waitress
- Creates Flask app, applies settings, registers ALL blueprints/endpoints:
  - DB routes         : /api/db/*
  - Utils routes      : /api/utils/*, /api/security/*, /api/time/*
  - Config routes     : /api/config/*, /api/settings/*
  - Seed routes       : /api/admin/seed/*, /api/drivers/seed/*, /api/employees/seed/*
  - Your main APIs    : (admin/driver/employee/trip/otp etc.) - if you have them as blueprints, register them here.

How to run:
- Dev (optional):
    python wsgi.py
- Production (Gunicorn):
    gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app

Flutter (Android emulator):
- Use base URL: http://10.0.2.2:5000

IMPORTANT:
- This file assumes your project now has:
    backend/db/__init__.py
    backend/utils/__init__.py
    backend/seeds/__init__.py
    backend/config/__init__.py
- If you already have app.py, you can either:
    A) Import create_app() from app.py
    B) Or keep everything here as the single entry point (recommended for deployment).
"""

from __future__ import annotations

import os
from flask import Flask, jsonify
from flask_cors import CORS


# =========================================================
# Safe imports (supports different run modes)
# =========================================================
def _import_config():
    try:
        from config import SETTINGS, apply_flask_config, register_config_all_routes
        return SETTINGS, apply_flask_config, register_config_all_routes
    except Exception:
        from .config import SETTINGS, apply_flask_config, register_config_all_routes  # type: ignore
        return SETTINGS, apply_flask_config, register_config_all_routes


def _import_db():
    try:
        from db import init_db, register_db_routes
        return init_db, register_db_routes
    except Exception:
        from .db import init_db, register_db_routes  # type: ignore
        return init_db, register_db_routes


def _import_utils():
    try:
        from utils import register_utils_routes
        return register_utils_routes
    except Exception:
        from .utils import register_utils_routes  # type: ignore
        return register_utils_routes


def _import_seeds():
    try:
        from seeds import register_seed_routes
        return register_seed_routes
    except Exception:
        from .seeds import register_seed_routes  # type: ignore
        return register_seed_routes


SETTINGS, apply_flask_config, register_config_all_routes = _import_config()
init_db, register_db_routes = _import_db()
register_utils_routes = _import_utils()
register_seed_routes = _import_seeds()


# =========================================================
# Optional: Import your main API blueprints (if exist)
# =========================================================
def _register_main_blueprints(app: Flask) -> None:
    """
    If you already have these modules, they will be registered.
    If not, this won't crash (safe for incremental development).

    Add your real modules here as you create them:
      - backend/routes/admin_routes.py
      - backend/routes/driver_routes.py
      - backend/routes/employee_routes.py
      - backend/routes/trip_routes.py
      - etc.
    """
    # Examples (keep safe with try/except)
    try:
        # If you have admin blueprint module
        from routes.admin_routes import admin_bp  # type: ignore
        app.register_blueprint(admin_bp)
    except Exception:
        pass

    try:
        from routes.driver_routes import driver_bp  # type: ignore
        app.register_blueprint(driver_bp)
    except Exception:
        pass

    try:
        from routes.employee_routes import employee_bp  # type: ignore
        app.register_blueprint(employee_bp)
    except Exception:
        pass

    try:
        from routes.grouping_routes import grouping_bp  # type: ignore
        app.register_blueprint(grouping_bp)
    except Exception:
        pass

    try:
        from routes.trip_creation_v2_routes import trip_v2_bp, list_no_trip_requests, create_groups  # type: ignore
        app.register_blueprint(trip_v2_bp)
        # Legacy compatibility aliases used by older Flutter builds.
        app.add_url_rule("/api/v2/employees/no-trip-requests", view_func=list_no_trip_requests, methods=["GET"])
        app.add_url_rule("/api/admin/groups/create", view_func=create_groups, methods=["POST"])
    except Exception:
        pass

    try:
        from routes.trip_routes import trip_bp  # type: ignore
        app.register_blueprint(trip_bp)
    except Exception:
        pass

    # If your OTP routes are registered via function:
    try:
        from services.otp_service import register_otp_routes  # type: ignore
        register_otp_routes(app)
    except Exception:
        pass


# =========================================================
# Flask App Factory (recommended)
# =========================================================
def create_app() -> Flask:
    app = Flask(__name__)

    # Apply config settings + secret key + DB config
    apply_flask_config(app)

    # CORS for Flutter (web / emulator)
    if SETTINGS.CORS_ENABLED:
        CORS(app, resources={r"/api/*": {"origins": SETTINGS.CORS_ORIGINS}})

    # Initialize DB schema (safe to run multiple times)
    try:
        init_db()
    except Exception:
        # If schema missing, app still starts; /api/db/init can be used after fixing schema file.
        pass

    # Register core system routes
    register_db_routes(app)           # /api/db/*
    register_utils_routes(app)        # /api/utils/* + /api/security/* + /api/time/*
    register_config_all_routes(app)   # /api/config/* + /api/settings/* (guarded by env flags)
    register_seed_routes(app)         # /api/*/seed/*

    # Register your project main business routes (admin/driver/employee/trips)
    _register_main_blueprints(app)

    # Root endpoint
    @app.get("/")
    def root():
        return jsonify(
            {
                "success": True,
                "message": "RG Travel Solution Backend is running.",
                "data": {
                    "api_base": "/api",
                    "health": "/api/db/health",
                    "ping": "/api/utils/ping",
                },
            }
        )

    # 404 handler (clean response for Flutter)
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(
            {
                "success": False,
                "message": "Endpoint not found.",
                "error": {"code": "NOT_FOUND"},
                "data": {"path": os.getenv("PATH_INFO", "")},
            }
        ), 404

    return app


# WSGI callable
app = create_app()


# =========================================================
# Dev run (optional)
# =========================================================
if __name__ == "__main__":
    # For local testing only (use gunicorn in production)
    app.run(host=SETTINGS.HOST, port=SETTINGS.PORT, debug=SETTINGS.DEBUG)
