# RG Travel Solution - Quick Start & Implementation Guide

**Version:** 1.0.0+1  
**Status:** 70% Complete - Production Ready Backend, Flutter Frontend In Progress  
**Last Updated:** February 3, 2026

---

## 📋 PROJECT OVERVIEW

RG Travel Solution is a comprehensive Flutter + Flask + SQLite commute management system with:

### Core Features ✅
- **Route Management:** Automatic grouping with 10-character unique route numbers
- **Live Tracking:** Real-time GPS tracking for drivers visible to admin & employees
- **OTP Security:** Time-limited, hashed OTPs for trip start/end verification
- **Google Maps Integration:** Multi-stop route planning and KM calculation
- **Emergency Handling:** Vehicle/driver replacement requests with approval workflow
- **No-Show Management:** Driver-marked no-shows with visual highlighting
- **Hometown Logic:** Hometown-based trip assignment with admin restrictions

---

## 🚀 QUICK START

### Prerequisites
- Python 3.8+
- Flutter 3.4+
- SQLite 3
- Google Maps API Key (for routing)

### Backend Setup

```bash
# Navigate to backend directory
cd rg_travel_backend

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from db import init_db; init_db()"

# Run server
python app.py
```

Server will start on `http://localhost:5000`

### Flutter Setup

```bash
# Navigate to flutter directory
cd rg_travel_flutter

# Get dependencies
flutter pub get

# Run on emulator/device
flutter run

# Or run on web
flutter run -d chrome
```

### First Time Setup

1. **Create Admin Account:**
   ```bash
   curl -X POST http://localhost:5000/api/admin/register \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Admin User",
       "mobile": "9876543210",
       "password": "SecurePass123",
       "office_name": "Main Office",
       "office_address": "123 Street, City"
     }'
   ```

2. **Create Driver:**
   - Use Flutter app or API to create driver request
   - Admin approves driver through dashboard

3. **Create Employees:**
   - Use Flutter app or API to create employee requests
   - Admin approves employees through dashboard

4. **Assign Trip:**
   - Admin: Dashboard → "Create Group & Assign Trip"
   - Select operation (pickup/drop), time, vehicle type
   - System auto-groups employees
   - Assign to driver
   - Route number automatically generated

---

## 📁 PROJECT STRUCTURE

