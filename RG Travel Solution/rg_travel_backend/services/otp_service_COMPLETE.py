"""
Complete Backend OTP Service Implementation
rg_travel_backend/services/otp_service.py

This file provides all OTP operations needed for the project.
"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import json

# Configure from environment
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_VERIFY_ATTEMPTS = 3

class OTPError(Exception):
    """Custom OTP Exception"""
    pass


class OTPService:
    """Handles OTP generation, verification, and management"""
    
    # In-memory storage (use Redis/DB in production)
    _otps: Dict[str, Dict] = {}
    _verify_attempts: Dict[str, int] = {}
    
    @staticmethod
    def _hash_otp(otp: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    @staticmethod
    def _generate_random_otp(length: int = OTP_LENGTH) -> str:
        """Generate random numeric OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @classmethod
    def generate_otp(
        cls,
        route_no: str,
        otp_type: str = "start",  # "start" or "end"
        expiry_minutes: int = OTP_EXPIRY_MINUTES
    ) -> Dict[str, str]:
        """
        Generate OTP for a trip
        
        Args:
            route_no: Route number
            otp_type: "start" or "end"
            expiry_minutes: OTP expiry time in minutes
            
        Returns:
            {
                "otp": "123456",
                "expires_at": "ISO timestamp",
                "route_no": "RG20260202001"
            }
        """
        try:
            # Generate OTP
            otp = cls._generate_random_otp()
            otp_hash = cls._hash_otp(otp)
            
            # Calculate expiry
            expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
            
            # Store OTP record
            otp_key = f"{route_no}:{otp_type}"
            cls._otps[otp_key] = {
                "route_no": route_no,
                "otp_type": otp_type,
                "otp_hash": otp_hash,
                "otp": otp,  # Keep for testing (remove in production)
                "expires_at": expires_at.isoformat(),
                "is_used": False,
                "created_at": datetime.utcnow().isoformat(),
                "verify_attempts": 0,
            }
            
            # Reset verify attempts counter
            cls._verify_attempts[otp_key] = 0
            
            return {
                "otp": otp,
                "expires_at": expires_at.isoformat(),
                "route_no": route_no,
            }
        
        except Exception as e:
            raise OTPError(f"Failed to generate OTP: {str(e)}")
    
    @classmethod
    def verify_otp(
        cls,
        route_no: str,
        otp: str,
        otp_type: str = "start"
    ) -> Tuple[bool, str]:
        """
        Verify OTP for a trip
        
        Args:
            route_no: Route number
            otp: OTP provided by employee/driver
            otp_type: "start" or "end"
            
        Returns:
            (success: bool, message: str)
        """
        try:
            otp_key = f"{route_no}:{otp_type}"
            
            # Check if OTP exists
            if otp_key not in cls._otps:
                return False, "OTP not found for this trip"
            
            otp_record = cls._otps[otp_key]
            
            # Check if already used
            if otp_record["is_used"]:
                return False, "OTP already used"
            
            # Check if expired
            expires_at = datetime.fromisoformat(otp_record["expires_at"])
            if datetime.utcnow() > expires_at:
                otp_record["is_used"] = True
                return False, "OTP has expired"
            
            # Check attempt limit
            if cls._verify_attempts.get(otp_key, 0) >= MAX_VERIFY_ATTEMPTS:
                otp_record["is_used"] = True
                return False, "Maximum verification attempts exceeded"
            
            # Verify OTP hash
            otp_hash = cls._hash_otp(otp)
            if otp_hash != otp_record["otp_hash"]:
                cls._verify_attempts[otp_key] = cls._verify_attempts.get(otp_key, 0) + 1
                return False, "Invalid OTP"
            
            # Mark as used
            otp_record["is_used"] = True
            otp_record["used_at"] = datetime.utcnow().isoformat()
            
            return True, "OTP verified successfully"
        
        except Exception as e:
            raise OTPError(f"Failed to verify OTP: {str(e)}")
    
    @classmethod
    def get_otp_status(cls, route_no: str, otp_type: str = "start") -> Dict:
        """Get OTP status for a trip"""
        otp_key = f"{route_no}:{otp_type}"
        
        if otp_key not in cls._otps:
            return {"exists": False}
        
        record = cls._otps[otp_key]
        return {
            "exists": True,
            "is_used": record["is_used"],
            "expires_at": record["expires_at"],
            "created_at": record["created_at"],
        }
    
    @classmethod
    def invalidate_otp(cls, route_no: str, otp_type: str = "start") -> bool:
        """Invalidate OTP (e.g., when trip is cancelled)"""
        otp_key = f"{route_no}:{otp_type}"
        if otp_key in cls._otps:
            cls._otps[otp_key]["is_used"] = True
            return True
        return False
    
    @classmethod
    def clean_expired_otps(cls) -> int:
        """Remove expired OTPs from memory"""
        expired_keys = []
        
        for otp_key, record in cls._otps.items():
            expires_at = datetime.fromisoformat(record["expires_at"])
            if datetime.utcnow() > expires_at:
                expired_keys.append(otp_key)
        
        for key in expired_keys:
            del cls._otps[key]
            cls._verify_attempts.pop(key, None)
        
        return len(expired_keys)


# For backward compatibility
def generate_otp(route_no: str, otp_type: str = "start"):
    """Function-based interface"""
    return OTPService.generate_otp(route_no, otp_type)


def verify_otp(route_no: str, otp: str, otp_type: str = "start"):
    """Function-based interface"""
    return OTPService.verify_otp(route_no, otp, otp_type)
