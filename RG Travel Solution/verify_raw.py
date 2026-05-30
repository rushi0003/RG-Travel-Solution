import requests
import json
import sys

BASE_URL = "http://localhost:5000"

try:
    print("SENDING REQUEST...")
    resp = requests.post(f"{BASE_URL}/api/auth/admin/login", json={
        "name": "Rushi Gund", 
        "mobile": "9325118627",
        "password": "admin123"
    })
    
    print(f"STATUS: {resp.status_code}")
    print("RAW BODY START")
    print(resp.text)
    print("RAW BODY END")
    
except Exception as e:
    print(f"ERROR: {e}")
