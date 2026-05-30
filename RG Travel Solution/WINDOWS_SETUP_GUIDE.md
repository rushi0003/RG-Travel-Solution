# RG TRAVEL SOLUTION - Windows Setup & Run Guide

**Last Updated:** February 2, 2026  
**OS:** Windows 10/11  
**Tested On:** PowerShell 5.1+  

---

## 📋 Prerequisites

### Backend
- Python 3.9+
- pip package manager
- Git (for version control)

### Flutter
- Flutter SDK 3.4+
- Android Studio or VS Code with Flutter extension
- Android Emulator or Physical Device

### System
- Internet connection
- 500 MB free disk space
- Port 5000 available (backend)

---

## 🚀 Quick Start (5 Minutes)

### 1. Clone/Extract Project

```powershell
# Navigate to project
cd "C:\Users\[YourUsername]\Desktop\RG Travel Solution"

# Verify structure
dir
# Should show: rg_travel_backend/, rg_travel_flutter/, docs/, etc.
```

### 2. Start Backend

```powershell
# Option A: Using batch file (Recommended)
.\start-backend.bat

# Option B: Using PowerShell script
.\start-backend.ps1

# Option C: Manual
cd rg_travel_backend
python app.py
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in production.
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### 3. Test Backend Health

**In a new PowerShell window:**

```powershell
# Using curl (Windows 10.1909+)
curl http://127.0.0.1:5000/api/health

# Using Invoke-WebRequest (PowerShell)
Invoke-WebRequest http://127.0.0.1:5000/api/health

# Expected Response:
# {
#   "success": true,
#   "message": "Backend is online",
#   "data": { ... }
# }
```

### 4. Start Flutter App

**In a new PowerShell window:**

```powershell
# Option A: Using batch file
.\start-flutter.bat

# Option B: Manual
cd rg_travel_flutter
flutter run

# Choose device when prompted (Android Emulator / Physical Device)
```

---

## 🔧 Detailed Backend Setup

### Step 1: Create Virtual Environment

```powershell
# Navigate to backend directory
cd rg_travel_backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If permission denied, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 2: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected packages:**
- Flask==3.0.3
- flask-cors==4.0.1
- requests==2.32.3
- gunicorn==22.0.0 (Windows)
- waitress==3.0.0 (Windows)
- bcrypt==4.2.0
- python-dotenv==1.0.1

### Step 3: Environment Configuration

Create `.env` file in `rg_travel_backend/` directory:

```env
# =========================
# Backend Configuration
# =========================
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key-here-change-in-production

# =========================
# Database
# =========================
DATABASE_PATH=./rg_travel.db

# =========================
# OTP Configuration
# =========================
OTP_EXPIRY_MINUTES=5
OTP_LENGTH=6

# =========================
# Google Maps (Optional)
# =========================
GOOGLE_MAPS_API_KEY=your-api-key-here

# =========================
# Session Configuration
# =========================
SESSION_TIMEOUT_HOURS=8
```

### Step 4: Initialize Database

```powershell
# Option 1: Using Python script
python verify_setup.py

# Option 2: Manual initialization
python -c "from db import init_db; init_db()"

# Verify database was created
dir rg_travel.db
# Should show: rg_travel.db file created
```

### Step 5: (Optional) Seed Demo Data

```powershell
# Start backend with Python
python app.py

# In another PowerShell window
Invoke-WebRequest http://127.0.0.1:5000/api/admin/seed -Method POST
Invoke-WebRequest http://127.0.0.1:5000/api/drivers/seed -Method POST
Invoke-WebRequest http://127.0.0.1:5000/api/employees/seed -Method POST

# Response should show "success": true
```

---

## 📱 Detailed Flutter Setup

### Step 1: Install Flutter SDK

```powershell
# Check if Flutter installed
flutter --version

# If not installed, download from: https://flutter.dev/docs/get-started/install/windows
# Extract to a path WITHOUT SPACES: C:\Flutter

# Add to PATH:
# 1. Right-click "This PC" → Properties
# 2. Advanced system settings → Environment Variables
# 3. Add C:\Flutter\bin to PATH
# 4. Restart PowerShell
```

### Step 2: Get Flutter Dependencies

```powershell
cd rg_travel_flutter

# Download pub dependencies
flutter pub get

# Check for issues
flutter doctor
```

**Expected output:**
```
[✓] Flutter (Channel stable, X.XX.X, ...)
[✓] Android SDK (...)
[✓] Android SDK Command-line Tools (...)
[✓] Connected device
```

### Step 3: Configure Android Emulator (If Not Using Physical Device)

```powershell
# List available emulators
flutter emulators

# Launch emulator
flutter emulators launch <emulator_name>

# OR open Android Studio → AVD Manager → Launch Emulator
```

