# backend/routes/__init__.py
"""
Routes module - simplified to avoid import errors
Just exports individual route files, let app.py handle registration
"""
from __future__ import annotations

# Don't import anything here to avoid circular dependencies
# Let the main app import routes directly

def register_blueprints(app):
    """
    Register all route blueprints to the Flask app.
    Import routes here to avoid circular imports.
    """
    print("Registering blueprints...")
    
    try:
        from routes.health_routes import health_bp  # type: ignore
        app.register_blueprint(health_bp)
        print("  ✅ Health routes")
    except Exception as e:
        print(f"  ⚠️  Health routes failed: {e}")
    
    try:
        from routes.auth_routes import auth_bp  # type: ignore
        app.register_blueprint(auth_bp)
        print("  ✅ Auth routes")
    except Exception as e:
        print(f"  ⚠️  Auth routes failed: {e}")
    
    try:
        from routes.admin_routes import admin_bp  # type: ignore
        app.register_blueprint(admin_bp)
        print("  ✅ Admin routes")
    except Exception as e:
        print(f"  ⚠️  Admin routes failed: {e}")
    
    try:
        from routes.driver_routes import driver_bp  # type: ignore
        app.register_blueprint(driver_bp)
        print("  ✅ Driver routes")
    except Exception as e:
        print(f"  ⚠️  Driver routes failed: {e}")
    
    try:
        from routes.employee_routes import employee_bp  # type: ignore
        app.register_blueprint(employee_bp)
        print("  ✅ Employee routes")
    except Exception as e:
        print(f"  ⚠️  Employee routes failed: {e}")
    
    print("Blueprint registration complete!")

# For backward compatibility
__all__ = ['register_blueprints']
