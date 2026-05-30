#!/usr/bin/env python3
import sqlite3
import hashlib
import secrets

def hash_password(password, salt=None):
    """Hash password using SHA256 - matches the backend implementation"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, pwd_hash

# Connect to database
db_path = 'rg_travel_backend/rg_travel.db'
conn = sqlite3.connect(db_path)
conn.execute('PRAGMA foreign_keys = ON')
cursor = conn.cursor()

print("=" * 80)
print("SEEDING DATABASE")
print("=" * 80)

# Check if admin_rg_001 already exists
cursor.execute("SELECT id FROM admins WHERE id = 'admin_rg_001'")
if cursor.fetchone():
    print("\n✓ admin_rg_001 already exists in database")
else:
    print("\n✗ admin_rg_001 not found, creating...")
    
    password = "admin123"
    salt, password_hash = hash_password(password)
    
    cursor.execute("""
        INSERT INTO admins (id, name, mobile, email, office_name, office_location, office_address, password_salt, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        'admin_rg_001',
        'Rushi Gund',
        '9325118627',
        'rushi@rgtravels.com',
        'RG Travels',
        'Pune',
        '123 Main Street, Pune',
        salt,
        password_hash
    ))
    
    conn.commit()
    print("✓ Created admin_rg_001 with password: admin123")

# Verify
cursor.execute("SELECT id, name, mobile FROM admins WHERE id = 'admin_rg_001'")
admin = cursor.fetchone()
if admin:
    print(f"✓ Admin verified: {admin[0]}, {admin[1]}, {admin[2]}")
else:
    print("✗ ERROR: Admin not found after insert!")

conn.close()
print("\nDatabase seeding complete!")
