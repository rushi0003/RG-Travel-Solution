#!/usr/bin/env python3
"""
RG Travel Solution - Backend Startup Verification Script

This script verifies all backend components are properly configured and ready.
Run this before starting the main app to catch issues early.

Usage:
    python verify_setup.py
"""

import os
import sys
import sqlite3
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text):
    print(f"{BLUE}ℹ {text}{RESET}")


def check_python_version():
    """Verify Python 3.8+"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    required = (3, 8)
    
    if version >= required:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} is too old. Need 3.8+")
        return False


def check_dependencies():
    """Check if all required packages are installed"""
    print_header("Checking Dependencies")
    
    required_packages = [
        'flask',
        'flask_cors',
        'requests',
        'dotenv',
    ]
    
    all_ok = True
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} NOT installed")
            all_ok = False
    
    if not all_ok:
        print_warning("Run: pip install -r requirements.txt")
    
    return all_ok


def check_env_file():
    """Check if .env file exists"""
    print_header("Checking Configuration")
    
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if env_file.exists():
        print_success(".env file found")
        
        # Check key variables
        env_content = env_file.read_text()
        required_vars = [
            'RG_DEBUG',
            'RG_HOST',
            'RG_PORT',
            'RG_CORS_ENABLED',
        ]
        
        missing = []
        for var in required_vars:
            if var not in env_content:
                missing.append(var)
        
        if missing:
            print_warning(f"Missing variables: {', '.join(missing)}")
            return True  # Not critical, will use defaults
        else:
            print_success("All required variables present")
            return True
    else:
        print_error(".env file NOT found")
        if env_example.exists():
            print_warning(f"Copy {env_example} to .env")
        return False


def check_database_schema():
    """Check if database schema file exists"""
    print_header("Checking Database Schema")
    
    backend_dir = Path(__file__).parent
    schema_file = backend_dir / "db" / "schema.sql"
    
    if schema_file.exists():
        print_success(f"Schema file found: {schema_file}")
        
        # Check table definitions
        schema_content = schema_file.read_text()
        tables = ['admins', 'drivers', 'employees', 'sessions', 'trips', 'trip_employees']
        
        for table in tables:
            if f"CREATE TABLE" in schema_content and table in schema_content:
                print_success(f"Table '{table}' defined in schema")
            else:
                print_warning(f"Table '{table}' definition not found")
        
        return True
    else:
        print_error(f"Schema file NOT found: {schema_file}")
        return False


def check_required_directories():
    """Check if all required directories exist"""
    print_header("Checking Directory Structure")
    
    backend_dir = Path(__file__).parent
    required_dirs = [
        'config',
        'db',
        'routes',
        'services',
        'repositories',
        'utils',
        'seeds',
    ]
    
    all_ok = True
    for dir_name in required_dirs:
        dir_path = backend_dir / dir_name
        if dir_path.is_dir():
            print_success(f"Directory exists: {dir_name}/")
        else:
            print_error(f"Directory NOT found: {dir_name}/")
            all_ok = False
    
    return all_ok


def check_required_modules():
    """Check if all required Python modules exist"""
    print_header("Checking Python Modules")
    
    backend_dir = Path(__file__).parent
    
    # Check main app.py
    if (backend_dir / "app.py").exists():
        print_success("app.py exists")
    else:
        print_error("app.py NOT found")
        return False
    
    # Check config modules
    config_modules = ['__init__.py', 'settings.py', 'keys.py']
    for module in config_modules:
        if (backend_dir / 'config' / module).exists():
            print_success(f"config/{module}")
        else:
            print_warning(f"config/{module} missing")
    
    # Check routes
    route_modules = ['auth_routes.py', 'admin_routes.py', 'driver_routes.py', 
                     'employee_routes.py', 'health_routes.py']
    for module in route_modules:
        if (backend_dir / 'routes' / module).exists():
            print_success(f"routes/{module}")
        else:
            print_warning(f"routes/{module} missing")
    
    # Check services
    service_modules = ['grouping_service.py', 'otp_service.py', 'routing_service.py',
                      'tracking_service.py', 'validation_service.py']
    for module in service_modules:
        if (backend_dir / 'services' / module).exists():
            print_success(f"services/{module}")
        else:
            print_warning(f"services/{module} missing")
    
    return True


def verify_flask_imports():
    """Test if Flask app can be imported"""
    print_header("Testing Flask Imports")
    
    try:
        from flask import Flask, request
        from flask_cors import CORS
        print_success("Flask and Flask-CORS imported successfully")
    except ImportError as e:
        print_error(f"Failed to import Flask: {e}")
        return False
    
    try:
        # Try to import from config
        import sys
        backend_dir = Path(__file__).parent
        sys.path.insert(0, str(backend_dir))
        
        # Try config
        from config import SETTINGS
        print_success("Config module loads successfully")
        
        # Try db
        from db import get_db, init_db
        print_success("Database module loads successfully")
        
        return True
    except Exception as e:
        print_error(f"Failed to import modules: {e}")
        return False


def check_flask_app():
    """Try to create Flask app"""
    print_header("Testing Flask App Creation")
    
    try:
        import sys
        backend_dir = Path(__file__).parent
        sys.path.insert(0, str(backend_dir))
        
        from app import create_app
        app = create_app()
        print_success("Flask app created successfully")
        print_info(f"Debug mode: {app.debug}")
        print_info(f"JSON sorted keys: {app.json.sort_keys}")
        return True
    except Exception as e:
        print_error(f"Failed to create Flask app: {e}")
        print_info(f"Error: {e}")
        return False


def print_summary(results):
    """Print verification summary"""
    print_header("Verification Summary")
    
    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed
    
    print(f"\nTotal checks: {total}")
    print_success(f"{passed} passed")
    if failed > 0:
        print_error(f"{failed} failed")
    
    print()
    if failed == 0:
        print(f"{GREEN}{BOLD}✓ All checks passed! Backend is ready to run.{RESET}")
        print(f"{BLUE}Start with: python app.py{RESET}\n")
        return True
    else:
        print(f"{RED}{BOLD}✗ Some checks failed. Fix issues above before running.{RESET}\n")
        return False


def main():
    """Run all verification checks"""
    print(f"\n{BOLD}{BLUE}RG Travel Solution - Backend Verification{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")
    
    results = []
    
    # Run checks
    results.append(check_python_version())
    results.append(check_dependencies())
    results.append(check_env_file())
    results.append(check_required_directories())
    results.append(check_database_schema())
    results.append(check_required_modules())
    results.append(verify_flask_imports())
    results.append(check_flask_app())
    
    # Print summary
    success = print_summary(results)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
