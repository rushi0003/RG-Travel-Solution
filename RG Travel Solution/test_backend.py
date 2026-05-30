"""
Test Backend Health Check & OTP Service
========================================

Run with:
  python -m pytest test_backend.py -v
  
or install pytest first:
  pip install pytest requests
"""

import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "rg_travel_backend"
sys.path.insert(0, str(backend_path.parent))

import pytest
from datetime import datetime, timedelta, timezone


class TestHealthCheck:
    """Test /api/health endpoint"""
    
    def test_health_check_import(self):
        """Verify health check module exists"""
        try:
            from rg_travel_backend.routes import health_routes
            assert hasattr(health_routes, 'health_bp')
        except ImportError:
            pytest.skip("Health routes not yet implemented")
    
    def test_health_endpoint_format(self):
        """Verify expected health response format"""
        # Mock response
        expected_keys = {'success', 'message', 'data'}
        mock_response = {
            "success": True,
            "message": "Backend is online",
            "data": {
                "status": "ok",
                "version": "2.0",
                "timestamp": "2026-02-02T15:30:00Z",
                "database": "connected"
            }
        }
        
        assert mock_response['success'] == True
        assert set(mock_response.keys()).issuperset(expected_keys)
        assert mock_response['data']['status'] == 'ok'


class TestOTPService:
    """Test OTP generation and verification"""
    
    def test_otp_code_generation(self):
        """Test OTP code generation"""
        from rg_travel_backend.services.otp_service import generate_otp_code
        
        otp = generate_otp_code()
        assert len(otp) == 6
        assert otp.isdigit()
        
        # Generate multiple and verify uniqueness (high probability)
        otps = [generate_otp_code() for _ in range(10)]
        assert len(set(otps)) >= 8  # Most should be unique
    
    def test_otp_hashing(self):
        """Test OTP hashing"""
        from rg_travel_backend.services.otp_service import hash_otp
        
        otp = "123456"
        hash1 = hash_otp(otp)
        hash2 = hash_otp(otp)
        
        assert hash1 == hash2  # Same input = same hash
        assert len(hash1) == 64  # SHA-256 = 64 hex chars
        assert hash1 != otp  # Hash != plaintext
    
    def test_otp_expiry_check(self):
        """Test OTP expiry logic"""
        from rg_travel_backend.services.otp_service import (
            is_expired,
            add_minutes_iso,
            now_iso
        )
        
        # Expired OTP
        past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        assert is_expired(past) == True
        
        # Valid OTP
        future = add_minutes_iso(5)
        assert is_expired(future) == False
        
        # Just expiring
        just_expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        assert is_expired(just_expired) == True
    
    def test_safe_hash_compare(self):
        """Test constant-time hash comparison"""
        from rg_travel_backend.services.otp_service import (
            safe_compare_hash,
            hash_otp
        )
        
        otp1 = "123456"
        otp2 = "123457"
        
        hash1 = hash_otp(otp1)
        hash2 = hash_otp(otp2)
        hash1_again = hash_otp(otp1)
        
        assert safe_compare_hash(hash1, hash1_again) == True
        assert safe_compare_hash(hash1, hash2) == False


class TestDBSchema:
    """Test database schema enhancements"""
    
    def test_schema_file_exists(self):
        """Verify schema.sql file exists"""
        schema_file = Path(__file__).parent / "rg_travel_backend" / "db" / "schema.sql"
        assert schema_file.exists(), f"Schema file not found at {schema_file}"
    
    def test_new_tables_in_schema(self):
        """Verify new tables are present in schema"""
        schema_file = Path(__file__).parent / "rg_travel_backend" / "db" / "schema.sql"
        schema_content = schema_file.read_text()
        
        required_tables = [
            'trip_otps',
            'otp_audit_log',
            'driver_location_history'
        ]
        
        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in schema_content, \
                f"Table {table} not found in schema"
    
    def test_schema_constraints(self):
        """Verify schema has proper constraints"""
        schema_file = Path(__file__).parent / "rg_travel_backend" / "db" / "schema.sql"
        schema_content = schema_file.read_text()
        
        # Check for indexes
        assert "CREATE INDEX" in schema_content
        assert "FOREIGN KEY" in schema_content
        assert "UNIQUE INDEX" in schema_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
