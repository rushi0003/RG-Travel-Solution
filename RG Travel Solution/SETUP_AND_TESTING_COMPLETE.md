# RG Travel Solution - Complete Setup & Testing Guide

## 📋 Project Overview

**RG Travel Solution** is a role-based commute management system with:
- **Flutter Frontend** (Admin/Driver/Employee dashboards)
- **Flask Backend** (REST API with SQLite)
- **Live Tracking** (GPS location updates)
- **OTP Verification** (Trip start/end authentication)
- **Trip Assignment** (Admin groups and assigns trips)

---

## 🚀 Quick Start (5 Minutes)

### Backend Setup
```bash
cd rg_travel_backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=rg-travel-solution-dev-key
DATABASE_PATH=rg_travel.db
OTP_EXPIRY_MINUTES=5
GOOGLE_MAPS_API_KEY=YOUR_KEY_HERE
EOF

# Run backend
python app.py
# Server runs on http://127.0.0.1:5000
```

### Frontend Setup
```bash
cd rg_travel_flutter

# Get dependencies
flutter pub get

# Run on Android Emulator
flutter run

# Run on Web
flutter run -d chrome

# Run on iOS Simulator
flutter run -d ios
```

---

## 🔧 Configuration

### Backend `.env` File
```ini
# Flask settings
FLASK_ENV=development
FLASK_DEBUG=True

# Database
DATABASE_PATH=rg_travel.db

# Security
SECRET_KEY=your-secret-key-change-in-prod

# OTP
OTP_EXPIRY_MINUTES=5
OTP_LENGTH=6

# Google Maps (optional)
GOOGLE_MAPS_API_KEY=your-api-key-here

# CORS
CORS_ORIGINS=*

# JWT
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=168
```

### Flutter Configuration
Edit `lib/core/config/api_config.dart`:
```dart
class ApiConfig {
  static const bool isDev = true;  // Change to false for production
  
  static String get baseUrl {
    // Auto-detects platform and returns correct URL
    // Android Emulator: http://10.0.2.2:5000
    // Web/iOS: http://127.0.0.1:5000
  }
}
```

---

## 🗄️ Database Setup

### Initialize Database
```bash
cd rg_travel_backend
python -c "from db import init_db; init_db()"
```

### Create Test Data
```bash
# Run all seeds
python -c "
from seeds.seed_admin import seed_admin
from seeds.seed_drivers import seed_drivers
from seeds.seed_employees import seed_employees

seed_admin()
seed_drivers()
seed_employees()
print('✅ Test data created!')
"
```

### Test Credentials

**Admin:**
- Mobile: 9876543210
- Password: AdminPass123

**Driver:**
- Mobile: 9876543211
- Password: DriverPass123

**Employee:**
- Mobile: 9876543212
- Password: EmpPass123

---

## 📱 API Testing

### 1. Health Check
```bash
curl http://127.0.0.1:5000/api/health
```

Response:
```json
{
  "success": true,
  "message": "Server is running",
  "data": {
    "status": "healthy",
    "timestamp": "2026-02-02T10:30:00Z"
  }
}
```

### 2. Admin Login
```bash
curl -X POST http://127.0.0.1:5000/api/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "mobile": "9876543210",
    "password": "AdminPass123"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "id": "ADMIN001",
    "name": "John Admin",
    "role": "admin",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2026-02-09T10:00:00Z"
  }
}
```

### 3. Get Admin Profile
```bash
curl http://127.0.0.1:5000/api/admin/ADMIN001 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 4. List Drivers
```bash
curl http://127.0.0.1:5000/api/admin/drivers \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 5. Create Groups
```bash
curl -X POST http://127.0.0.1:5000/api/admin/groups/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "mode": "pickup",
    "vehicle_type": 4,
    "scheduled_time": "2026-02-02T08:00:00Z",
    "admin_override": false,
    "employee_ids": [],
    "preferred_driver_ids": []
  }'
```

### 6. Assign Trip
```bash
curl -X POST http://127.0.0.1:5000/api/admin/trips/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "group_id": "GRP001",
    "driver_id": "DRV001",
    "cab_no": "MH12AB1234",
    "mode": "pickup",
    "scheduled_time": "2026-02-02T08:00:00Z"
  }'
```

