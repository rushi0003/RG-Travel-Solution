
import sqlite3
import hashlib
import hmac
import secrets

DB_PATH = "rg_travel.db"

def verify_password(password: str, salt: str, pwd_hash: str) -> bool:
    calc = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(calc, pwd_hash)

def check_admin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, mobile, password_salt, password_hash FROM admins")
    rows = cur.fetchall()
    conn.close()

    print(f"Found {len(rows)} admins.")
    for row in rows:
        uid, name, mobile, salt, h = row
        print(f"Admin: ID={uid}, Name='{name}', Mobile='{mobile}'")
        
        # Check against 'Rushi123'
        is_valid = verify_password("Rushi123", salt, h)
        print(f"  Password 'Rushi123' valid? {is_valid}")

if __name__ == "__main__":
    check_admin()
