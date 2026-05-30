# RG Travel Solution - Quick Start & Setup Guide

## 🚀 5-Minute Quick Start

### Prerequisites
- Python 3.8+ installed
- Node.js 14+ (for web deployment)
- Flutter SDK 3.4+ (for mobile)
- Git installed

### Step 1: Clone & Navigate
```bash
cd "RG Travel Solution"
ls  # Should show: rg_travel_backend/, rg_travel_flutter/, docs/, README.md
```

### Step 2: Start Backend
```bash
cd rg_travel_backend
pip install -r requirements.txt
python app.py

# Output should show:
# * Running on http://127.0.0.1:5000
# * Database initialized successfully
```

### Step 3: Test Backend (in another terminal)
```bash
# Health check
curl http://localhost:5000/api/health

# Should return:
# {"success": true, "message": "System healthy"}
```

### Step 4: Seed Demo Data
```bash
curl -X POST http://localhost:5000/api/seed/admin
curl -X POST http://localhost:5000/api/seed/drivers
curl -X POST http://localhost:5000/api/seed/employees
```

### Step 5: Login
```bash
curl -X POST http://localhost:5000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"mobile": "9876543210", "password": "admin@123"}'

# Save the token from response
```

### Step 6: Run Flutter App
```bash
cd ../rg_travel_flutter
flutter pub get
flutter run

# For Android emulator:
flutter run -d emulator-5554

# For web:
flutter run -d chrome
```

---

## 📋 Complete Installation Guide

### Windows Setup

```bash
# 1. Install Python dependencies
cd rg_travel_backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Create .env file
copy ..\\.env.example .env
# Edit .env with your settings

# 3. Start backend
python app.py

# 4. In new terminal, setup Flutter
cd ..\rg_travel_flutter
flutter pub get

# 5. Run Flutter
flutter run
```

### macOS/Linux Setup

```bash
# 1. Install Python dependencies
cd rg_travel_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create .env file
cp ../.env.example .env
# Edit .env with your settings

# 3. Start backend
python app.py

# 4. In new terminal, setup Flutter
cd ../rg_travel_flutter
flutter pub get

# 5. Run Flutter
flutter run -d chrome  # For web/emulator
```

### Docker Setup (Optional)

```bash
# Build Docker image
docker build -t rg-travel-backend -f Dockerfile .

# Run container
docker run -p 5000:5000 \
  -v $(pwd)/db:/app/db \
  -e FLASK_ENV=development \
  rg-travel-backend

# Backend runs at http://localhost:5000
```

---

## 🗂️ Project Files Explained

### Backend Structure
```
rg_travel_backend/
├── app.py                    # Main Flask application (1151 lines)
├── wsgi.py                   # Production entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
│
├── config/                   # Configuration
│   ├── settings.py           # App settings
│   └── keys.py               # API keys & secrets
│
├── db/                       # Database
│   ├── __init__.py           # Database connection
│   └── schema.sql            # SQLite schema definition
│
├── routes/                   # API endpoints
│   ├── auth_routes.py        # Login/signup
│   ├── admin_routes.py       # Admin APIs (400+ lines)
│   ├── driver_routes.py      # Driver APIs
│   ├── employee_routes.py    # Employee APIs
│   └── health_routes.py      # Health checks
│
├── services/                 # Business logic
│   ├── otp_service.py        # OTP generation/verification
│   ├── grouping_service.py   # Employee grouping algorithm
│   ├── routing_service.py    # Google Maps integration
│   ├── tracking_service.py   # Live location tracking
│   └── validation_service.py # Input validation
│
├── repositories/             # Database queries
│   ├── admin_repo.py         # Admin queries
│   ├── driver_repo.py        # Driver queries
│   ├── employee_repo.py      # Employee queries
│   └── trip_repo.py          # Trip queries
│
├── utils/                    # Utilities
│   ├── response.py           # Standard API response format
│   ├── security.py           # Authentication & hashing
│   └── time_utils.py         # Time/date helpers
│
└── seeds/                    # Demo data
    ├── seed_admin.py         # Admin seeding
    ├── seed_drivers.py       # Driver seeding
    └── seed_employees.py     # Employee seeding
```

