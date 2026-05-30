# Quick script to add shim functions to validation_service.py
import re

filepath = r"C:\Users\HP\Desktop\RG Travel Solution\RG Travel Solution\rg_travel_backend\services\validation_service.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add shim/alias functions at the end (before the file ends)
shim_code = '''

# =========================
# Legacy Aliases (for backward compatibility)
# =========================

def require_str(val: Any, name: str) -> str:
    """
    Legacy helper - ensures value is non-empty string.
    """
    s = clean_text(val)
    if not s:
        raise ValueError(f"{name} is required.")
    return s


def validate_mobile10(mobile: Any) -> bool:
    """
    Legacy alias - returns True/False only (no message).
    """
    ok, _ = validate_mobile(mobile)
    return ok


def validate_mobile_10(mobile: Any) -> bool:
    """Another alias for mobile validation."""
    return validate_mobile10(mobile)


def validate_driver_license(dl: Any) -> bool:
    """
    Legacy alias - returns True/False only.
    """
    ok, _ = validate_driving_license(dl)
    return ok


def validate_dl_number(dl: Any) -> bool:
    """Another alias for DL validation."""
    return validate_driver_license(dl)


def validate_employee_code(code: Any) -> bool:
    """
    Legacy alias - validates employee code format.
    For now, just check it's not empty (adjust as needed).
    """
    s = clean_text(code)
    return len(s) >= 3


def validate_time_hhmm(time_str: Any) -> bool:
    """
    Legacy alias - returns True/False only.
    """
    ok, _ = validate_hhmm(time_str)
    return ok


def validate_lat_lng(lat: Any, lng: Any) -> bool:
    """
    Legacy alias - returns True/False only.
    """
    ok, _ = validate_coord(lat, lng)
    return ok


def validate_route_no_optional(route_no: Any) -> bool:
    """
    Legacy alias - validates route number format.
    """
    if not route_no:
        return True  # optional
    ok, _ = validate_route_no(route_no)
    return ok
'''

# Append the shim code
content += shim_code

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added shim functions to validation_service.py")
