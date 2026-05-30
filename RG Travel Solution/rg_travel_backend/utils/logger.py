# rg_travel_backend/utils/logger.py
"""
Centralized Logging Utility
STEP 4: Production-ready logging with levels and trip lifecycle events

Usage:
    from utils.logger import log_info, log_warning, log_error, log_trip_event
    
    log_info("Trip created", trip_id=123, route_no="26020451FE")
    log_trip_event("trip_started", trip_id=123, driver_id=1)
    log_error("OTP verification failed", trip_id=123, reason="expired")
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # Add FileHandler for production
        # logging.FileHandler('logs/rg_travel.log')
    ]
)

logger = logging.getLogger('rg_travel')


def _format_extra(extra: Optional[Dict[str, Any]] = None) -> str:
    """Format extra data as key=value pairs."""
    if not extra:
        return ""
    pairs = [f"{k}={v}" for k, v in extra.items()]
    return " | " + " | ".join(pairs)


def log_info(message: str, **kwargs):
    """Log informational message."""
    logger.info(message + _format_extra(kwargs))


def log_warning(message: str, **kwargs):
    """Log warning message."""
    logger.warning(message + _format_extra(kwargs))


def log_error(message: str, **kwargs):
    """Log error message."""
    logger.error(message + _format_extra(kwargs))


def log_trip_event(event: str, trip_id: int, **kwargs):
    """
    Log trip lifecycle event.
    
    Events:
    - trip_created
    - trip_assigned
    - trip_started
    - trip_completed
    - trip_cancelled
    - otp_generated
    - otp_verified
    - otp_failed
    - no_show_marked
    - swap_requested
    - swap_approved
    """
    log_info(f"TRIP_EVENT: {event}", trip_id=trip_id, **kwargs)


def log_auth_event(event: str, role: str, user_id: str, **kwargs):
    """
    Log authentication event.
    
    Events:
    - login_success
    - login_failed
    - logout
    - token_expired
    - unauthorized_access
    """
    log_info(f"AUTH_EVENT: {event}", role=role, user_id=user_id, **kwargs)


def log_admin_action(action: str, admin_id: str, target_type: str, target_id: Any, **kwargs):
    """
    Log admin actions for audit trail.
    
    Actions:
    - approved_driver
    - rejected_driver
    - approved_employee
    - cancelled_trip
    - approved_swap
    """
    log_info(
        f"ADMIN_ACTION: {action}",
        admin_id=admin_id,
        target_type=target_type,
        target_id=target_id,
        **kwargs
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)
