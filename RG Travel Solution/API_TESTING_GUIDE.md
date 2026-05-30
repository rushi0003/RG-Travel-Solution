# RG Travel Solution - Complete API Reference & Testing Guide

## 📚 Quick Navigation
- [Backend Setup](#backend-setup)
- [All API Endpoints](#all-api-endpoints)
- [Testing Guide](#testing-guide)
- [Common Issues & Fixes](#common-issues--fixes)

---

## 🚀 Backend Setup

### 1. Installation & Environment

```bash
# Navigate to backend directory
cd rg_travel_backend

# Create Python virtual environment (optional but recommended)
python -m venv venv

# Windows activation
venv\Scripts\activate

# macOS/Linux activation
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
cp ../.env.example .env
```

### 2. Start Backend Server

```bash
# Development server (with auto-reload)
python app.py

# Or with specific port
export FLASK_PORT=5000  # Linux/Mac
set FLASK_PORT=5000    # Windows
python app.py

# Production server (using Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### 3. Database Initialization

The database initializes automatically on first run. To manually reset:

```bash
# Reset database and seed demo data
curl -X POST http://localhost:5000/api/db/reset

# Or seed individually
curl -X POST http://localhost:5000/api/seed/admin
curl -X POST http://localhost:5000/api/seed/drivers
curl -X POST http://localhost:5000/api/seed/employees
```

---

## 📡 All API Endpoints

### Auth Routes (`/api/auth`)

#### Admin Login
```
POST /api/auth/admin/login
Content-Type: application/json

{
  "mobile": "9876543210",
  "password": "admin@123"
}

Response:
{
  "success": true,
  "message": "Login success",
  "data": {
    "token": "...",
    "expires_at": "2026-02-01T...",
    "profile": {...}
  }
}
```

#### Driver Login
```
POST /api/auth/driver/login
{
  "mobile": "9123456789",
  "password": "driver@123"
}
```

#### Employee Login
```
POST /api/auth/employee/login
{
  "mobile": "9111111111",
  "password": "emp@123"
}
```

#### Admin Signup/Create
```
POST /api/auth/admin/create
{
  "name": "Admin Name",
  "mobile": "9876543210",
  "email": "admin@rg.com",
  "password": "admin@123",
  "office_name": "RG Office",
  "office_location": "Bangalore",
  "office_address": "123 Main St"
}
```

#### Driver Signup
```
POST /api/auth/driver/signup
{
  "name": "Driver Name",
  "mobile": "9123456789",
  "dl_no": "DL0220230001234",
  "vehicle_no": "KA12AB1234",
  "vehicle_type": "4",
  "home_town": "Bangalore",
  "password": "driver@123"
}
```

#### Employee Signup
```
POST /api/auth/employee/signup
{
  "name": "Employee Name",
  "mobile": "9111111111",
  "email": "emp@company.com",
  "login_time": "09:00",
  "logout_time": "18:00",
  "pickup_location": "Home Location",
  "drop_location": "Office Location",
  "drop_lat": 12.9352,
  "drop_lng": 77.6245,
  "password": "emp@123"
}
```

#### Logout
```
POST /api/auth/logout
Authorization: Bearer {token}

Response:
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Admin Routes (`/api/admin`)

#### Get Admin Profile
```
GET /api/admin/profile
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": {
    "id": "admin_123",
    "name": "Admin Name",
    "mobile": "9876543210",
    "office_name": "RG Office"
  }
}
```

#### Update Admin Profile
```
PUT /api/admin/profile
Authorization: Bearer {admin_token}
{
  "office_name": "New Office Name",
  "office_address": "New Address"
}
```

#### List All Drivers
```
GET /api/admin/drivers
Authorization: Bearer {admin_token}
```

#### Approve Driver
```
POST /api/admin/drivers/{driver_id}/approve
Authorization: Bearer {admin_token}
```

#### Reject Driver
```
POST /api/admin/drivers/{driver_id}/reject
Authorization: Bearer {admin_token}
{
  "reason": "Documents not verified"
}
```

#### List All Employees
```
GET /api/admin/employees
Authorization: Bearer {admin_token}
```

#### Approve Employee
```
POST /api/admin/employees/{employee_id}/approve
Authorization: Bearer {admin_token}
```

#### Reject Employee
```
POST /api/admin/employees/{employee_id}/reject
Authorization: Bearer {admin_token}
{
  "reason": "Verification failed"
}
```

#### Create Trip & Auto-Group Employees
```
POST /api/admin/trips/create
Authorization: Bearer {admin_token}

{
  "trip_type": "pickup",     # or "drop"
  "schedule_time": "09:00",  # HH:MM format
  "vehicle_type": "4",       # or "6" seater
  "employee_ids": [1, 2, 3], # Optional: manual selection
  "auto_group": true         # Auto-group if no employee_ids
}

Response:
{
  "success": true,
  "data": {
    "trip_id": 123,
    "route_no": "RT2FG8H9JK",
    "status": "created",
    "groups": [...]
  }
}
```

#### Assign Driver to Trip
```
POST /api/admin/trips/{trip_id}/assign_driver
Authorization: Bearer {admin_token}

{
  "driver_id": "driver_456",
  "vehicle_type": "4"
}

Response:
{
  "success": true,
  "data": {
    "trip_id": 123,
    "driver_id": "driver_456",
    "status": "assigned"
  }
}
```

#### List Live Trips
```
GET /api/admin/trips/live
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "trip_id": 123,
      "route_no": "RT2FG8H9JK",
      "status": "started",
      "driver_name": "Driver Name",
      "employee_count": 5,
      "total_km": 12.5
    }
  ]
}
```

#### List Trip History
```
GET /api/admin/trips?status=completed&limit=10
Authorization: Bearer {admin_token}
```

#### Cancel Trip
```
POST /api/admin/trips/{trip_id}/cancel
Authorization: Bearer {admin_token}

{
  "reason": "Driver unavailable"
}
```

#### Generate OTPs for Trip
```
POST /api/admin/trips/{trip_id}/otps/generate
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": {
    "trip_id": 123,
    "start_otp": "123456",
    "end_otp": "654321",
    "expiry_minutes": 15
  }
}
```

#### Get Online Drivers
```
GET /api/admin/drivers/online
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": [
    {
      "driver_id": "driver_123",
      "name": "Driver Name",
      "lat": 12.9352,
      "lng": 77.6245,
      "last_update": "2026-02-01T10:30:00"
    }
  ]
}
```

#### Get Driver Location for Route
```
GET /api/admin/routes/{route_no}/driver-location
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "data": {
    "route_no": "RT2FG8H9JK",
    "driver_name": "Driver Name",
    "lat": 12.9352,
    "lng": 77.6245,
    "accuracy": 25.5
  }
}
```

### Driver Routes (`/api/driver`)

#### Get Driver Profile
```
GET /api/driver/profile
Authorization: Bearer {driver_token}
```

#### Update Driver Profile
```
PUT /api/driver/profile
Authorization: Bearer {driver_token}

{
  "home_town": "New Hometown",
  "dl_expiry": "2027-12-31",
  "rc_expiry": "2026-06-30"
}
```

#### Get Assigned Trips
```
GET /api/driver/trips
Authorization: Bearer {driver_token}

Response:
{
  "success": true,
  "data": [
    {
      "trip_id": 123,
      "route_no": "RT2FG8H9JK",
      "trip_type": "pickup",
      "status": "assigned",
      "employee_count": 5,
      "schedule_time": "09:00",
      "members": [...]
    }
  ]
}
```

#### Get Trip Details
```
GET /api/driver/trips/{trip_id}
Authorization: Bearer {driver_token}
```

#### Start Trip (OTP Verification)
```
POST /api/driver/trips/{trip_id}/start
Authorization: Bearer {driver_token}

{
  "otp": "123456"
}

Response:
{
  "success": true,
  "message": "Trip started",
  "data": {
    "trip_id": 123,
    "status": "started",
    "start_time": "2026-02-01T09:15:00"
  }
}
```

#### End Trip (OTP Verification)
```
POST /api/driver/trips/{trip_id}/end
Authorization: Bearer {driver_token}

{
  "otp": "654321"
}

Response:
{
  "success": true,
  "data": {
    "trip_id": 123,
    "status": "completed",
    "end_time": "2026-02-01T10:45:00",
    "total_km": 12.5
  }
}
```

#### Send Live Location
```
POST /api/driver/trips/{trip_id}/location
Authorization: Bearer {driver_token}

{
  "lat": 12.9352,
  "lng": 77.6245,
  "accuracy": 25.5
}

Response:
{
  "success": true,
  "message": "Location updated"
}
```

#### Mark Employee No-Show
```
POST /api/driver/trips/{trip_id}/no-show
Authorization: Bearer {driver_token}

{
  "employee_id": "emp_789",
  "reason": "Employee not at pickup point"
}

Response:
{
  "success": true,
  "data": {
    "employee_id": "emp_789",
    "is_no_show": true
  }
}
```

#### Get Trip History
```
GET /api/driver/trip-history
Authorization: Bearer {driver_token}
```

### Employee Routes (`/api/employee`)

#### Get Employee Profile
```
GET /api/employee/profile
Authorization: Bearer {employee_token}
```

#### Update Employee Profile
```
PUT /api/employee/profile
Authorization: Bearer {employee_token}

{
  "drop_location": "New Drop Location",
  "drop_lat": 12.9500,
  "drop_lng": 77.6500
}
```

#### Get My Assigned Trip
```
GET /api/employee/my-trip
Authorization: Bearer {employee_token}

Response:
{
  "success": true,
  "data": {
    "trip_id": 123,
    "route_no": "RT2FG8H9JK",
    "trip_type": "pickup",
    "driver_name": "Driver Name",
    "schedule_time": "09:00",
    "status": "started",
    "pickup_point": "Pickup Location"
  }
}
```

#### View Live Tracking
```
GET /api/employee/trips/{route_no}/driver-location
Authorization: Bearer {employee_token}

Response:
{
  "success": true,
  "data": {
    "driver_name": "Driver Name",
    "lat": 12.9352,
    "lng": 77.6245,
    "accuracy": 25.5,
    "last_update": "2026-02-01T10:30:00"
  }
}
```

#### Get Trip History
```
GET /api/employee/trip-history
Authorization: Bearer {employee_token}
```

### Health & Utility Routes

#### System Health Check
```
GET /api/health
GET /api/utils/ping

Response:
{
  "success": true,
  "message": "System healthy",
  "data": {
    "status": "operational",
    "timestamp": "2026-02-01T10:30:00"
  }
}
```

#### Database Health
```
GET /api/db/health

Response:
{
  "success": true,
  "data": {
    "database": "connected",
    "path": "/path/to/rg_travel.db",
    "size_mb": 2.5
  }
}
```

#### List Database Tables
```
GET /api/db/tables

Response:
{
  "success": true,
  "data": {
    "tables": [
      "admins",
      "drivers",
      "employees",
      "trips",
      "trip_employees",
      "sessions",
      "route_numbers"
    ]
  }
}
```

#### Get Current Time (IST)
```
GET /api/time/now

Response:
{
  "success": true,
  "data": {
    "utc": "2026-02-01T05:00:00Z",
    "ist": "2026-02-01T10:30:00",
    "unix": 1743650400
  }
}
```

---

## 🧪 Testing Guide

### Using cURL

#### 1. Admin Login
```bash
curl -X POST http://localhost:5000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "mobile": "9876543210",
    "password": "admin@123"
  }'
```

#### 2. Save Token (from login response)
```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..." # from login response
```

#### 3. Get Admin Profile
```bash
curl -X GET http://localhost:5000/api/admin/profile \
  -H "Authorization: Bearer $TOKEN"
```

#### 4. List All Drivers
```bash
curl -X GET http://localhost:5000/api/admin/drivers \
  -H "Authorization: Bearer $TOKEN"
```

### Using Postman

1. **Import Collection**: Use the included `RG_Travel_Postman_Collection.json`
2. **Set Variables**:
   - `base_url`: `http://localhost:5000`
   - `admin_token`: (from admin login)
   - `driver_token`: (from driver login)
   - `employee_token`: (from employee login)

3. **Test Flow**:
   - ✅ Health Check → `/api/health`
   - ✅ Admin Login → `/api/auth/admin/login`
   - ✅ Seed Data → `/api/seed/admin`, `/api/seed/drivers`, `/api/seed/employees`
   - ✅ Create Trip → `/api/admin/trips/create`
   - ✅ Assign Driver → `/api/admin/trips/123/assign_driver`
   - ✅ Driver Login → `/api/auth/driver/login`
   - ✅ Start Trip → `/api/driver/trips/123/start`
   - ✅ Send Location → `/api/driver/trips/123/location`
   - ✅ End Trip → `/api/driver/trips/123/end`

### Using Python Requests

```python
import requests
import json

BASE_URL = "http://localhost:5000"
ADMIN_MOBILE = "9876543210"
ADMIN_PASSWORD = "admin@123"

# 1. Admin Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/admin/login",
    json={"mobile": ADMIN_MOBILE, "password": ADMIN_PASSWORD}
)
admin_token = login_response.json()["data"]["token"]
print(f"Admin Token: {admin_token}")

# 2. Get Admin Profile
headers = {"Authorization": f"Bearer {admin_token}"}
profile = requests.get(f"{BASE_URL}/api/admin/profile", headers=headers)
print(json.dumps(profile.json(), indent=2))

# 3. List Drivers
drivers = requests.get(f"{BASE_URL}/api/admin/drivers", headers=headers)
print(f"Total Drivers: {len(drivers.json()['data'])}")

# 4. Create Trip
trip_payload = {
    "trip_type": "pickup",
    "schedule_time": "09:00",
    "vehicle_type": "4",
    "auto_group": True
}
trip_response = requests.post(
    f"{BASE_URL}/api/admin/trips/create",
    headers=headers,
    json=trip_payload
)
trip_data = trip_response.json()["data"]
trip_id = trip_data["trip_id"]
print(f"Created Trip ID: {trip_id}")
```

---

## 🐛 Common Issues & Fixes

### Issue 1: "Failed to fetch" on Android Emulator

**Problem**: Flutter can't connect to backend

**Solution**:
```dart
// In Flutter (lib/core/config/env.dart)
const String baseUrl = "http://10.0.2.2:5000"; // Android Emulator
// OR
const String baseUrl = "http://192.168.1.X:5000"; // Replace X with your machine IP
```

**Backend**: Ensure server runs on `0.0.0.0:5000` not just `127.0.0.1`

### Issue 2: CORS Errors

**Problem**: "Access to XMLHttpRequest blocked by CORS policy"

**Solution**: Already handled in app.py with `CORS(app)`. If persisting:

```python
# In app.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE"])
```

### Issue 3: Token Expired

**Problem**: 401 Unauthorized response

**Solution**:
1. Check token expiry: `GET /api/time/now`
2. Re-login to get new token
3. Update token in Flutter SharedPreferences

### Issue 4: Database Locked Error

**Problem**: "database is locked"

**Solution**:
```bash
# Close any open connections
pkill -f "python.*app.py"

# Delete database and restart (development only)
rm rg_travel.db
python app.py  # Will recreate and initialize
```

### Issue 5: ModuleNotFoundError

**Problem**: `ModuleNotFoundError: No module named 'flask'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall requirements
pip install -r requirements.txt
```

### Issue 6: Port Already in Use

**Problem**: `Address already in use`

**Solution**:
```bash
# Find process using port 5000
lsof -i :5000           # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill process
kill -9 <PID>           # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Use different port
export FLASK_PORT=5001
python app.py
```

---

## 📊 Response Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Login successful, data retrieved |
| 201 | Created | Trip created, user registered |
| 400 | Bad Request | Invalid phone format, missing fields |
| 401 | Unauthorized | Invalid credentials, expired token |
| 403 | Forbidden | Permission denied, wrong role |
| 404 | Not Found | Trip/driver not found |
| 409 | Conflict | Duplicate mobile, duplicate route number |
| 500 | Server Error | Database error, unhandled exception |

---

## 📝 Common Request Headers

All authenticated requests must include:
```
Authorization: Bearer {token}
Content-Type: application/json
```

## 🎯 Testing Checklist

- [ ] Backend starts without errors
- [ ] Database initializes successfully
- [ ] Admin can login
- [ ] Drivers can be seeded and listed
- [ ] Employees can be seeded and listed
- [ ] Trip creation works
- [ ] Driver assignment works
- [ ] OTP generation works
- [ ] Location updates work
- [ ] Trip completion works
- [ ] Live tracking works
- [ ] Flutter app connects successfully

---

**Last Updated**: 2026-02-01  
**API Version**: 1.0  
**Status**: ✅ Ready for Testing
