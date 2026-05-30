# rg_travel_backend/utils/validation.py
"""
Input Validation Utilities
STEP 4: Security hardening - validate all user inputs

Functions:
- validate_mobile(mobile: str) -> bool
- validate_dl_number(dl: str) -> bool
- validate_cab_number(cab: str) -> bool
- validate_route_no(route_no: str) -> bool
- validate_image_file(filename: str) -> bool
- sanitize_filename(filename: str) -> str
"""

import re
import os
from typing import Optional


# Validation patterns
MOBILE_PATTERN = re.compile(r'^\d{10}$')
DL_PATTERN = re.compile(r'^[A-Za-z]{2}\d{13}$')
CAB_PATTERN = re.compile(r'^[A-Za-z]{2}\d{2}[A-Za-z]{2}\d{4}$')
ROUTE_NO_PATTERN = re.compile(r'^\d{10}[A-Z]{2}$')  # YYYY + 4digits + 2 letters

# File upload constraints
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
MAX_UPLOAD_SIZE_MB = 2
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_mobile(mobile: str, field_name: str = "Mobile") -> str:
    """
    Validate mobile number (exactly 10 digits).
    Returns sanitized mobile.
    Raises ValidationError if invalid.
    """
    if not mobile:
        raise ValidationError(f"{field_name} is required")
    
    # Remove spaces and dashes
    sanitized = mobile.strip().replace(' ', '').replace('-', '')
    
    if not MOBILE_PATTERN.match(sanitized):
        raise ValidationError(f"{field_name} must be exactly 10 digits")
    
    return sanitized


def validate_dl_number(dl: str) -> str:
    """
    Validate DL number (2 letters + 13 digits).
    Returns sanitized DL.
    """
    if not dl:
        raise ValidationError("DL number is required")
    
    sanitized = dl.strip().upper().replace(' ', '')
    
    if not DL_PATTERN.match(sanitized):
        raise ValidationError("DL number must be 2 letters + 13 digits (e.g., MH1234567890123)")
    
    return sanitized


def validate_cab_number(cab: str) -> str:
    """
    Validate cab/vehicle number (XX00XX0000 format, e.g., MH12AB1234).
    Returns sanitized cab number.
    """
    if not cab:
        raise ValidationError("Cab/Vehicle number is required")
    
    sanitized = cab.strip().upper().replace(' ', '').replace('-', '')
    
    if not CAB_PATTERN.match(sanitized):
        raise ValidationError("Cab number must be in format XX00XX0000 (e.g., MH12AB1234)")
    
    return sanitized


def validate_route_no(route_no: str) -> str:
    """
    Validate route number format (10 digits + 2 letters, e.g., 26020451FE).
    Returns sanitized route number.
    """
    if not route_no:
        raise ValidationError("Route number is required")
    
    sanitized = route_no.strip().upper().replace(' ', '')
    
    if not ROUTE_NO_PATTERN.match(sanitized):
        raise ValidationError("Invalid route number format (expected: YYYY4digits2letters)")
    
    return sanitized


def validate_image_file(filename: str, file_size: Optional[int] = None) -> str:
    """
    Validate uploaded image file.
    Checks:
    - File extension (jpg, jpeg, png, gif only)
    - File size (max 2MB if provided)
    
    Returns sanitized filename.
    """
    if not filename:
        raise ValidationError("Filename is required")
    
    # Check extension
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Only image files allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")
    
    # Check size if provided
    if file_size is not None and file_size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(f"File size must be less than {MAX_UPLOAD_SIZE_MB}MB")
    
    return sanitize_filename(filename)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    Removes unsafe characters and limits length.
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 50:
        name = name[:50]
    
    return name + ext


def validate_time_format(time_str: str, field_name: str = "Time") -> str:
    """
    Validate time string in HH:MM format.
    Returns sanitized time.
    """
    if not time_str:
        raise ValidationError(f"{field_name} is required")
    
    time_pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
    sanitized = time_str.strip()
    
    if not time_pattern.match(sanitized):
        raise ValidationError(f"{field_name} must be in HH:MM format (e.g., 09:30)")
    
    return sanitized


def validate_date_format(date_str: str, field_name: str = "Date") -> str:
    """
    Validate date string in YYYY-MM-DD format.
    Returns sanitized date.
    """
    if not date_str:
        raise ValidationError(f"{field_name} is required")
    
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    sanitized = date_str.strip()
    
    if not date_pattern.match(sanitized):
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format")
    
    return sanitized


def validate_password_strength(password: str, min_length: int = 6) -> None:
    """
    Validate password strength.
    Raises ValidationError if password is weak.
    """
    if not password:
        raise ValidationError("Password is required")
    
    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters")
    
    # Optional: Add more strength checks
    # if not re.search(r'[A-Z]', password):
    #     raise ValidationError("Password must contain at least one uppercase letter")
    # if not re.search(r'[0-9]', password):
    #     raise ValidationError("Password must contain at least one number")
