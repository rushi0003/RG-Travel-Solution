# backend/seeds/__init__.py
"""
RG Travel Solution - Seeds Package Init

✅ Path: backend/seeds/__init__.py

Purpose:
- Makes `backend/seeds/` a proper Python package
- Provides ONE clean function to register ALL seed endpoints at once

After adding this file, in your backend/app.py you can do:

    from seeds import register_seed_routes
    register_seed_routes(app)

This will register:
- Admin seed endpoints  : /api/admin/seed/...
- Driver seed endpoints : /api/drivers/seed/...
- Employee seed endpoints: /api/employees/seed/...
"""

from __future__ import annotations

from typing import Any


def register_seed_routes(app: Any) -> None:
    """
    Register all seed blueprints in one call.

    ✅ Call from app.py:
        from seeds import register_seed_routes
        register_seed_routes(app)
    """

    # Import inside function to avoid circular-import issues
    # and to keep backend startup clean.
    try:
        from .seed_admin import register_seed_admin_routes  # type: ignore
    except Exception:
        # fallback if you run app.py in different way
        from seed_admin import register_seed_admin_routes  # type: ignore

    try:
        from .seed_drivers import register_seed_driver_routes  # type: ignore
    except Exception:
        from seed_drivers import register_seed_driver_routes  # type: ignore

    try:
        from .seed_employees import register_seed_employee_routes  # type: ignore
    except Exception:
        from seed_employees import register_seed_employee_routes  # type: ignore

    # Register all
    register_seed_admin_routes(app)
    register_seed_driver_routes(app)
    register_seed_employee_routes(app)


# Optional exports for convenience
__all__ = [
    "register_seed_routes",
]
