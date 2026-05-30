#!/usr/bin/env python
# Test script to identify import errors
print("=== Testing Backend Imports ===\n")

try:
    print("1. Testing Flask import...")
    from flask import Flask
    print("   ✅ Flask OK\n")
except Exception as e:
    print(f"   ❌ Flask FAILED: {e}\n")
    exit(1)

try:
    print("2. Testing db import...")
    from db import get_db
    print("   ✅ db OK\n")
except Exception as e:
    print(f"   ❌ db FAILED: {e}\n")
    exit(1)

try:
    print("3. Testing validation_service...")
    from services.validation_service import require_str, validate_mobile10
    print("   ✅ validation_service OK\n")
except Exception as e:
    print(f"   ❌ validation_service FAILED: {e}\n")
    exit(1)

try:
    print("4. Testing auth_routes...")
    from routes.auth_routes import auth_bp
    print("   ✅ auth_routes OK\n")
except Exception as e:
    print(f"   ❌ auth_routes FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    exit(1)

try:
    print("5. Testing individual route files...")
    from routes.admin_routes import admin_bp
    print("   ✅ routes.admin_routes OK")
    from routes.driver_routes import driver_bp
    print("   ✅ routes.driver_routes OK")
    from routes.employee_routes import employee_bp
    print("   ✅ routes.employee_routes OK")
    from routes.otp_routes import otp_bp
    print("   ✅ routes.otp_routes OK")
    from routes.tracking_routes import tracking_bp
    print("   ✅ routes.tracking_routes OK")
    from routes.grouping_routes import grouping_bp
    print("   ✅ routes.grouping_routes OK")
    print("   ✅ ALL route files OK\n")
except Exception as e:
    print(f"   ❌ route import FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    exit(1)

print("=== ALL IMPORTS SUCCESSFUL ✅ ===")
print("\nNow testing app.py import...")

try:
    import app
    print("✅ app.py imported successfully!")
except Exception as e:
    print(f"❌ app.py import failed: {e}")
    import traceback
    traceback.print_exc()
