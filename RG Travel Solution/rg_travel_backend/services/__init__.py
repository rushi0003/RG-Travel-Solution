# rg_travel_backend/services/__init__.py
"""
RG Travel Solution — services package
====================================

This __init__.py makes it easy to import services like:

    from services import (
        grouping_service,
        routing_service,
        otp_service,
        route_no_service,
        tracking_service,
        validation_service,
    )

or directly import key functions:

    from services import (
        create_trip_otps,
        verify_trip_otp_and_update,
        generate_unique_route_no,
        build_multi_stop_route,
        update_driver_location,
        validate_driver_payload,
    )

✅ This file does NOT create routes.
Routes must call these service functions inside your routes/*.py.

"""

# Export whole modules (nice for clarity)
from . import grouping_service
from . import routing_service
from . import otp_service
from . import route_no_service
from . import tracking_service
from . import validation_service
from . import nominatim_geocoding_service

# -----------------------
# OTP service exports
# -----------------------
from .otp_service import (
    create_trip_otps,
    get_trip_otp_status,
    verify_trip_otp_and_update,
    verify_employee_trip_otp,
    get_pending_employee_otp_ids,
    # API wrappers (not present here) are intentionally omitted.
)

# -----------------------
# Route No service exports
# -----------------------
from .route_no_service import (
    generate_route_no,
    generate_unique_route_no,
    reserve_route_no_for_trip,
    api_generate_route_no,
    api_reserve_route_no,
    is_route_no_exists,
    format_info as route_no_format_info,
)

# -----------------------
# Routing service exports
# -----------------------
from .routing_service import (
    build_multi_stop_route,
    compute_round_trip_km,
    geocode_address,
    reverse_geocode,
    api_build_route,
)

# -----------------------
# Nominatim geocoding exports
# -----------------------
from .nominatim_geocoding_service import (
    geocode_address_nominatim,
    ensure_geocode_cache_table,
)

# -----------------------
# Tracking service exports
# -----------------------
from .tracking_service import (
    update_driver_location,
    set_driver_online_status,
    get_driver_latest_location,
    get_driver_location_history,
    get_online_drivers,
    get_assigned_driver_location_by_trip,
    get_assigned_driver_location_by_route_no,
    api_update_location,
    api_get_online_drivers,
    api_get_driver_latest,
    api_get_trip_driver_location,
    api_get_route_driver_location,
)

# -----------------------
# Validation service exports
# -----------------------
from .validation_service import (
    clean_text,
    validate_mobile,
    assert_mobile,
    validate_driving_license,
    assert_driving_license,
    validate_vehicle_no,
    assert_vehicle_no,
    validate_otp,
    validate_route_no,
    validate_hhmm,
    validate_coord,
    validate_name,
    validate_address,
    validate_required_fields,
    validate_driver_payload,
    validate_employee_payload,
    validate_admin_profile_payload,
)

# -----------------------
# Grouping service exports
# NOTE: You asked earlier for grouping_service.py
# If your file has different function names, update here accordingly.
# -----------------------
try:
    from .grouping_service import (
        # Common naming suggestions (adjust if your file differs)
        create_groups,
        api_create_groups,
        build_groups_for_trip,
    )
except Exception:
    # Grouping service may not yet be implemented or has different exports.
    # Keeping package import safe.
    pass


__all__ = [
    # modules
    "grouping_service",
    "routing_service",
    "otp_service",
    "route_no_service",
    "tracking_service",
    "validation_service",
    "nominatim_geocoding_service",

    # otp
    "create_trip_otps",
    "get_trip_otp_status",
    "verify_trip_otp_and_update",
    "verify_employee_trip_otp",
    "get_pending_employee_otp_ids",
    # api_* aliases removed to match actual exports

    # route no
    "generate_route_no",
    "generate_unique_route_no",
    "reserve_route_no_for_trip",
    "api_generate_route_no",
    "api_reserve_route_no",
    "is_route_no_exists",
    "route_no_format_info",

    # routing
    "build_multi_stop_route",
    "compute_round_trip_km",
    "geocode_address",
    "reverse_geocode",
    "api_build_route",

    # nominatim geocoding
    "geocode_address_nominatim",
    "ensure_geocode_cache_table",

    # tracking
    "update_driver_location",
    "set_driver_online_status",
    "get_driver_latest_location",
    "get_driver_location_history",
    "get_online_drivers",
    "get_assigned_driver_location_by_trip",
    "get_assigned_driver_location_by_route_no",
    "api_update_location",
    "api_get_online_drivers",
    "api_get_driver_latest",
    "api_get_trip_driver_location",
    "api_get_route_driver_location",

    # validation
    "clean_text",
    "validate_mobile",
    "assert_mobile",
    "validate_driving_license",
    "assert_driving_license",
    "validate_vehicle_no",
    "assert_vehicle_no",
    "validate_otp",
    "validate_route_no",
    "validate_hhmm",
    "validate_coord",
    "validate_name",
    "validate_address",
    "validate_required_fields",
    "validate_driver_payload",
    "validate_employee_payload",
    "validate_admin_profile_payload",
]