### Frontend Structure
```
rg_travel_flutter/
├── lib/
│   ├── main.dart             # Entry point
│   ├── app.dart              # App routing
│   │
│   ├── core/
│   │   ├── config/
│   │   │   ├── env.dart      # API configuration
│   │   │   └── constants.dart# App constants
│   │   ├── network/
│   │   │   └── api_client.dart  # HTTP client
│   │   ├── storage/
│   │   │   └── session_store.dart # Local storage
│   │   └── utils/
│   │       ├── validators.dart   # Form validation
│   │       └── helpers.dart      # Helpers
│   │
│   ├── models/               # Data models
│   │   ├── admin_model.dart
│   │   ├── driver_model.dart
│   │   ├── employee_model.dart
│   │   ├── trip_model.dart
│   │   └── auth_models.dart
│   │
│   ├── services/             # API calls
│   │   ├── auth_service.dart
│   │   ├── admin_service.dart
│   │   ├── driver_service.dart
│   │   ├── employee_service.dart
│   │   └── location_service.dart
│   │
│   ├── state/                # State management
│   │   ├── auth_provider.dart
│   │   ├── admin_provider.dart
│   │   ├── driver_provider.dart
│   │   └── employee_provider.dart
│   │
│   ├── screens/              # UI screens
│   │   ├── login/
│   │   ├── admin/
│   │   ├── driver/
│   │   └── employee/
│   │
│   └── widgets/              # Reusable widgets
│       ├── common/
│       ├── layout/
│       └── trip/
│
├── pubspec.yaml              # Flutter dependencies
├── test/                     # Unit & widget tests
└── web/                      # Web configuration
```

---

## 🔑 Environment Variables

Create `.env` file in `rg_travel_backend/`:

```env
# Flask Configuration
FLASK_ENV=development              # or production
FLASK_PORT=5000
SECRET_KEY=your-secret-key-here   # Generate with secrets.token_hex(32)

# Database
RG_DB_PATH=rg_travel.db           # Database file path
RG_ENABLE_SEED_API=1              # Enable seed endpoints (set to 0 in production)

# Google Maps (Optional)
GOOGLE_MAPS_API_KEY=your-api-key-here

# OTP & Token Settings
RG_OTP_EXPIRY_MINUTES=15
RG_TOKEN_TTL_MINUTES=72

# CORS & Security
CORS_ORIGINS=*                    # or specific origins: http://localhost:3000,http://localhost:5000

# Development
DEBUG=1
LOG_LEVEL=DEBUG
```

---

## 🧪 Testing Workflows

### Admin Workflow

```bash
# 1. Get admin token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"mobile": "9876543210", "password": "admin@123"}' | jq -r '.data.token')

# 2. Get profile
curl http://localhost:5000/api/admin/profile \
  -H "Authorization: Bearer $TOKEN"

# 3. List drivers
curl http://localhost:5000/api/admin/drivers \
  -H "Authorization: Bearer $TOKEN"

# 4. Create trip
curl -X POST http://localhost:5000/api/admin/trips/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trip_type": "pickup",
    "schedule_time": "09:00",
    "vehicle_type": "4",
    "auto_group": true
  }'

# 5. Assign driver to trip (replace TRIP_ID and DRIVER_ID)
curl -X POST http://localhost:5000/api/admin/trips/123/assign_driver \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_id": "driver_1",
    "vehicle_type": "4"
  }'
```

### Driver Workflow

```bash
# 1. Login as driver
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/driver/login \
  -H "Content-Type: application/json" \
  -d '{"mobile": "9123456789", "password": "driver@123"}' | jq -r '.data.token')

# 2. Get assigned trips
curl http://localhost:5000/api/driver/trips \
  -H "Authorization: Bearer $TOKEN"

# 3. Start trip (with OTP from admin)
curl -X POST http://localhost:5000/api/driver/trips/123/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456"}'

# 4. Send location update
curl -X POST http://localhost:5000/api/driver/trips/123/location \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 12.9352,
    "lng": 77.6245,
    "accuracy": 25.5
  }'

# 5. End trip (with OTP)
curl -X POST http://localhost:5000/api/driver/trips/123/end \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp": "654321"}'
```