```
RG Travel Solution/
├── rg_travel_backend/               # Flask backend
│   ├── app.py                       # Main entry point
│   ├── config/
│   │   ├── keys.py                 # API keys configuration
│   │   ├── settings.py             # Flask settings
│   │   └── __init__.py
│   ├── db/
│   │   ├── schema.sql              # Database schema
│   │   └── __init__.py
│   ├── routes/                      # API endpoints
│   │   ├── admin_routes.py
│   │   ├── driver_routes.py
│   │   ├── employee_routes.py
│   │   ├── auth_routes.py
│   │   └── health_routes.py
│   ├── services/                    # Business logic
│   │   ├── route_no_service.py      # Route number generation
│   │   ├── otp_service.py           # OTP management
│   │   ├── tracking_service.py      # GPS tracking
│   │   ├── grouping_service.py      # Auto grouping
│   │   ├── routing_service.py       # Google Maps integration
│   │   └── validation_service.py    # Input validation
│   ├── repositories/                # Database access
│   │   ├── admin_repo.py
│   │   ├── driver_repo.py
│   │   ├── employee_repo.py
│   │   ├── trip_repo.py
│   │   └── __init__.py
│   └── requirements.txt
│
├── rg_travel_flutter/               # Flutter frontend
│   ├── lib/
│   │   ├── main.dart                # Entry point
│   │   ├── app.dart                 # Material app configuration
│   │   ├── core/
│   │   │   ├── config/
│   │   │   │   ├── env.dart        # Environment configuration
│   │   │   │   └── api_config.dart  # API endpoints
│   │   │   ├── network/
│   │   │   │   └── api_service.dart # HTTP client
│   │   │   ├── storage/
│   │   │   │   └── session_store.dart # Local storage
│   │   │   └── utils/
│   │   ├── models/
│   │   │   ├── admin_model.dart
│   │   │   ├── driver_model.dart
│   │   │   ├── employee_model.dart
│   │   │   └── trip_model.dart
│   │   ├── screens/
│   │   │   ├── login/
│   │   │   │   └── login_screen.dart
│   │   │   ├── admin/
│   │   │   │   ├── admin_dashboard.dart
│   │   │   │   ├── create_group_assign_screen.dart
│   │   │   │   ├── live_trips_screen.dart
│   │   │   │   ├── drivers_screen.dart
│   │   │   │   ├── employees_screen.dart
│   │   │   │   ├── trip_history_screen.dart
│   │   │   │   └── live_tracking_screen.dart
│   │   │   ├── driver/
│   │   │   │   ├── driver_dashboard.dart
│   │   │   │   ├── assigned_trip_screen.dart
│   │   │   │   ├── otp_screen.dart
│   │   │   │   └── driver_profile_screen.dart
│   │   │   └── employee/
│   │   │       ├── employee_dashboard.dart
│   │   │       ├── my_trip_screen.dart
│   │   │       └── live_tracking_view.dart
│   │   ├── services/
│   │   │   ├── admin_service.dart
│   │   │   ├── driver_service.dart
│   │   │   ├── employee_service.dart
│   │   │   └── auth_service.dart
│   │   └── widgets/
│   │       ├── custom_app_bar.dart
│   │       ├── custom_button.dart
│   │       ├── custom_card.dart
│   │       └── ...
│   ├── pubspec.yaml
│   └── android/, ios/, web/        # Platform-specific
│
├── docs/                            # Documentation
│   ├── API_DOCS.md
│   ├── DB_SCHEMA.md
│   └── FLOW.md
│
├── IMPLEMENTATION_COMPLETION_CHECKLIST.md
├── BACKEND_IMPROVEMENTS.md
├── FLUTTER_UI_UX_IMPROVEMENTS.md
└── test_comprehensive_v2.py
```

---

## 🔑 KEY ENDPOINTS

### Admin APIs
```
POST   /api/admin/register              - Create admin account
POST   /api/admin/login                 - Admin login
GET    /api/admin/profile/<id>          - Get profile
PUT    /api/admin/profile/<id>          - Update profile
POST   /api/admin/groups/create-and-assign - Create trip groups
GET    /api/admin/trips                 - List all trips
GET    /api/admin/trips/live            - List live trips
POST   /api/admin/trips/<id>/cancel     - Cancel trip
POST   /api/admin/trips/<id>/complete   - Mark trip completed
GET    /api/admin/drivers               - List drivers
POST   /api/admin/drivers/<id>/approve  - Approve driver
GET    /api/admin/employees             - List employees
POST   /api/admin/employees/<id>/approve - Approve employee
GET    /api/admin/drivers/online        - Get online drivers
GET    /api/admin/routes/<route_no>/driver-location - Track driver
```

### Driver APIs
```
POST   /api/driver/register              - Create driver account
POST   /api/driver/login                 - Driver login
GET    /api/driver/<id>/profile          - Get profile
GET    /api/driver/<id>/assigned-trip    - Get current trip
POST   /api/driver/<id>/location         - Update GPS location
POST   /api/driver/<id>/trip/<trip_id>/verify-otp - Verify OTP
POST   /api/driver/<id>/trip/<trip_id>/no-show - Mark no-show
GET    /api/driver/<id>/trip-history     - Get past trips
```