### Step 4: Update API Base URL

File: `rg_travel_flutter/lib/core/config/env.dart`

```dart
// Android Emulator
static const String devBaseUrl = "http://10.0.2.2:5000";

// Web (localhost)
static String get devBaseUrl {
  if (kIsWeb) {
    return "http://127.0.0.1:5000";
  }
  return "http://10.0.2.2:5000";
}

// Physical Device on LAN
// Change to your LAN IP: "http://192.168.x.x:5000"
```

### Step 5: Run Flutter App

```powershell
cd rg_travel_flutter

# List connected devices
flutter devices

# Run on specific device
flutter run -d <device_id>

# Run on Android Emulator
flutter run

# Run on Web
flutter run -d chrome

# Hot reload (when app running)
# Type 'r' in terminal

# Hot restart
# Type 'R' in terminal

# Stop app
# Type 'q' in terminal
```

---

## 🧪 Running Tests

### Backend Tests

```powershell
cd rg_travel_backend

# Install pytest
pip install pytest pytest-cov

# Run tests
pytest test_backend.py -v

# Run with coverage
pytest --cov=. test_backend.py
```

### Flutter Tests

```powershell
cd rg_travel_flutter

# Run unit tests
flutter test

# Run integration tests (requires emulator)
flutter test integration_test/

# Generate coverage
flutter test --coverage
```

---

## 🔍 Troubleshooting

### Port 5000 Already in Use

```powershell
# Find process using port 5000
Get-NetTCPConnection -LocalPort 5000

# Kill process
Stop-Process -Id <PID> -Force

# Or use different port in env:
# FLASK_PORT=5001
```

### Flutter Can't Connect to Backend

**Check 1: Backend Running?**
```powershell
curl http://127.0.0.1:5000/api/health
# Should return 200 OK with JSON
```

**Check 2: Correct Base URL?**
- Android Emulator: `http://10.0.2.2:5000`
- Physical Device: `http://<YOUR_LAN_IP>:5000`
- Web: `http://127.0.0.1:5000`

**Check 3: Firewall?**
```powershell
# Allow port through firewall
netsh advfirewall firewall add rule name="Flask App" dir=in action=allow protocol=tcp localport=5000
```

### Database Lock Error

```powershell
# Remove old database
Remove-Item rg_travel_backend\rg_travel.db

# Reinitialize
python verify_setup.py
```

### Python Module Not Found

```powershell
# Verify virtual environment activated
# Should show (venv) in prompt

# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Check specific module
python -c "import flask; print(flask.__version__)"
```

---

## 📊 API Testing

### Using Postman

1. Download [Postman](https://www.postman.com/downloads/)
2. Import collection: `API_ENDPOINTS.json`
3. Set environment variable: `base_url = http://127.0.0.1:5000`
4. Test endpoints

### Using cURL (PowerShell)

```powershell
# Health check
curl http://127.0.0.1:5000/api/health -Headers @{"Content-Type"="application/json"}

# Login
$body = @{
    mobile = "9876543210"
    password = "password"
} | ConvertTo-Json

curl -Method POST `
  -Uri http://127.0.0.1:5000/api/auth/admin/login `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

---

## 📦 Production Deployment (Checklist)

- [ ] Set `FLASK_ENV=production`
- [ ] Generate strong `SECRET_KEY`
- [ ] Disable debug mode (`FLASK_DEBUG=0`)
- [ ] Use gunicorn instead of Flask dev server
- [ ] Enable HTTPS/SSL
- [ ] Configure database backup
- [ ] Set up logging
- [ ] Configure rate limiting
- [ ] Test all API endpoints
- [ ] Set `flutter_web` to production URL

---

## 🔒 Security Checklist

- [ ] `.env` file not committed to Git
- [ ] Passwords hashed using bcrypt
- [ ] OTP hashed in database (never plaintext)
- [ ] CORS configured for specific origins
- [ ] HTTPS enforced in production
- [ ] Database encrypted at rest
- [ ] API tokens expire after 8 hours
- [ ] Rate limiting configured

---

## 📞 Quick Help

| Issue | Solution |
|-------|----------|
| Backend won't start | Check port 5000, check Python installed |
| Flutter build error | Run `flutter clean && flutter pub get` |
| Can't connect to backend | Verify base URL, check firewall |
| Database error | Delete `rg_travel.db`, reinit with verify_setup.py |
| Permission denied script | Run: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flutter Documentation](https://flutter.dev/docs)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [REST API Best Practices](https://restfulapi.net/)

---

**Project:** RG Travel Solution  
**Version:** 2.0  
**Last Updated:** February 2, 2026
