# rg_travel_backend/services/validation_service.py
"""
RG Travel Solution — validation_service.py
=========================================

This module provides all **shared validations** used across:
- Auth / Signup / Profile Update APIs
- Driver & Employee forms
- Trip assignment checks (OTP format, route no format, coordinates)
- Vehicle / DL formats as per your requirement

✅ Project requirements covered:
1) Mobile number must be exactly **10 digits** (India).
2) Driving License format: **2 letters + 13 digits**  (example: MH1234567890123)
3) Vehicle number format: **XX00XX0000**
   Example: MH12AB1234
4) OTP format: exactly **6 digits**.
5) Route number format: **10 characters**
   - First 4: year (YYYY)
   - Next 4: digits
   - Last 2: month initials (first 2 letters of month, uppercase)
6) Coordinate validation: lat/lng bounds
7) Time format: "HH:MM" 24-hour (login/logout time)
8) Basic text validations (name, address length)

------------------------------------------------------------
Public APIs (call from routes/services)
------------------------------------------------------------

Mobile:
- validate_mobile(mobile) -> (bool, msg)
- assert_mobile(mobile) -> cleaned mobile

Driving License:
- validate_driving_license(dl) -> (bool, msg)
- assert_driving_license(dl) -> cleaned dl

Vehicle number:
- validate_vehicle_no(vehicle_no) -> (bool, msg)
- assert_vehicle_no(vehicle_no) -> cleaned

OTP:
- validate_otp(otp) -> (bool, msg)

Route No:
- validate_route_no(route_no) -> (bool, msg)

Time:
- validate_hhmm(time_str) -> (bool, msg)

Coordinates:
- validate_coord(lat, lng) -> (bool, msg)

Helper:
- clean_text(s)
- validate_required_fields(data, fields)

------------------------------------------------------------
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple, Optional


# =========================
# Regex patterns
# =========================

RE_MOBILE_10 = re.compile(r"^[0-9]{10}$")

# DL: 2 letters + 13 digits (you required)
RE_DL = re.compile(r"^[A-Z]{2}[0-9]{13}$")

# Vehicle: XX00XX0000  (2 letters, 2 digits, 2 letters, 4 digits)
RE_VEHICLE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}$")

# OTP: 6 digits
RE_OTP = re.compile(r"^[0-9]{6}$")

# Time: 24-hour HH:MM
RE_HHMM = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

# Route number: YYYY + 4 digits + 2 letters
RE_ROUTE_NO = re.compile(r"^[0-9]{4}[0-9]{4}[A-Z]{2}$")

# Month letters allowed (JAN->JA etc)
ALLOWED_MONTH2 = {
    "JA", "FE", "MA", "AP", "MY", "JU", "JL", "AU", "SE", "OC", "NO", "DE"
}


# =========================
# Core cleaners
# =========================

def clean_text(s: Any) -> str:
    """
    Normalizes text safely.
    """
    if s is None:
        return ""
    return str(s).strip()


def _upper_alnum(s: str) -> str:
    """
    For DL/vehicle/route no: remove spaces and make uppercase.
    """
    return re.sub(r"\s+", "", s).upper()


# =========================
# Mobile validations
# =========================

def validate_mobile(mobile: Any) -> Tuple[bool, str]:
    m = clean_text(mobile)
    if not m:
        return False, "Mobile number is required."
    if not RE_MOBILE_10.match(m):
        return False, "Mobile must be exactly 10 digits."
    return True, "OK"


def assert_mobile(mobile: Any) -> str:
    ok, msg = validate_mobile(mobile)
    if not ok:
        raise ValueError(msg)
    return clean_text(mobile)


# =========================
# Driving License validations
# =========================

def validate_driving_license(dl: Any) -> Tuple[bool, str]:
    s = _upper_alnum(clean_text(dl))
    if not s:
        return False, "Driving license is required."
    if not RE_DL.match(s):
        return False, "Driving license must be 2 letters + 13 digits (e.g., MH1234567890123)."
    return True, "OK"


def assert_driving_license(dl: Any) -> str:
    ok, msg = validate_driving_license(dl)
    if not ok:
        raise ValueError(msg)
    return _upper_alnum(clean_text(dl))


# =========================
# Vehicle number validations
# =========================

def validate_vehicle_no(vehicle_no: Any) -> Tuple[bool, str]:
    s = _upper_alnum(clean_text(vehicle_no))
    if not s:
        return False, "Vehicle number is required."
    if not RE_VEHICLE.match(s):
        return False, "Vehicle number must be format XX00XX0000 (e.g., MH12AB1234)."
    return True, "OK"


def assert_vehicle_no(vehicle_no: Any) -> str:
    ok, msg = validate_vehicle_no(vehicle_no)
    if not ok:
        raise ValueError(msg)
    return _upper_alnum(clean_text(vehicle_no))


# =========================
# OTP validations
# =========================

def validate_otp(otp: Any) -> Tuple[bool, str]:
    s = clean_text(otp)
    if not s:
        return False, "OTP is required."
    if not RE_OTP.match(s):
        return False, "OTP must be exactly 6 digits."
    return True, "OK"


# =========================
# Route number validations
# =========================

def validate_route_no(route_no: Any) -> Tuple[bool, str]:
    s = _upper_alnum(clean_text(route_no))
    if not s:
        return False, "Route number is required."
    if len(s) != 10:
        return False, "Route number must be exactly 10 characters."
    if not RE_ROUTE_NO.match(s):
        return False, "Route number format must be YYYY + 4 digits + 2 month letters."
    month2 = s[-2:]
    if month2 not in ALLOWED_MONTH2:
        return False, f"Invalid month code '{month2}' in route number."
    return True, "OK"


# =========================
# Time validations
# =========================

def validate_hhmm(time_str: Any) -> Tuple[bool, str]:
    s = clean_text(time_str)
    if not s:
        return False, "Time is required."
    if not RE_HHMM.match(s):
        return False, "Time must be HH:MM in 24-hour format (e.g., 09:30, 18:05)."
    return True, "OK"


# =========================
# Coordinate validations
# =========================

def validate_coord(lat: Any, lng: Any) -> Tuple[bool, str]:
    try:
        latf = float(lat)
        lngf = float(lng)
    except Exception:
        return False, "Latitude/Longitude must be numeric."

    if not (-90.0 <= latf <= 90.0):
        return False, "Latitude must be between -90 and 90."
    if not (-180.0 <= lngf <= 180.0):
        return False, "Longitude must be between -180 and 180."
    if latf == 0.0 and lngf == 0.0:
        return False, "Invalid coordinates (0,0)."
    return True, "OK"


# =========================
# Name / Address validations
# =========================

def validate_name(name: Any, min_len: int = 2, max_len: int = 60) -> Tuple[bool, str]:
    s = clean_text(name)
    if not s:
        return False, "Name is required."
    if len(s) < min_len:
        return False, f"Name must be at least {min_len} characters."
    if len(s) > max_len:
        return False, f"Name must be at most {max_len} characters."
    return True, "OK"


def validate_address(address: Any, min_len: int = 5, max_len: int = 200) -> Tuple[bool, str]:
    s = clean_text(address)
    if not s:
        return False, "Address is required."
    if len(s) < min_len:
        return False, f"Address must be at least {min_len} characters."
    if len(s) > max_len:
        return False, f"Address must be at most {max_len} characters."
    return True, "OK"


# =========================
# Generic helpers for routes
# =========================

def validate_required_fields(data: Dict[str, Any], fields: List[str]) -> Tuple[bool, str]:
    """
    Validates presence of fields in a payload dict.
    """
    missing = []
    for f in fields:
        if f not in data or clean_text(data.get(f)) == "":
            missing.append(f)
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, "OK"


def validate_driver_payload(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates driver create/update payload.
    Requires:
      name, mobile, dl_no, cab_no, vehicle_type(4/6), home_town(optional)
    """
    ok, msg = validate_required_fields(data, ["name", "mobile", "dl_no", "cab_no", "vehicle_type"])
    if not ok:
        return ok, msg

    ok, msg = validate_name(data.get("name"))
    if not ok:
        return ok, msg

    ok, msg = validate_mobile(data.get("mobile"))
    if not ok:
        return ok, msg

    ok, msg = validate_driving_license(data.get("dl_no"))
    if not ok:
        return ok, msg

    ok, msg = validate_vehicle_no(data.get("cab_no"))
    if not ok:
        return ok, msg

    try:
        vt = int(data.get("vehicle_type"))
        if vt not in (4, 6):
            return False, "vehicle_type must be 4 or 6."
    except Exception:
        return False, "vehicle_type must be numeric (4 or 6)."

    return True, "OK"


