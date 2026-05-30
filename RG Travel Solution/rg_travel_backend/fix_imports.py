# Quick fix script to replace relative imports with absolute imports
import os
import re

# List of files to fix
files_to_fix = [
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\employee_routes.py",
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\auth_routes.py",
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\admin_routes.py",
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\driver_routes.py",
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\tracking_routes.py",
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\otp_routes.py",
    r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\routes\grouping_routes.py",
]

replacements = [
    (r'from \.\.db import', 'from db import'),
    (r'from \.\.utils\.response import', 'from utils.response import'),
    (r'from \.\.services\.validation_service import', 'from services.validation_service import'),
    (r'from \.\.services\.otp_service import', 'from services.otp_service import'),
    (r'from \.\.services\.tracking_service import', 'from services.tracking_service import'),
    (r'from \.\.services\.grouping_service import', 'from services.grouping_service import'),
    (r'from \.\.services\.route_no_service import', 'from services.route_no_service import'),
    (r'from \.\.services\.routing_service import', 'from services.routing_service import'),
    (r'from \.\.utils\.jwt_utils import', 'from utils.jwt_utils import'),
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply all replacements
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed: {os.path.basename(filepath)}")
    else:
        print(f"❌ Not found: {filepath}")

print("\n✅ All imports fixed!")
