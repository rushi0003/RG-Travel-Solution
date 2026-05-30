# RG TRAVEL SOLUTION - DEVELOPER QUICK REFERENCE

**Version:** 2.0  
**Last Updated:** February 2, 2026  

---

## 🚀 Getting Started (5 min)

```powershell
# Terminal 1: Start Backend
cd "C:\Users\[YourUsername]\Desktop\RG Travel Solution\rg_travel_backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
# Should print: Running on http://127.0.0.1:5000

# Terminal 2: Start Flutter
cd "C:\Users\[YourUsername]\Desktop\RG Travel Solution\rg_travel_flutter"
flutter run
# Choose device (Android Emulator recommended)
```

**Verify:**
```powershell
# New Terminal 3
curl http://127.0.0.1:5000/api/health
# Should return: {"success": true, ...}
```

---

## 📂 Project Structure

```
rg_travel_backend/
├── app.py                 # Flask entry point
├── requirements.txt       # Dependencies
├── db/
│   ├── schema.sql        # 13 SQLite tables
│   └── __init__.py       # get_db(), init_db()
├── routes/               # API endpoints
│   ├── admin_routes.py
│   ├── driver_routes.py
│   ├── employee_routes.py
│   ├── auth_routes.py
│   └── health_routes.py
├── services/             # Business logic
│   ├── otp_service.py            # ✅ NEW/CONSOLIDATED
│   ├── grouping_service.py       # Auto-grouping
│   ├── routing_service.py        # Google Maps
│   ├── tracking_service.py       # GPS storage
│   ├── route_no_service.py       # 10-char route numbers
│   └── validation_service.py     # Input validation
├── utils/
│   ├── response.py       # Standard response format
│   ├── security.py       # Hashing & tokens
│   └── time_utils.py     # Datetime helpers
└── seeds/                # Demo data

rg_travel_flutter/
├── lib/
│   ├── main.dart         # Entry point
│   ├── app.dart          # App configuration
│   ├── core/
│   │   ├── config/       # API config & env
│   │   ├── network/      # API client
│   │   ├── storage/      # SharedPreferences
│   │   └── utils/        # Validators, constants
│   ├── models/           # Data classes
│   ├── services/         # API services
│   ├── screens/          # UI screens
│   └── widgets/          # Custom widgets
└── pubspec.yaml          # Dependencies
```

---

## 🔐 OTP Workflow (Key Feature)

### Generate OTP (Admin)
```python
# Backend: services/otp_service.py
from db import get_db
from services.otp_service import create_otp_for_trip

conn = get_db()
result = create_otp_for_trip(conn, trip_id=42, otp_expiry_minutes=5)
# Returns: {
#   "success": true,
#   "data": {
#     "trip_id": 42,
#     "start_otp": "123456",
#     "end_otp": "654321",
#     "expires_at": "2026-02-02T15:35:00Z"
#   }
# }

conn.close()
```

### Verify OTP (Driver)
```python
# Backend: In driver_routes.py
from services.otp_service import verify_otp_and_mark_used

result = verify_otp_and_mark_used(
    conn=conn,
    trip_id=42,
    otp_type="start",
    otp_input="123456",
    driver_id="driver_456"
)
# Returns: {
#   "success": true,
#   "message": "Trip started successfully",
#   "data": { "trip_id": 42, "status": "started" }
# }
```

### Check OTP Status
```python
# Backend: services/otp_service.py
from services.otp_service import get_otp_status

result = get_otp_status(conn, trip_id=42)
# Returns: {
#   "success": true,
#   "data": {
#     "trip_id": 42,
#     "start": {"exists": true, "is_used": false, "expired": false},
#     "end": {"exists": true, "is_used": false, "expired": false}
#   }
# }
```

---

## 🗄️ Database Quick Reference