def validate_employee_payload(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates employee create/update payload.
    Requires:
      name, mobile, login_time, logout_time, address, employee_code(optional on create)
    """
    ok, msg = validate_required_fields(data, ["name", "mobile", "login_time", "logout_time", "address"])
    if not ok:
        return ok, msg

    ok, msg = validate_name(data.get("name"))
    if not ok:
        return ok, msg

    ok, msg = validate_mobile(data.get("mobile"))
    if not ok:
        return ok, msg

    ok, msg = validate_hhmm(data.get("login_time"))
    if not ok:
        return ok, msg

    ok, msg = validate_hhmm(data.get("logout_time"))
    if not ok:
        return ok, msg

    ok, msg = validate_address(data.get("address"))
    if not ok:
        return ok, msg

    return True, "OK"


def validate_admin_profile_payload(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates admin profile update payload.
    Requires:
      name, mobile, office_name, office_address
    """
    ok, msg = validate_required_fields(data, ["name", "mobile", "office_name", "office_address"])
    if not ok:
        return ok, msg

    ok, msg = validate_name(data.get("name"))
    if not ok:
        return ok, msg

    ok, msg = validate_mobile(data.get("mobile"))
    if not ok:
        return ok, msg

    ok, msg = validate_address(data.get("office_name"), min_len=2, max_len=80)
    if not ok:
        return ok, msg

    ok, msg = validate_address(data.get("office_address"), min_len=5, max_len=250)
    if not ok:
        return ok, msg

    return True, "OK"


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


def require_int(val: Any, name: str) -> int:
    try:
        if val is None or str(val).strip() == "":
            raise ValueError()
        return int(val)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be an integer.")


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


def validate_route_no_10(route_no: Any) -> bool:
    """Another alias."""
    ok, _ = validate_route_no(route_no)
    return ok
