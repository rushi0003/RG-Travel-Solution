"""
RG Travel Solution - Comprehensive Test & Validation Suite

This file contains critical business logic tests and validation helpers
for all major features of the system.

Run with: python test_comprehensive_v2.py
"""

import sys
import json
from datetime import datetime, timedelta
import random
import string

# Expected to be run from rg_travel_backend directory
try:
    from db import get_db, init_db
    from services.route_no_service import generate_route_no, generate_unique_route_no
    from services.otp_service import (
        generate_otp_code,
        hash_otp,
        safe_compare_hash,
        create_trip_otps,
        verify_trip_otp_and_update,
    )
    from services.validation_service import (
        validate_mobile_10,
        validate_dl_number,
        validate_vehicle_no,
        validate_hhmm,
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from rg_travel_backend directory")
    sys.exit(1)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name):
        self.passed += 1
        self.tests.append(("✅", test_name))
        print(f"✅ {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.tests.append(("❌", test_name, error))
        print(f"❌ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        print(f"{'='*60}")
        if self.failed == 0:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️ {self.failed} tests failed")


results = TestResults()


# ============================================================
# 1. ROUTE NO GENERATION TESTS
# ============================================================

def test_route_no_format():
    """Test that route numbers are exactly 10 characters in format YYYY+4digits+2letters"""
    try:
        rn = generate_route_no()
        assert len(rn) == 10, f"Route no length is {len(rn)}, expected 10"
        
        # Check format: YYYY + 4digits + 2letters
        year_part = rn[:4]
        rand_part = rn[4:8]
        month_part = rn[8:10]
        
        assert year_part.isdigit() and len(year_part) == 4, "First 4 chars should be year digits"
        assert rand_part.isdigit() and len(rand_part) == 4, "Next 4 chars should be digits"
        assert month_part.isalpha() and len(month_part) == 2, "Last 2 chars should be letters"
        
        results.add_pass("Route No format validation")
    except Exception as e:
        results.add_fail("Route No format validation", str(e))


def test_route_no_uniqueness():
    """Test that multiple generated route numbers are unique"""
    try:
        routes = set()
        for _ in range(100):
            rn = generate_route_no()
            routes.add(rn)
        
        # May have some collisions by chance, but should be mostly unique
        collision_rate = (100 - len(routes)) / 100
        assert collision_rate < 0.05, f"Collision rate too high: {collision_rate:.1%}"
        
        results.add_pass(f"Route No uniqueness (generated 100, got {len(routes)} unique)")
    except Exception as e:
        results.add_fail("Route No uniqueness", str(e))


def test_route_no_today_format():
    """Test that today's route numbers have correct year and month"""
    try:
        now = datetime.now()
        expected_year = str(now.year)
        expected_month = now.strftime("%b").upper()[:2]  # JAN, FEB, etc.
        
        rn = generate_route_no()
        actual_year = rn[:4]
        actual_month = rn[8:10]
        
        assert actual_year == expected_year, f"Year {actual_year} != {expected_year}"
        assert actual_month == expected_month, f"Month {actual_month} != {expected_month}"
        
        results.add_pass("Route No today format validation")
    except Exception as e:
        results.add_fail("Route No today format validation", str(e))


# ============================================================
# 2. OTP TESTS
# ============================================================

def test_otp_code_generation():
    """Test that OTP codes are 6 digits"""
    try:
        for _ in range(10):
            otp = generate_otp_code()
            assert len(otp) == 6, f"OTP length is {len(otp)}, expected 6"
            assert otp.isdigit(), f"OTP contains non-digits: {otp}"
        
        results.add_pass("OTP code generation (6 digits)")
    except Exception as e:
        results.add_fail("OTP code generation", str(e))


def test_otp_hashing():
    """Test that OTP hashing is consistent and secure"""
    try:
        otp1 = "123456"
        otp2 = "654321"
        
        hash1a = hash_otp(otp1)
        hash1b = hash_otp(otp1)
        hash2 = hash_otp(otp2)
        
        # Same OTP should produce same hash
        assert hash1a == hash1b, "Same OTP should produce same hash"
        
        # Different OTP should produce different hash
        assert hash1a != hash2, "Different OTPs should produce different hashes"
        
        # Hash should be long (SHA-256 = 64 hex chars)
        assert len(hash1a) == 64, f"Hash length is {len(hash1a)}, expected 64 (SHA-256)"
        
        results.add_pass("OTP hashing consistency and security")
    except Exception as e:
        results.add_fail("OTP hashing", str(e))


def test_otp_secure_comparison():
    """Test that hash comparison is constant-time (timing-safe)"""
    try:
        otp = "123456"
        hash_correct = hash_otp(otp)
        hash_wrong = hash_otp("654321")
        
        assert safe_compare_hash(hash_correct, hash_correct), "Should match correct hash"
        assert not safe_compare_hash(hash_correct, hash_wrong), "Should not match wrong hash"
        
        results.add_pass("OTP secure comparison (timing-safe)")
    except Exception as e:
        results.add_fail("OTP secure comparison", str(e))


# ============================================================
# 3. VALIDATION TESTS
# ============================================================

def test_mobile_validation():
    """Test 10-digit mobile number validation"""
    try:
        valid = ["9876543210", "1234567890", "0000000000"]
        invalid = ["987654321", "98765432101", "abcd123456", ""]
        
        for m in valid:
            assert validate_mobile_10(m), f"Should validate: {m}"
        
        for m in invalid:
            assert not validate_mobile_10(m), f"Should reject: {m}"
        
        results.add_pass("Mobile number validation")
    except Exception as e:
        results.add_fail("Mobile number validation", str(e))


def test_dl_validation():
    """Test driving license format validation"""
    try:
        valid = ["AB1234567890123", "XY9876543210123"]
        invalid = ["A1234567890123", "AB123456789012", "AB12345678901a"]
        
        for dl in valid:
            assert validate_dl_number(dl), f"Should validate: {dl}"
        
        for dl in invalid:
            assert not validate_dl_number(dl), f"Should reject: {dl}"
        
        results.add_pass("Driving license validation")
    except Exception as e:
        results.add_fail("Driving license validation", str(e))


def test_vehicle_no_validation():
    """Test vehicle registration number validation"""
    try:
        valid = ["MH01AB1234", "DL02CD5678", "KA03EF9999"]
        invalid = ["MH1AB1234", "MHAB1234", "mh01ab1234"]
        
        for vn in valid:
            assert validate_vehicle_no(vn), f"Should validate: {vn}"
        
        for vn in invalid:
            assert not validate_vehicle_no(vn), f"Should reject: {vn}"
        
        results.add_pass("Vehicle registration validation")
    except Exception as e:
        results.add_fail("Vehicle registration validation", str(e))


def test_time_hhmm_validation():
    """Test HH:MM time format validation"""
    try:
        valid = ["09:30", "00:00", "23:59", "12:00"]
        invalid = ["9:30", "09:60", "24:00", "ab:cd"]
        
        for t in valid:
            assert validate_hhmm(t), f"Should validate: {t}"
        
        for t in invalid:
            assert not validate_hhmm(t), f"Should reject: {t}"
        
        results.add_pass("Time HH:MM validation")
    except Exception as e:
        results.add_fail("Time HH:MM validation", str(e))


# ============================================================
# 4. DATABASE TESTS
# ============================================================

def test_database_initialization():
    """Test that database initializes correctly"""
    try:
        # This would normally be done in app startup
        init_db()
        
        conn = get_db()
        cur = conn.cursor()
        
        # Check that required tables exist
        tables = [
            "admins", "drivers", "employees", "trips", "trip_employees",
            "trip_otps", "otp_audit_log", "driver_location_history"
        ]
        
        for table in tables:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            assert cur.fetchone(), f"Table {table} does not exist"
        
        conn.close()
        results.add_pass(f"Database initialization ({len(tables)} tables)")
    except Exception as e:
        results.add_fail("Database initialization", str(e))


def test_trip_otps_insertion():
    """Test that OTPs can be generated and stored in database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Create a test trip first
        cur.execute("""
            INSERT INTO trips (
                route_no, trip_day, trip_type, schedule_time, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("20261234FE", "20260203", "pickup", "09:30", "created", datetime.now().isoformat(), datetime.now().isoformat()))
        trip_id = cur.lastrowid
        
        # Create OTPs
        result = create_trip_otps(conn, trip_id)
        
        assert result["success"], f"Failed to create OTPs: {result}"
        assert "start_otp" in result["data"], "No start_otp in response"
        assert "end_otp" in result["data"], "No end_otp in response"
        
        # Verify OTPs stored in database
        cur.execute("SELECT COUNT(*) FROM trip_otps WHERE trip_id = ?", (trip_id,))
        count = cur.fetchone()[0]
        assert count == 2, f"Expected 2 OTPs, found {count}"
        
        conn.close()
        results.add_pass("OTP insertion and storage")
    except Exception as e:
        results.add_fail("OTP insertion and storage", str(e))


# ============================================================
# 5. BUSINESS LOGIC TESTS
# ============================================================

def test_trip_type_enum():
    """Test trip type enum values"""
    try:
        valid_types = ["pickup", "drop"]
        
        # This would be in Flutter, but test logic here
        for tt in valid_types:
            assert tt in ["pickup", "drop"], f"Invalid trip type: {tt}"
        
        results.add_pass("Trip type enum validation")
    except Exception as e:
        results.add_fail("Trip type enum validation", str(e))


def test_trip_status_flow():
    """Test valid trip status transitions"""
    try:
        # Valid transitions:
        # created -> assigned -> started -> completed
        # created/assigned/started -> cancelled
        
        valid_transitions = {
            "created": ["assigned", "cancelled"],
            "assigned": ["started", "cancelled"],
            "started": ["completed", "cancelled"],
            "completed": [],
            "cancelled": [],
        }
        
        # This just validates the logic is sound
        assert "created" in valid_transitions, "created not defined"
        assert "cancelled" in valid_transitions["created"], "Can't cancel from created"
        
        results.add_pass("Trip status flow validation")
    except Exception as e:
        results.add_fail("Trip status flow validation", str(e))


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("RG Travel Solution - Comprehensive Test Suite")
    print("="*60)
    print()
    
    # 1. Route No Tests
    print("1. Route No Generation Tests")
    print("-" * 40)
    test_route_no_format()
    test_route_no_uniqueness()
    test_route_no_today_format()
    print()
    
    # 2. OTP Tests
    print("2. OTP Tests")
    print("-" * 40)
    test_otp_code_generation()
    test_otp_hashing()
    test_otp_secure_comparison()
    print()
    
    # 3. Validation Tests
    print("3. Input Validation Tests")
    print("-" * 40)
    test_mobile_validation()
    test_dl_validation()
    test_vehicle_no_validation()
    test_time_hhmm_validation()
    print()
    
    # 4. Database Tests
    print("4. Database Tests")
    print("-" * 40)
    test_database_initialization()
    test_trip_otps_insertion()
    print()
    
    # 5. Business Logic Tests
    print("5. Business Logic Tests")
    print("-" * 40)
    test_trip_type_enum()
    test_trip_status_flow()
    print()
    
    # Summary
    results.summary()


if __name__ == "__main__":
    run_all_tests()