### Employee Workflow

```bash
# 1. Login as employee
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/employee/login \
  -H "Content-Type: application/json" \
  -d '{"mobile": "9111111111", "password": "emp@123"}' | jq -r '.data.token')

# 2. Get my trip
curl http://localhost:5000/api/employee/my-trip \
  -H "Authorization: Bearer $TOKEN"

# 3. View driver location
curl http://localhost:5000/api/employee/trips/RT2FG8H9JK/driver-location \
  -H "Authorization: Bearer $TOKEN"

# 4. Get trip history
curl http://localhost:5000/api/employee/trip-history \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🐛 Troubleshooting

### Problem: Backend won't start

**Solution:**
```bash
# Check Python version (need 3.8+)
python --version

# Verify dependencies installed
pip list | grep flask

# Try installing again
pip install --upgrade pip
pip install -r requirements.txt

# Check if port is in use
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows
```

### Problem: Flutter can't connect to backend

**Solution:**
```dart
// Edit lib/core/config/env.dart
const String baseUrl = "http://10.0.2.2:5000";  // Android Emulator
// OR
const String baseUrl = "http://192.168.1.X:5000";  // Your Machine IP
```

### Problem: Database errors

**Solution:**
```bash
# Check database health
curl http://localhost:5000/api/db/health

# Reset database
curl -X POST http://localhost:5000/api/db/reset

# Or delete and restart
rm rg_travel.db
python app.py
```

### Problem: CORS errors

**Solution:** Already handled in Flask app with `CORS(app)`. If persisting:
```python
# Check app.py has:
from flask_cors import CORS
CORS(app)
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md) | Complete API reference & testing |
| [FLUTTER_INTEGRATION_GUIDE.md](FLUTTER_INTEGRATION_GUIDE.md) | Flutter app setup & integration |
| [DATABASE_OPERATIONS_GUIDE.md](DATABASE_OPERATIONS_GUIDE.md) | Database queries & management |
| [PROJECT_COMPLETE_ANALYSIS.md](PROJECT_COMPLETE_ANALYSIS.md) | Project overview & architecture |
| README.md | Original project documentation |

---

## 🎯 Next Steps

1. ✅ **Backend Running** - Start with `python app.py`
2. ✅ **Data Seeded** - Call seed endpoints
3. ✅ **Manual Testing** - Use cURL commands or Postman
4. ✅ **Flutter App** - Run `flutter run`
5. ✅ **End-to-End Testing** - Test complete workflows
6. 📝 **Production Deployment** - See deployment docs

---

## 💡 Pro Tips

### Use Aliases for Common Commands
```bash
# Add to ~/.bash_profile (macOS) or ~/.bashrc (Linux)
alias rg-backend="cd ~/RG_Travel_Solution/rg_travel_backend && python app.py"
alias rg-flutter="cd ~/RG_Travel_Solution/rg_travel_flutter && flutter run"
alias rg-logs="cd ~/RG_Travel_Solution/rg_travel_backend && tail -f flask.log"
```

### Use Postman Collection
Import [postman_collection.json](postman_collection.json) for easy API testing with pre-configured endpoints and variables.

### Enable Logging
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py  # Shows detailed logs
```

### Monitor Database Changes
```bash
# Install sqlite3 CLI
brew install sqlite3  # macOS

# Open database
sqlite3 rg_travel.db

# Common queries
.tables
.schema trips
SELECT COUNT(*) FROM trips;
```

---

## 📞 Support & Help

If you encounter issues:

1. **Check Logs** - Backend logs show errors
2. **Review Guides** - Troubleshooting sections in documentation
3. **Test Endpoints** - Use curl to isolate issues
4. **Reset State** - Delete database and reseed

---

## 🎓 Learning Path

1. **Week 1**: Understand project structure & database
2. **Week 2**: Test backend APIs with cURL
3. **Week 3**: Integrate Flutter with backend
4. **Week 4**: Deploy to testing environment
5. **Week 5**: Production deployment & monitoring

---

**Last Updated**: 2026-02-01  
**Version**: 1.0  
**Status**: ✅ Production Ready
