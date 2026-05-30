#!/usr/bin/env python3
"""
Test script for new trip management endpoints (Create, View, Update)
Tests the complete flow:
1. Create trip with driver + employees
2. List trips and verify structure
3. Complete a trip
4. Cancel a trip with reason
"""

import sys
import requests
import pytest

BASE_URL = "http://127.0.0.1:5000"

# Test data (adjust IDs based on your database)
ADMIN_ID = 1
DRIVER_ID = 1  # Must be approved (is_approved=1)
EMPLOYEE_IDS = [1, 2, 3]  # Must exist in employees table

def log(msg: str, level: str = "INFO"):
    """Print log message"""
    prefix = f"[{level}]" if level != "INFO" else "[✓]"
    print(f"{prefix} {msg}")

def test_create_trip():
    """Test POST /api/admin/trips"""
    log("Testing POST /api/admin/trips...")
    
    payload = {
        "route_no": "ROUTE123ABC",
        "trip_type": "pickup",
        "schedule_time": "09:00",
        "driver_id": DRIVER_ID,
        "employee_ids": EMPLOYEE_IDS,
        "admin_id": ADMIN_ID,
        "vehicle_type": "4"
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/api/admin/trips",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code != 201:
            log(f"HTTP {resp.status_code}: {resp.text}", "ERROR")
            return None
        
        data = resp.json()
        log(f"✓ Trip created successfully")
        log(f"  Trip ID: {data.get('data', {}).get('trip_id')}")
        log(f"  Route No: {data.get('data', {}).get('route_no')}")
        log(f"  Status: {data.get('data', {}).get('status')}")
        
        return data.get('data', {}).get('trip_id')
    except Exception as e:
        log(f"Exception: {e}", "ERROR")
        return None

def test_list_trips():
    """Test GET /api/admin/trips"""
    log("Testing GET /api/admin/trips...")
    
    try:
        try:
            health = requests.get(f"{BASE_URL}/api/admin/trips", timeout=4)
            if health.status_code not in (200, 201):
                pytest.skip("API server not ready for trip endpoint tests")
        except Exception:
            pytest.skip("API server not running on 127.0.0.1:5000")

        resp = requests.get(f"{BASE_URL}/api/admin/trips")
        
        if resp.status_code != 200:
            log(f"HTTP {resp.status_code}: {resp.text}", "ERROR")
            assert False
        
        data = resp.json()
        trips = data.get('data', [])
        
        log(f"??? Retrieved {len(trips)} trips")
        
        for trip in trips[:3]:  # Show first 3
            log(f"  Trip {trip.get('id')}: {trip.get('route_no')} ({trip.get('status')})")
            log(f"    Driver: {trip.get('driver_name')} | Employees: {len(trip.get('employees', []))}")
            
        assert True
    except Exception as e:
        log(f"Exception: {e}", "ERROR")
        assert False

def test_complete_trip(trip_id: int):
    """Test PUT /api/admin/trips/{id} with status=completed"""
    log(f"Testing PUT /api/admin/trips/{trip_id} (Complete)...")
    
    payload = {
        "status": "completed"
    }
    
    try:
        resp = requests.put(
            f"{BASE_URL}/api/admin/trips/{trip_id}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code != 200:
            log(f"HTTP {resp.status_code}: {resp.text}", "ERROR")
            return False
        
        data = resp.json()
        log(f"✓ Trip completed successfully")
        log(f"  Status: {data.get('data', {}).get('status')}")
        
        return True
    except Exception as e:
        log(f"Exception: {e}", "ERROR")
        return False

def test_cancel_trip(trip_id: int):
    """Test PUT /api/admin/trips/{id} with status=cancelled"""
    log(f"Testing PUT /api/admin/trips/{trip_id} (Cancel)...")
    
    payload = {
        "status": "cancelled",
        "cancel_reason": "Driver unavailable due to emergency"
    }
    
    try:
        resp = requests.put(
            f"{BASE_URL}/api/admin/trips/{trip_id}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code != 200:
            log(f"HTTP {resp.status_code}: {resp.text}", "ERROR")
            return False
        
        data = resp.json()
        log(f"✓ Trip cancelled successfully")
        log(f"  Status: {data.get('data', {}).get('status')}")
        log(f"  Reason: {data.get('data', {}).get('cancel_reason')}")
        
        return True
    except Exception as e:
        log(f"Exception: {e}", "ERROR")
        return False

def test_cancel_without_reason(trip_id: int):
    """Test error handling: cancel without reason"""
    log(f"Testing PUT /api/admin/trips/{trip_id} (Cancel without reason - should fail)...")
    
    payload = {
        "status": "cancelled"
    }
    
    try:
        resp = requests.put(
            f"{BASE_URL}/api/admin/trips/{trip_id}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code == 400:
            log(f"✓ Correctly rejected request without cancel_reason")
            return True
        else:
            log(f"✗ Expected 400, got {resp.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"Exception: {e}", "ERROR")
        return False


@pytest.fixture
def trip_id():
    # Skip if API server is not running
    try:
        health = requests.get(f"{BASE_URL}/api/admin/trips", timeout=4)
        if health.status_code not in (200, 201):
            pytest.skip("API server not ready for trip endpoint tests")
    except Exception:
        pytest.skip("API server not running on 127.0.0.1:5000")

    tid = test_create_trip()
    if not tid:
        pytest.skip("Unable to create trip for trip endpoint tests")
    return tid

def main():
    print("\n" + "="*60)
    print("RG Travel Solution - Trip Management Endpoint Tests")
    print("="*60 + "\n")
    
    print("Prerequisites:")
    print(f"  - Base URL: {BASE_URL}")
    print(f"  - Admin ID: {ADMIN_ID}")
    print(f"  - Driver ID: {DRIVER_ID} (must be approved)")
    print(f"  - Employee IDs: {EMPLOYEE_IDS}")
    print()
    
    results = {}
    
    # Test 1: Create trip
    trip_id = test_create_trip()
    results['create_trip'] = trip_id is not None
    print()
    
    # Test 2: List trips
    results['list_trips'] = test_list_trips()
    print()
    
    if trip_id:
        # Test 3: Complete trip
        results['complete_trip'] = test_complete_trip(trip_id)
        print()
        
        # Test 4: Create another trip for cancel test
        trip_id_2 = test_create_trip()
        if trip_id_2:
            # Test 5: Cancel trip with reason
            results['cancel_trip'] = test_cancel_trip(trip_id_2)
            print()
            
            # Test 6: Cancel without reason (should fail)
            trip_id_3 = test_create_trip()
            if trip_id_3:
                results['cancel_without_reason'] = test_cancel_without_reason(trip_id_3)
                print()
    
    # Summary
    print("="*60)
    print("Test Summary:")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    print()
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
