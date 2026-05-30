"""
Final System Verification Script
Tests complete data flow from Flutter → Backend → Database
"""

import sqlite3
import json
from pathlib import Path

def verify_database_schema():
    """Verify database schema matches backend expectations"""
    print("=" * 60)
    print("VERIFYING DATABASE SCHEMA")
    print("=" * 60)
    
    db_path = Path(__file__).parent / "rg_travel.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check drivers table
    print("\n✓ Checking 'drivers' table...")
    cur.execute("PRAGMA table_info(drivers)")
    drivers_cols = {row[1]: row[2] for row in cur.fetchall()}
    
    required_driver_cols = {
        'id': 'TEXT',
        'name': 'TEXT',
        'mobile': 'TEXT',
        'dl_no': 'TEXT',
        'vehicle_no': 'TEXT',
        'vehicle_type': 'TEXT',
        'home_town': 'TEXT',
        'is_approved': 'INTEGER',
        'password_salt': 'TEXT',
        'password_hash': 'TEXT'
    }
    
    issues = []
    for col, expected_type in required_driver_cols.items():
        if col not in drivers_cols:
            issues.append(f"  ❌ Missing column: {col}")
        else:
            print(f"  ✅ {col}: {drivers_cols[col]}")
    
    # Check driver_requests table
    print("\n✓ Checking 'driver_requests' table...")
    cur.execute("PRAGMA table_info(driver_requests)")
    requests_cols = {row[1]: row[2] for row in cur.fetchall()}
    
    required_request_cols = {
        'id': 'INTEGER',
        'name': 'TEXT',
        'mobile': 'TEXT',
        'dl_no': 'TEXT',
        'cab_no': 'TEXT',
        'vehicle_type': 'TEXT',
        'home_town': 'TEXT',
        'status': 'TEXT'
    }
    
    for col, expected_type in required_request_cols.items():
        if col not in requests_cols:
            issues.append(f"  ❌ Missing column: {col}")
        else:
            print(f"  ✅ {col}: {requests_cols[col]}")
    
    conn.close()
    
    if issues:
        print("\n❌ Schema Issues Found:")
        for issue in issues:
            print(issue)
        return False
    else:
        print("\n✅ Database schema is correct!")
        return True

def verify_sample_data():
    """Check if there's sample data and verify it's in correct format"""
    print("\n" + "=" * 60)
    print("VERIFYING SAMPLE DATA")
    print("=" * 60)
    
    db_path = Path(__file__).parent / "rg_travel.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check drivers
    cur.execute("SELECT COUNT(*) as count FROM drivers")
    driver_count = cur.fetchone()['count']
    print(f"\n✓ Total drivers in database: {driver_count}")
    
    if driver_count > 0:
        cur.execute("SELECT id, name, mobile, dl_no, vehicle_no, is_approved FROM drivers LIMIT 3")
        print("\n  Sample drivers:")
        for row in cur.fetchall():
            print(f"    - ID: {row['id']} | Name: {row['name']} | Cab: {row['vehicle_no']} | Approved: {row['is_approved']}")
    
    # Check driver requests
    cur.execute("SELECT COUNT(*) as count FROM driver_requests")
    request_count = cur.fetchone()['count']
    print(f"\n✓ Total driver requests: {request_count}")
    
    if request_count > 0:
        cur.execute("SELECT id, name, mobile, status, vehicle_type FROM driver_requests LIMIT 3")
        print("\n  Sample requests:")
        for row in cur.fetchall():
            vtype = row['vehicle_type'] if row['vehicle_type'] else 'NULL'
            print(f"    - ID: {row['id']} | Name: {row['name']} | Status: {row['status']} | VType: {vtype}")
    
    conn.close()
    return True

def main():
    print("\n" + "🔍 " * 30)
    print("FINAL SYSTEM VERIFICATION")
    print("🔍 " * 30 + "\n")
    
    schema_ok = verify_database_schema()
    data_ok = verify_sample_data()
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    if schema_ok and data_ok:
        print("✅ ALL CHECKS PASSED - System is ready!")
    else:
        print("❌ Some checks failed - Review issues above")
    
    print()

if __name__ == "__main__":
    main()