### Connect to Database
```python
from db import get_db

conn = get_db()
cur = conn.cursor()

# Query
cur.execute("SELECT * FROM trips WHERE id = ? LIMIT 1", (42,))
trip = cur.fetchone()

# Insert
cur.execute(
    "INSERT INTO trips (route_no, trip_type, ...) VALUES (?, ?, ...)",
    ("0202123402", "pickup", ...)
)
conn.commit()

# Don't forget!
conn.close()
```

### Key Tables
```sql
-- Users
admins(id, name, mobile, email, ...)
drivers(id, name, mobile, vehicle_no, is_approved, ...)
employees(id, name, mobile, drop_location, ...)

-- Trips
trips(id, route_no, trip_day, trip_type, status, driver_id, ...)
trip_employees(trip_id, employee_id, sequence_no, is_no_show, ...)

-- Security
sessions(id, user_id, role, token, expires_at, ...)
trip_otps(trip_id, otp_type, otp_hash, is_used, expires_at, ...)
otp_audit_log(trip_id, otp_type, driver_id, action, reason, ...)

-- Tracking
driver_location_history(trip_id, driver_id, latitude, longitude, recorded_at, ...)

-- Extras
route_numbers(route_no, trip_day, created_at, ...)
swap_requests(trip_id, requested_by_driver_id, new_driver_id, status, ...)
```

---

## 🔌 API Endpoints (Most Used)

```
# Authentication
POST   /api/auth/admin/login
POST   /api/auth/driver/login
POST   /api/auth/employee/login

# Trips
POST   /api/admin/trips/create-group      # Create & group employees
POST   /api/admin/trips/assign            # Assign driver
POST   /api/admin/trips/{trip_id}/otp/generate
GET    /api/admin/trips/live              # Active trips
GET    /api/admin/trips/history           # Past trips

# Driver
GET    /api/driver/{driver_id}/assigned-trip
POST   /api/driver/{driver_id}/gps        # Submit GPS
POST   /api/driver/{driver_id}/trip/{trip_id}/otp/verify/start
POST   /api/driver/{driver_id}/trip/{trip_id}/otp/verify/end
POST   /api/driver/{driver_id}/trip/{trip_id}/no-show

# Employee
GET    /api/employee/{employee_id}/my-trip
GET    /api/employee/{employee_id}/tracking/{trip_id}

# Health
GET    /api/health                        # Backend status
```

---

## 📲 Flutter Key Classes

### API Client
```dart
// lib/core/network/api_client.dart
final api = ApiClient();

final response = await api.get("/api/admin/drivers");
final drivers = (response.data as List).map((d) => Driver.fromJson(d)).toList();

// Error handling
try {
  final response = await api.post("/api/auth/admin/login", 
    body: {"mobile": "...", "password": "..."}
  );
  if (response.success) {
    // Handle success
  }
} catch (e) {
  // Handle error
}
```

### Session Management
```dart
// lib/core/storage/session_store.dart
await SessionStore.saveToken(token);
await SessionStore.saveUserId(userId);
await SessionStore.saveRole("admin");

final isLoggedIn = await SessionStore.isLoggedIn();
final token = await SessionStore.getToken();
final role = await SessionStore.getRole();

await SessionStore.clear();  // Logout
```

### Services
```dart
// lib/services/admin_service.dart
final adminService = AdminService();

final drivers = await adminService.getDrivers();
final trips = await adminService.getLiveTrips();
await adminService.assignTrip(tripId: 42, driverId: "driver_456");

// lib/services/driver_service.dart
final driverService = DriverService();

final trip = await driverService.getAssignedTrip();
await driverService.submitGPS(lat: 18.52, lng: 73.85);
await driverService.verifyStartOTP(otp: "123456");
await driverService.verifyEndOTP(otp: "654321");
```

---

## 🧪 Testing

### Backend Tests
```bash
# Install pytest
pip install pytest pytest-cov

# Run all tests
pytest test_backend.py -v

# Run specific test class
pytest test_backend.py::TestOTPService -v

# Run with coverage
pytest --cov=rg_travel_backend test_backend.py
```

