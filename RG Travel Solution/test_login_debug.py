#!/usr/bin/env python3
import requests
import json

# Try login with debugging
BASE_URL = "http://localhost:5000"

passwords_to_try = ["Rushi123", "Rushi123"]

for pwd in passwords_to_try:
    print(f"\nTesting login with password: {pwd}")
    try:
        response = requests.post(f"{BASE_URL}/api/auth/admin/login", json={
            "name": "Rushi Gund", 
            "mobile": "9325118627",
            "password": pwd
        })
        
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            print(f"Message: {data.get('message', '')}")
            if data.get('success'):
                print(f"*** VALID PASSWORD FOUND: {pwd} ***")
                break
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Response text: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")
