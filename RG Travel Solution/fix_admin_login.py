#!/usr/bin/env python3
"""
Fix Admin Login - Verify and Update Admin Record
"""
import sqlite3
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rg_travel_backend'))

from utils.security import hash_password

DB_PATH = "rg_travel_backend/rg_travel.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check current admin
    print("=" * 60)
    print("CHECKING ADMIN RECORDS")
    print("=" * 60)
    
    cur.execute("SELECT id, name, mobile, password_salt, password_hash FROM admins")
    admins = cur.fetchall()
    
    if not admins:
        print("❌ NO ADMINS FOUND IN DATABASE!")
        conn.close()
        return
    
    print(f"\nFound {len(admins)} admin(s):\n")
    for admin in admins:
        print(f"ID: {admin['id']}")
        print(f"Name: {admin['name']}")
        print(f"Mobile: {admin['mobile']}")
        print(f"Has Password Hash: {bool(admin['password_hash'])}")
        print(f"Has Password Salt: {bool(admin['password_salt'])}")
        print("-" * 40)
    
    # Fix Rushi Gund's password
    target_mobile = "9325118627"
    target_name = "Rushi Gund"
    new_password = "admin123"
    
    print(f"\n🔧 UPDATING PASSWORD for {target_name} (Mobile: {target_mobile})")
    print(f"New Password: {new_password}")
    
    # Generate new hash
    password_salt, password_hash = hash_password(new_password)
    
    # Update database
    cur.execute("""
        UPDATE admins 
        SET password_salt = ?, password_hash = ?
        WHERE mobile = ? AND LOWER(name) = LOWER(?)
    """, (password_salt, password_hash, target_mobile, target_name))
    
    if cur.rowcount == 0:
        print(f"\n❌ No admin found with mobile={target_mobile} and name={target_name}")
        print("Creating new admin record...")
        
        cur.execute("""
            INSERT INTO admins (id, name, mobile, email, password_salt, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            f"admin_{target_mobile}",
            target_name,
            target_mobile,
            "rushi@rgtravel.com",
            password_salt,
            password_hash
        ))
        print(f"✅ Created new admin: {target_name}")
    else:
        print(f"✅ Updated password for {target_name}")
    
    conn.commit()
    
    # Verify
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    cur.execute("""
        SELECT id, name, mobile, password_salt, password_hash 
        FROM admins 
        WHERE mobile = ?
    """, (target_mobile,))
    
    admin = cur.fetchone()
    if admin:
        print(f"\n✅ Admin Record Confirmed:")
        print(f"   ID: {admin['id']}")
        print(f"   Name: {admin['name']}")
        print(f"   Mobile: {admin['mobile']}")
        print(f"   Password Hash Length: {len(admin['password_hash']) if admin['password_hash'] else 0}")
        print(f"   Password Salt Length: {len(admin['password_salt']) if admin['password_salt'] else 0}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("NEXT STEP: Test login with:")
    print(f"  Name: {target_name}")
    print(f"  Mobile: {target_mobile}")
    print(f"  Password: {new_password}")
    print("=" * 60)

if __name__ == "__main__":
    main()