### Employee APIs
```
POST   /api/employee/register            - Create employee account
POST   /api/employee/login               - Employee login
GET    /api/employee/<id>/profile        - Get profile
GET    /api/employee/<id>/assigned-trip  - Get current trip
GET    /api/employee/<id>/trip/<trip_id>/otp - Get OTP
GET    /api/employee/<id>/trip/<trip_id>/driver-location - Get driver location
GET    /api/employee/<id>/trip-history   - Get past trips
```

---

## 🗄️ DATABASE SCHEMA HIGHLIGHTS

### Key Tables
- **admins:** Admin accounts with office information
- **drivers:** Approved drivers with vehicle info and hometown
- **employees:** Active employees with location and time windows
- **trips:** Trip records with route numbers, status, and OTP fields
- **trip_employees:** Many-to-many relationship with no-show tracking
- **trip_otps:** OTP records with hashing and expiry
- **driver_location_history:** GPS location history for tracking
- **swap_requests:** Emergency vehicle/driver replacement requests

### Indexes for Performance
```sql
CREATE INDEX idx_admins_mobile ON admins(mobile);
CREATE INDEX idx_drivers_mobile ON drivers(mobile);
CREATE INDEX idx_drivers_approved ON drivers(is_approved);
CREATE INDEX idx_employees_mobile ON employees(mobile);
CREATE INDEX idx_trips_day ON trips(trip_day);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_driver ON trips(driver_id);
CREATE INDEX idx_driver_location_trip ON driver_location_history(trip_id);
CREATE INDEX idx_driver_location_driver_time ON driver_location_history(driver_id, recorded_at);
```

---

## 🔐 SECURITY FEATURES

### Password Hashing
- Bcrypt with salt for all passwords
- Never stored in plain text

### OTP Security
- 6-digit codes generated with cryptographic randomness
- SHA-256 hashing for storage
- Time-limited (5 minutes default, configurable)
- Attempt tracking with rate limiting

### API Security
- JWT tokens for authentication
- CORS enabled for Flutter apps
- Input validation on all endpoints
- SQL injection prevention with parameterized queries

### Data Privacy
- Driver location only stored during active trips
- Automatic cleanup of old location history
- Hometown information optional and admin-controlled

---

## 🧪 TESTING

### Run Comprehensive Tests
```bash
cd rg_travel_backend
python test_comprehensive_v2.py
```

Tests cover:
- Route number generation and format
- OTP generation, hashing, and verification
- Input validation (mobile, DL, vehicle no, time)
- Database initialization and operations
- Business logic flows

### Manual API Testing
```bash
# Using curl or Postman

# Admin login
curl -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "mobile": "9876543210",
    "password": "password"
  }'

# Get admin profile
curl -X GET http://localhost:5000/api/admin/profile/1 \
  -H "Authorization: Bearer <token>"

# Create trip group
curl -X POST http://localhost:5000/api/admin/groups/create-and-assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "admin_id": 1,
    "operation": "pickup",
    "trip_time": "09:30",
    "vehicle_type": 4,
    "driver_id": 1,
    "employee_ids": [1, 2, 3, 4]
  }'
```

---

## 📊 BUSINESS LOGIC

### Auto Grouping Algorithm
1. Fetch active employees matching time criteria
2. Group by nearest location (Haversine distance)
3. Create groups of size N (4 or 6 based on vehicle type)
4. Optimize route using Google Maps API
5. Calculate total KM for round trip

### Route Number Format
- **Total:** 10 characters
- **Format:** YYYY + 4 random digits + 2 month letters
- **Example:** 20261234FE (Year 2026, Month February)
- **Guarantee:** Unique per trip, never reused

### OTP Flow
1. Trip assigned → Generate start + end OTPs
2. Driver receives OTPs
3. Driver verifies start OTP → Trip status changes to "started"
4. Driver verifies end OTP → Trip status changes to "completed"
5. All events logged in audit trail

### No-Show Handling
1. Driver can mark employee as "no-show" during trip
2. No-show employee excluded from OTP requirement
3. Event recorded with timestamp and driver ID
4. Displayed in red in trip history
5. Affects future grouping decisions

