# rg_travel_backend/services/audit_service.py
"""
Centralized audit logging for tracking security events.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

AUDIT_LOG_FILE = LOGS_DIR / "tracking_audit.log"

# Configure audit logger
audit_logger = logging.getLogger("tracking_audit")
audit_logger.setLevel(logging.INFO)

# File handler with rotation
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler(
    AUDIT_LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
handler.setLevel(logging.INFO)

# Format: timestamp | level | event_type | details_json
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
audit_logger.addHandler(handler)

# Prevent propagation to root logger
audit_logger.propagate = False


def log_tracking_event(
    event_type: str,
    user_id: str,
    role: str,
    route_no: str = None,
    success: bool = True,
    reason: str = None,
    extra: dict = None
):
    """
    Log a tracking security event.
    
    Args:
        event_type: 'location_update', 'socket_join', 'socket_disconnect', 'unauthorized_access', 'rate_limit'
        user_id: User/driver/employee/admin ID
        role: 'admin', 'driver', 'employee'
        route_no: Route number (if applicable)
        success: Whether the action succeeded
        reason: Reason for failure (if applicable)
        extra: Additional data to log
    """
    event_data = {
        "event": event_type,
        "user_id": user_id,
        "role": role,
        "success": success,
    }
    
    if route_no:
        event_data["route_no"] = route_no
    if reason:
        event_data["reason"] = reason
    if extra:
        event_data["extra"] = extra
    
    # Convert to JSON string
    log_message = json.dumps(event_data)
    
    if success:
        audit_logger.info(log_message)
    else:
        audit_logger.warning(log_message)


def log_location_update(driver_id: str, route_no: str, success: bool, reason: str = None):
    """Log driver location update attempt."""
    log_tracking_event(
        event_type="location_update",
        user_id=driver_id,
        role="driver",
        route_no=route_no,
        success=success,
        reason=reason
    )


def log_socket_join(user_id: str, role: str, route_no: str, success: bool, reason: str = None):
    """Log socket room join attempt."""
    log_tracking_event(
        event_type="socket_join",
        user_id=user_id,
        role=role,
        route_no=route_no,
        success=success,
        reason=reason
    )


def log_unauthorized_access(user_id: str, role: str, route_no: str, action: str, reason: str):
    """Log unauthorized access attempt."""
    log_tracking_event(
        event_type="unauthorized_access",
        user_id=user_id,
        role=role,
        route_no=route_no,
        success=False,
        reason=reason,
        extra={"action": action}
    )


def log_rate_limit(user_id: str, role: str, route_no: str = None):
    """Log rate limit violation."""
    log_tracking_event(
        event_type="rate_limit",
        user_id=user_id,
        role=role,
        route_no=route_no,
        success=False,
        reason="Rate limit exceeded"
    )