### 7. Driver: Get Assigned Trip
```bash
curl http://127.0.0.1:5000/api/driver/DRV001/assigned-trip \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 8. Driver: Send Location
```bash
curl -X POST http://127.0.0.1:5000/api/driver/DRV001/trips/RG20260202001/location \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "lat": 12.9716,
    "lng": 77.5946,
    "speed": 45.5,
    "heading": 180
  }'
```

### 9. Get OTP
```bash
curl "http://127.0.0.1:5000/api/employee/EMP001/otp?route_no=RG20260202001&type=start" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 10. Verify OTP
```bash
curl -X POST http://127.0.0.1:5000/api/driver/DRV001/trips/RG20260202001/verify-otp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "type": "start",
    "otp": "123456"
  }'
```

---

## 🧪 Postman Testing

1. Download [Postman](https://www.postman.com/downloads/)
2. Import collection from `API_ENDPOINTS_COMPLETE.json`
3. Set environment variable:
   - `base_url` = `http://127.0.0.1:5000`
   - `token` = Retrieved from login response

### Postman Collection Template
```json
{
  "info": {
    "name": "RG Travel Solution API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Admin Login",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/auth/admin/login",
            "body": {
              "mode": "raw",
              "raw": "{\"mobile\": \"9876543210\", \"password\": \"AdminPass123\"}"
            }
          }
        }
      ]
    }
  ]
}
```

---

## 🐛 Debugging

### View Backend Logs
```bash
# Run with verbose logging
python app.py --debug
```

### Check Database
```bash
# Connect to SQLite
sqlite3 rg_travel.db

# List tables
.tables

# Query admins
SELECT * FROM admins;

# Query trips
SELECT * FROM trips;

# Exit
.quit
```

### Check Flutter Logs
```bash
flutter logs
```

### Common Issues

**Issue:** "Connection refused"
- **Solution:** Make sure backend is running on correct port

**Issue:** Android Emulator can't reach 10.0.2.2
- **Solution:** Check `api_config.dart` - should auto-detect Android

**Issue:** OTP not working
- **Solution:** Check OTP expiry time in `.env` (default 5 minutes)

**Issue:** CORS errors
- **Solution:** Add frontend URL to `CORS_ORIGINS` in `.env`

---

## 📊 Monitoring

### Health Check Endpoint
```bash
curl http://127.0.0.1:5000/api/health
```

### Database Health
```bash
curl http://127.0.0.1:5000/api/db/health
```

### View Active Trips
```bash
curl http://127.0.0.1:5000/api/admin/trips/live \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🚢 Deployment

### Backend (Production)

**Option 1: Gunicorn (Linux/Mac)**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

**Option 2: Waitress (Windows)**
```bash
pip install waitress
waitress-serve --port=5000 wsgi:app
```

**Option 3: Docker**
```dockerfile
FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app"]
```

### Frontend (Production)

**Web:**
```bash
flutter build web --release
# Deploy to Firebase Hosting, Netlify, or any static host
```

**Android:**
```bash
flutter build apk --release
flutter build app-bundle --release
# Upload to Google Play Store
```

**iOS:**
```bash
flutter build ios --release
# Upload to App Store
```

---

## 📈 Performance Tips

1. **Enable HTTPS in production**
   - Use Let's Encrypt for free SSL/TLS

2. **Implement Redis caching**
   - Cache driver locations
   - Cache trip listings

3. **Database optimization**
   - Add indexes on frequently queried columns
   - Partition large tables

4. **API rate limiting**
   - Use Flask-Limiter to prevent abuse
   - 100 requests per minute per IP

5. **Compress responses**
   - Enable gzip compression
   - Reduce payload sizes

---

## 🔐 Security Checklist

- [ ] Generate strong `SECRET_KEY` in production
- [ ] Use HTTPS everywhere
- [ ] Validate all inputs on backend
- [ ] Hash passwords with bcrypt
- [ ] Implement rate limiting
- [ ] Use JWT tokens with short expiry
- [ ] Log all important actions
- [ ] Regular backups of database
- [ ] Restrict API access by IP (if possible)
- [ ] Regular security audits

---

## 📞 Support

For issues or questions:
1. Check `DEBUGGING_GUIDE.md`
2. Review API documentation in `API_ENDPOINTS_COMPLETE.json`
3. Check database schema in `db/schema.sql`

---

**Last Updated:** 2026-02-02
**Version:** 1.0.0
**Status:** Production Ready