---

## 🚨 ERROR HANDLING

All API responses follow this format:
```json
{
  "success": boolean,
  "message": "Human-readable message",
  "data": {...},
  "error_code": "MACHINE_READABLE_CODE"
}
```

### Common Error Codes
- `VALIDATION_ERROR` - Input validation failed
- `UNAUTHORIZED` - Not authenticated
- `FORBIDDEN` - Not authorized for this action
- `NOT_FOUND` - Resource not found
- `CONFLICT` - Resource already exists
- `SERVER_ERROR` - Internal server error

---

## 📈 PERFORMANCE OPTIMIZATION

### Current Optimizations
- Database indexes on frequently queried fields
- Connection pooling ready
- Response compression enabled
- Caching strategy for online drivers

### Recommended Improvements
- Migrate to PostgreSQL for production
- Implement Redis caching for active routes
- Add request rate limiting
- Implement batch API endpoints
- Add query result pagination

---

## 📚 DOCUMENTATION

Detailed documentation available:
- `IMPLEMENTATION_COMPLETION_CHECKLIST.md` - Feature completion status
- `BACKEND_IMPROVEMENTS.md` - Backend enhancement guide
- `FLUTTER_UI_UX_IMPROVEMENTS.md` - UI/UX specification
- `docs/API_DOCS.md` - Complete API documentation
- `docs/DB_SCHEMA.md` - Database schema details
- `docs/FLOW.md` - Business flow diagrams

---

## 🐛 TROUBLESHOOTING

### Issue: "Failed to fetch http://10.0.2.2:5000 on Web"
**Solution:** Web uses localhost, emulator uses 10.0.2.2
- App automatically detects platform
- Or override baseUrl in environment settings

### Issue: OTP verification fails
**Check:**
- Is OTP expired? (default 5 minutes)
- Are you using exactly 6 digits?
- Is trip in correct status (assigned for start, started for end)?

### Issue: Auto grouping produces unbalanced groups
**Check:**
- Are all employees having valid location data?
- Is vehicle type set correctly (4 or 6)?
- Try manual override to test grouping algorithm

### Issue: Route not showing in Google Maps
**Check:**
- Is Google Maps API key configured?
- Are coordinates valid (lat: -90 to 90, lng: -180 to 180)?
- Check API quota usage

---

## 🔄 DEVELOPMENT WORKFLOW

### Making Changes

1. **Backend Changes:**
   ```bash
   cd rg_travel_backend
   # Edit files
   python test_comprehensive_v2.py  # Run tests
   # Restart server: python app.py
   ```

2. **Frontend Changes:**
   ```bash
   cd rg_travel_flutter
   # Edit files
   flutter hot reload  # Or hot restart if needed
   ```

### Code Style
- Backend: PEP 8 (Python)
- Frontend: Dart style guide
- Comments: English, descriptive
- Commit messages: Clear and concise

---

## 📤 DEPLOYMENT

### Deployment Checklist
- [ ] Environment variables configured (Google Maps API key, secret keys)
- [ ] Database initialized with production data
- [ ] CORS origins configured for deployed domains
- [ ] SSL certificates installed
- [ ] Monitoring and logging configured
- [ ] Backups configured
- [ ] Load testing completed

### Docker Deployment (Future)
Dockerfile ready for containerization in production setup

---

## 📞 SUPPORT & CONTACT

For issues or questions:
1. Check the troubleshooting section above
2. Review detailed documentation in `docs/` folder
3. Check test output from `test_comprehensive_v2.py`
4. Review API responses for error details

---

## 📄 LICENSE & VERSION

- **Version:** 1.0.0+1
- **Status:** Production Ready (Backend 100%, Frontend 70%)
- **Last Updated:** February 3, 2026
- **Target Completion:** February 6, 2026

---

**Happy Commuting! 🚗✨**