### Flutter Tests
```bash
# Run unit tests
flutter test

# Run integration tests
flutter test integration_test/

# Generate coverage
flutter test --coverage
```

---

## 🐛 Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| Backend won't start | Check port 5000 free, Python installed |
| "Module not found" error | Activate venv: `.\venv\Scripts\Activate.ps1` |
| Database locked error | Delete `rg_travel.db`, run `python verify_setup.py` |
| Flutter can't connect | Check base URL, firewall, backend running |
| OTP always invalid | Check hash mismatch, expiry, database |
| Permission denied on script | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## 📝 Making Changes

### Add New Endpoint
```python
# 1. Create route in routes/admin_routes.py
@admin_bp.route("/new-endpoint", methods=["POST"])
def new_endpoint():
    data = request.get_json()
    # Validate
    # Call service
    # Return response using success_response()
    return success_response(data=result, message="Success")

# 2. Register in routes/__init__.py
from .admin_routes import admin_bp
app.register_blueprint(admin_bp)

# 3. Call from Flutter
final response = await api.post("/api/admin/new-endpoint", body: {...});
```

### Add New Database Table
```sql
-- 1. Update db/schema.sql
CREATE TABLE new_table (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  column TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- 2. Create indexes as needed
CREATE INDEX idx_new_table_column ON new_table(column);

-- 3. Re-run initialization
python -c "from db import init_db; init_db()"
```

### Add New Service Function
```python
# 1. Create function in services/my_service.py
def my_function(conn, param1):
    cur = conn.cursor()
    cur.execute("SELECT * FROM my_table WHERE id = ?", (param1,))
    row = cur.fetchone()
    if not row:
        return {"success": False, "message": "Not found"}
    return {"success": True, "data": dict(row)}

# 2. Call from route
from services.my_service import my_function
result = my_function(conn, param)
return success_response(data=result["data"])
```

---

## 📚 Documentation Files

- **[ARCHITECTURE_ANALYSIS_AND_FIXES.md](../ARCHITECTURE_ANALYSIS_AND_FIXES.md)** - Issues & fixes
- **[WINDOWS_SETUP_GUIDE.md](../WINDOWS_SETUP_GUIDE.md)** - Setup instructions
- **[docs/API_DOCS.md](../docs/API_DOCS.md)** - Complete API reference
- **[docs/DB_SCHEMA.md](../docs/DB_SCHEMA.md)** - Database tables & relationships
- **[PROJECT_UPDATE_SUMMARY_v2.md](../PROJECT_UPDATE_SUMMARY_v2.md)** - v2.0 changes

---

## 🔗 Key Dependencies

### Backend
```
Flask==3.0.3              # Web framework
flask-cors==4.0.1         # Cross-origin requests
requests==2.32.3          # HTTP client (Google Maps)
python-dotenv==1.0.1      # Environment variables
```

### Flutter
```
http: ^1.2.2              # HTTP requests
shared_preferences: ^2.3  # Local storage
google_maps_flutter: ^2.9 # Maps display
geolocator: ^13.0.1       # GPS location
intl: ^0.19.0             # Localization
```

---

## 🚢 Deployment Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Change `SECRET_KEY` in `.env`
- [ ] Disable debug logging
- [ ] Enable HTTPS
- [ ] Set correct `baseUrl` in Flutter
- [ ] Test all endpoints
- [ ] Backup database
- [ ] Set up monitoring
- [ ] Configure rate limiting
- [ ] Test on physical device

---

## 📞 Get Help

1. **Backend Issues** - Check `app.py` error logs
2. **Database Issues** - Run `python verify_setup.py`
3. **API Issues** - Check endpoint in [docs/API_DOCS.md](../docs/API_DOCS.md)
4. **Flutter Issues** - Check `flutter doctor` output
5. **OTP Issues** - Run `pytest test_backend.py::TestOTPService -v`

---

**Happy Coding! 🚀**
