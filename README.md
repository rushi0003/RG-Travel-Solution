# RG Travel Solution - Complete Setup & Deployment Guide

> **Project**: RG Travel Solution - Employee Commute Management System  
> **Stack**: Flutter (Frontend) + Flask (Backend) + SQLite (Database)  
> **Version**: 1.0.0  
> **Date**: 2026-02-04

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Prerequisites](#prerequisites)
4. [Backend Setup](#backend-setup)
5. [Flutter Setup](#flutter-setup)
6. [Database Migration](#database-migration)
7. [Running the Application](#running-the-application)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**RG Travel Solution** automates employee commute management with features:

- **Auto-grouping** employees by proximity using Google Maps
- **Route No. generation** (globally unique, never reused)
- **OTP-based** trip verification (start/end)
- **Live tracking** with GPS updates
- **No-show marking** for absent employees
- **Emergency swap requests** for vehicle replacement
- **Cab rotation fairness** to distribute trips evenly
- **Role-based dashboards** for Admin, Driver, and Employee
- **Standalone backend operations app** for transport-control monitoring

---

## 🏗️ System Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Flutter   │  HTTP   │   Flask     │  SQL    │   SQLite    │
│   (Mobile)  │◀──────▶│  (Backend)  │◀──────▶│  (Database) │
└─────────────┘         └─────────────┘         └─────────────┘
      │                        │
      │                        │
      ▼                        ▼
 Google Maps API      Google Directions API
```

### Tech Stack
- **Frontend**: Flutter 3.4+ (Dart)
- **Standalone Ops Frontend**: Flutter 3.4+ (separate app folder)
- **Backend**: Python 3.8+ (Flask)
- **Database**: SQLite 3
- **Maps**: Google Maps API
- **State**: SharedPreferences (Flutter)

---

## ✅ Prerequisites

### Required Software
- **Python**: 3.8 or higher
- **Flutter**: 3.4 or higher
- **Git**: For cloning repository

### Required API Keys
- **Google Maps API Key** (for routing and live tracking)

### System Requirements
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 500MB free space
- **OS**: Windows 10/11, macOS 10.14+, or Linux

---

## 🔧 Backend Setup

### 1. Navigate to Backend Directory
```bash
cd "RG Travel Solution/rg_travel_backend"
```

### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Expected packages**:
- Flask
- flask-cors
- requests (for Google Maps API)
- bcrypt (for password hashing)

### 4. Configure Environment
Create `.env` file (optional):
```env
FLASK_ENV=development
FLASK_DEBUG=True
GOOGLE_MAPS_API_KEY=your_api_key_here
OTP_EXPIRY_MINUTES=5
RG_ALLOW_DB_RESET=True
```

### 5. Initialize Database
```bash
# Run migration script (idempotent - safe to run multiple times)
python db/migrate.py
```

**Expected output**:
```
✅ Migration completed successfully!
Summary:
  - All table schema updates applied
  - All indexes created
  - Foreign key constraints enabled
  - Database ready for STEP 2 backend
```

### 6. Verify Backend
```bash
# Start Flask server
python app.py
```

**Expected output**:
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

Test health endpoint:
```bash
curl http://localhost:5000/api/health
```

**Expected response**:
```json
{
  "success": true,
  "message": "RG Travel Backend is running",
  "timestamp": "2026-02-04T12:00:00"
}
```

---

## 📱 Flutter Setup

### 1. Navigate to Flutter Directory
```bash
cd "RG Travel Solution/rg_travel_flutter"
```

### 2. Install Dependencies
```bash
flutter pub get
```

### 3. Configure Google Maps API

#### Android
Edit `android/app/src/main/AndroidManifest.xml`:
```xml
<manifest ...>
  <application ...>
    <meta-data
        android:name="com.google.android.geo.API_KEY"
        android:value="YOUR_API_KEY_HERE"/>
  </application>
</manifest>
```

#### iOS
Edit `ios/Runner/AppDelegate.swift`:
```swift
import UIKit
import Flutter
import GoogleMaps

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GMSServices.provideAPIKey("YOUR_API_KEY_HERE")
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
```

#### Web
Edit `web/index.html`:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY_HERE"></script>
```

### 4. Verify Flutter
```bash
# Check devices
flutter devices

# Expected output shows available devices (Chrome, Android Emulator, etc.)
```

---

## 🖥️ Standalone Backend Ops App

This repo now contains a **separate Flutter app** for backend operations:

```bash
cd "RG Travel Solution/rg_backend_operations_app"
```

### Current Purpose

- keep backend operations separate from the main admin/driver/employee app
- provide a dedicated login and operations shell
- expose trip operations, request queues, fleet views, and support views

### Current Files

- `lib/screens/backend_operations_dashboard.dart`
- `lib/screens/ops_login_screen.dart`
- `lib/screens/trip_operations_screen.dart`
- `lib/screens/request_queue_screen.dart`
- `lib/screens/fleet_operations_screen.dart`
- `lib/screens/support_operations_screen.dart`

### Initialize Platform Folders

If platform folders are not present yet, run:

```powershell
.\setup_ops_app.ps1
```

### Run The Standalone Ops App

```powershell
.\run_ops_web.ps1
```

Or manually:

```bash
flutter pub get
flutter run -d chrome
```

### Important Note

The main travel app remains in `rg_travel_flutter/`.
The backend operations app is now separate in `rg_backend_operations_app/`.

---

## 🗄️ Database Migration

### Migration Script Features
- **Idempotent**: Safe to run multiple times
- **Non-destructive**: Only adds missing columns/tables
- **Validates**: Checks existing schema before changes

### Running Migrations
```bash
cd rg_travel_backend
python db/migrate.py
```

### Manual Schema Recreation (if needed)
```bash
# Delete existing database (DANGER: loses all data!)
rm rg_travel.db

# Recreate from schema.sql
sqlite3 rg_travel.db < db/schema.sql
```

### Verify Database Schema
```bash
sqlite3 rg_travel.db
```

```sql
-- List all tables
.tables

-- Check specific table structure
PRAGMA table_info(trips);

-- Verify foreign keys enabled
PRAGMA foreign_keys;  -- Should return 1

-- Exit
.exit
```

---

## 🚀 Running the Application

### Option 1: Chrome (Fastest for Development)
```bash
# Terminal 1: Start backend
cd rg_travel_backend
python app.py

# Terminal 2: Start Flutter (Chrome)
cd rg_travel_flutter
flutter run -d chrome
```

**Backend URL**: `http://127.0.0.1:5000`  
**Flutter URL**: `http://localhost:XXXXX` (auto-assigned port)

### Option 2: Android Emulator
```bash
# Terminal 1: Start backend
cd rg_travel_backend
python app.py

# Terminal 2: Start Flutter (Android)
cd rg_travel_flutter
flutter run
```

**Backend URL** in Flutter: `http://10.0.2.2:5000` (auto-configured)

### Option 3: iOS Simulator (macOS only)
```bash
# Terminal 1: Start backend
cd rg_travel_backend
python app.py

# Terminal 2: Start Flutter (iOS)
cd rg_travel_flutter
flutter run -d ios
```

---

## 🧪 Testing

### Backend Tests
```bash
cd rg_travel_backend

# Test OTP service
python -m pytest tests/test_otp_service.py

# Test tracking service
python -m pytest tests/test_tracking_service.py

# Run all tests
python -m pytest
```

### Flutter Tests
```bash
cd rg_travel_flutter

# Run unit tests
flutter test

# Run integration tests
flutter drive --target=test_driver/app.dart
```

### Manual Testing
Follow the comprehensive checklist: [`TESTING_CHECKLIST.md`](file:///C:/Users/HP/Desktop/RG%20Travel%20Solution/TESTING_CHECKLIST.md)

**Test Credentials**:
- **Admin**: Mobile `9325118627`, Password `Rushi123`
- **Driver**: Create via registration flow
- **Employee**: Create via registration flow

---

## 📦 Deployment

### Production Backend (Example: Heroku)

1. **Install Heroku CLI**
2. **Create Heroku App**
   ```bash
   heroku create rg-travel-backend
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set GOOGLE_MAPS_API_KEY=your_key
   heroku config:set FLASK_ENV=production
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

5. **Run Migration**
   ```bash
   heroku run python db/migrate.py
   ```

### Production Flutter (Web)

1. **Build for Web**
   ```bash
   flutter build web --release
   ```

2. **Deploy to Firebase Hosting** (example)
   ```bash
   firebase init hosting
   firebase deploy
   ```

### Production Database
For production, migrate from SQLite to PostgreSQL:
1. Update `db/__init__.py` to use PostgreSQL
2. Update connection string in environment
3. Re-run migrations

---

## 🔧 Troubleshooting

### Backend Issues

**Error**: `ModuleNotFoundError: No module named 'flask'`  
**Fix**: Install dependencies: `pip install -r requirements.txt`

**Error**: `Port 5000 already in use`  
**Fix**: Change port in `app.py` or kill process on port 5000

**Error**: `PRAGMA foreign_keys = ON failed`  
**Fix**: Update SQLite to 3.6.19 or higher

### Flutter Issues

**Error**: `Failed to fetch`  
**Fix**: Check backend URL in `lib/core/config/api_config.dart`
- Web: `http://127.0.0.1:5000`
- Android: `http://10.0.2.2:5000`

**Error**: `Google Maps not loading`  
**Fix**: Verify API key in platform-specific config files

**Error**: `Session not persisting`  
**Fix**: Check `SessionStore.saveSession()` called after login

### Database Issues

**Error**: `UNIQUE constraint failed: trips.route_no`  
**Fix**: Route No collision - retry will auto-generate new number

**Error**: `FOREIGN KEY constraint failed`  
**Fix**: Ensure foreign keys enabled: `PRAGMA foreign_keys = ON;`

---

## 📞 Support

For issues, contact:
- **Developer**: RG Team
- **Documentation**: See `docs/` folder
- **API Reference**: See `API_DOCS.md`

---

## 📄 License

Internal Project - RG Travel Solution  
© 2026 All Rights Reserved
