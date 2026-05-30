# backend/__init__.py
"""
RG Travel Solution - Backend Package Init

✅ Path: backend/__init__.py
✅ Structure: backend/

Purpose:
- Makes `backend/` a Python package (so you can run: python -m backend.app)
- Provides a single app factory + WSGI entrypoint export:
    from backend import create_app, app

- Provides "register_all_routes(app)" convenience if you want modular setup.

This file integrates:
- backend/config/     -> settings + keys + optional /api/config/* and /api/settings/*
- backend/db/         -> init_db + /api/db/*
- backend/utils/      -> /api/utils/* + /api/security/* + /api/time/*
- backend/seeds/      -> /api/admin/seed/*, /api/drivers/seed/*, /api/employees/seed/*
- backend/app.py      -> your main project APIs (admin/driver/employee/trips/otp etc.)

So:
- In production: you can point WSGI server to `backend:app`
- In dev: you can run `python -m backend.app` or `python backend/app.py`

"""

from __future__ import annotations

from typing import Any

from flask import Flask

# ---------------------------------------------------------
# Import create_app/app from backend/app.py (single source)
# ---------------------------------------------------------
try:
    # If running from inside backend/ folder
    from app import create_app as _create_app  # type: ignore
    from app import app as _app  # type: ignore
except Exception:
    # If running as a package: python -m backend.app
    from .app import create_app as _create_app  # type: ignore
    from .app import app as _app  # type: ignore


def create_app() -> Flask:
    """
    Public app factory.
    Returns the fully configured Flask app with all endpoints registered.
    """
    return _create_app()


# Pre-created WSGI callable (for gunicorn: backend:app)
app: Flask = _app


def register_all_routes(app: Any) -> None:
    """
    Optional helper:
    If you want to build your own Flask app somewhere else and only register routes.

    BUT: Recommended is to just use create_app() from backend/app.py.

    This will register:
    - db routes
    - utils routes
    - config routes
    - seed routes
    - (any extra main routes already in backend/app.py are included there)
    """
    # Usually NOT needed because backend/app.py already registers everything.
    # Provided for flexibility.
    try:
        from db import register_db_routes  # type: ignore
        from utils import register_utils_routes  # type: ignore
        from config import register_config_all_routes  # type: ignore
        from seeds import register_seed_routes  # type: ignore
    except Exception:
        from .db import register_db_routes  # type: ignore
        from .utils import register_utils_routes  # type: ignore
        from .config import register_config_all_routes  # type: ignore
        from .seeds import register_seed_routes  # type: ignore

    register_db_routes(app)
    register_utils_routes(app)
    register_config_all_routes(app)
    register_seed_routes(app)


__all__ = [
    "create_app",
    "app",
    "register_all_routes",
]
