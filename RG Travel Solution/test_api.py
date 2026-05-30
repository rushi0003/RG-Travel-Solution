#!/usr/bin/env python3
import requests

# Test the drivers endpoint
resp = requests.get('http://127.0.0.1:5000/api/admin/drivers')
print(f'Status: {resp.status_code}')
print(f'Response: {resp.json()}')
