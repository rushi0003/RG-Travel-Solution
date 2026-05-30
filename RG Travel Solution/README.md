# RG Travel Solution (Lite) 🚖  
A role-based Commute Driver style system using **Flutter (Frontend)** + **Flask (Backend)** + **SQLite (Database)**.

This project is a **lite version** of a professional commute/ride management system with:
- Admin dashboard (grouping + trip assignment)
- Driver dashboard (live trips + OTP start/end + no-show)
- Employee module (trip view + live tracking)
- Google Maps integration (routing/distance) — optional by API key

---

## ✅ Project Structure (Recommended)

Desktop
└── RG_TRAVEL_SOLUTION/
    │
    ├── README.md
    ├── .gitignore
    ├── .env.example                        # sample env (keys, secrets)
    │
    ├── rg_travel_backend/                  # Flask Backend
    │   │
    │   ├── app.py                          # main entry (run server / calls create_app)
    │   ├── wsgi.py                         # production entry (optional)
    │   ├── __init__.py                     # create_app() + register blueprints
    │   │
    │   ├── config/
    │   │   ├── __init__.py                 # loads env + constants
    │   │   ├── settings.py                 # OTP expiry, app constants
    │   │   └── keys.py                     # google maps key loader (from env)
    │   │
    │   ├── db/
    │   │   ├── __init__.py                 # get_db(), close_db(), init_db()
    │   │   ├── schema.sql                  # all tables schema
    │   │   └── migrations/                 # optional (future)
    │   │
    │   ├── routes/                         # API layer (request/response only)
    │   │   ├── __init__.py
    │   │   ├── auth_routes.py              # login/signup for admin/driver/employee
    │   │   ├── admin_routes.py             # approvals, grouping, assign trips, history, tracking
    │   │   ├── driver_routes.py            # driver profile, assigned trip, gps updates, otp verify
    │   │   ├── employee_routes.py          # employee profile, my trip, status
    │   │   └── health_routes.py            # /api/health
    │   │
    │   ├── services/                       # Business logic layer
    │   │   ├── __init__.py
    │   │   ├── grouping_service.py         # auto grouping employees
    │   │   ├── routing_service.py          # google directions/multi-stop routing
    │   │   ├── otp_service.py              # otp generate/verify + expiry
    │   │   ├── route_no_service.py         # 10-char route no + uniqueness rules
    │   │   ├── tracking_service.py         # driver live location store/fetch
    │   │   └── validation_service.py       # shared validations (mobile, etc.)
    │   │
    │   ├── repositories/                   # DB queries layer (optional but professional)
    │   │   ├── __init__.py
    │   │   ├── admin_repo.py
    │   │   ├── driver_repo.py
    │   │   ├── employee_repo.py
    │   │   └── trip_repo.py
    │   │
    │   ├── utils/
    │   │   ├── __init__.py
    │   │   ├── response.py                 # standard JSON response helper
    │   │   ├── security.py                 # hashing helpers
    │   │   └── time_utils.py               # timestamps, expiry helpers
    │   │
    │   ├── seeds/                          # One-time seed scripts (optional)
    │   │   ├── __init__.py
    │   │   ├── seed_admin.py
    │   │   ├── seed_drivers.py
    │   │   └── seed_employees.py
    │   │
    │   ├── requirements.txt
    │   └── rg_travel.db                    # (DO NOT COMMIT) created runtime
    │
    │
    ├── rg_travel_flutter/                  # Flutter App (Web + Android + iOS)
    │   │
    │   ├── pubspec.yaml
    │   ├── analysis_options.yaml
    │   ├── android/                     # Android native project
    │   │   ├── app/
    │   │   │   ├── src/
    │   │   │   │   ├── main/
    │   │   │   │   │   ├── AndroidManifest.xml
    │   │   │   │   │   ├── kotlin/
    │   │   │   │   │   │   └── com/
    │   │   │   │   │   │       └── rg/
    │   │   │   │   │   │           └── travel/
    │   │   │   │   │   │               └── solution/
    │   │   │   │   │   │                   └── MainActivity.kt
    │   │   │   │   │   ├── res/
    │   │   │   │   │   │   ├── layout/
    │   │   │   │   │   │   ├── mipmap-hdpi/
    │   │   │   │   │   │   ├── mipmap-mdpi/
    │   │   │   │   │   │   ├── mipmap-xhdpi/
    │   │   │   │   │   │   ├── mipmap-xxhdpi/
    │   │   │   │   │   │   └── mipmap-xxxhdpi/
    │   │   │   │   │   └── values/
    │   │   │   │   │       └── styles.xml
    │   │   │   │   ├── debug/
    │   │   │   │   │   └── AndroidManifest.xml
    │   │   │   │   └── profile/
    │   │   │   │       └── AndroidManifest.xml
    │   │   │   │
    │   │   │   └── build.gradle
    │   │   │
    │   │   ├── gradle/
    │   │   │   └── wrapper/
    │   │   │       ├── gradle-wrapper.jar
    │   │   │       └── gradle-wrapper.properties
    │   │   │
    │   │   ├── build.gradle
    │   │   ├── settings.gradle
    │   │   ├── gradle.properties
    │   │   └── local.properties
    │   │
    │   │
    │   ├── ios/                         # iOS native project
    │   │   ├── Podfile
    │   │   ├── Podfile.lock
    │   │   ├── Runner/
    │   │   │   ├── AppDelegate.swift
    │   │   │   ├── Info.plist
    │   │   │   ├── Runner.entitlements
    │   │   │   ├── Assets.xcassets/
    │   │   │   │   └── AppIcon.appiconset/
    │   │   │   ├── Base.lproj/
    │   │   │   │   ├── LaunchScreen.storyboard
    │   │   │   │   └── Main.storyboard
    │   │   │   └── GeneratedPluginRegistrant.swift
    │   │   │
    │   │   ├── Runner.xcodeproj
    │   │   └── Runner.xcworkspace
    │   │
    │   ├── web/                         # Flutter Web project
    │   │   ├── index.html
    │   │   ├── manifest.json
    │   │   ├── favicon.png
    │   │   └── icons/
    │   │       ├── Icon-192.png
    │   │       └── Icon-512.png
    │   │
    │   │
    │   │
    │   │
    │   ├── assets/
    │   │   ├── images/
    │   │   │   ├── background.png
    │   │   │   └── logo.png                # optional
    │   │   └── fonts/                      # Marathi/Unicode fonts (optional but recommended)
    │   │       ├── NotoSansDevanagari-Regular.ttf
    │   │       └── NotoSans-Regular.ttf
    │   │
    │   └── lib/
    │       ├── main.dart                   # app entry
    │       ├── app.dart                    # MaterialApp config (theme + routes)
    │       │
    │       ├── core/
    │       │   ├── config/
    │       │   │   ├── api_config.dart     # ✅ ONLY ONE baseUrl here
    │       │   │   └── env.dart            # optional (dev/prod)
    │       │   │
    │       │   ├── network/
    │       │   │   ├── api_client.dart     # GET/POST wrapper + headers + errors
    │       │   │   └── api_exception.dart
    │       │   │
    │       │   ├── storage/
    │       │   │   └── session_store.dart  # save token/userId/role
    │       │   │
    │       │   └── utils/
    │       │       ├── validators.dart
    │       │       └── constants.dart
    │       │
    │       ├── models/
    │       │   ├── admin_model.dart
    │       │   ├── driver_model.dart
    │       │   ├── employee_model.dart
    │       │   └── trip_model.dart
    │       │
    │       ├── services/                   # API services (role-wise)
    │       │   ├── auth_service.dart
    │       │   ├── admin_service.dart
    │       │   ├── driver_service.dart
    │       │   └── employee_service.dart
    │       │
    │       ├── screens/
    │       │   ├── login/
    │       │   │   └── login_screen.dart
    │       │   │
    │       │   ├── admin/
    │       │   │   ├── admin_dashboard.dart
    │       │   │   ├── admin_profile_sheet.dart
    │       │   │   ├── create_group_assign_screen.dart
    │       │   │   ├── live_trips_screen.dart
    │       │   │   ├── drivers_screen.dart
    │       │   │   ├── employees_screen.dart
    │       │   │   ├── trip_history_screen.dart
    │       │   │   └── live_tracking_screen.dart
    │       │   │
    │       │   ├── driver/
    │       │   │   ├── driver_dashboard.dart
    │       │   │   ├── driver_profile_screen.dart
    │       │   │   ├── assigned_trip_screen.dart
    │       │   │   └── otp_screen.dart
    │       │   │
    │       │   └── employee/
    │       │       ├── employee_dashboard.dart
    │       │       ├── my_trip_screen.dart
    │       │       └── live_tracking_view.dart
    │       │
    │       ├── widgets/
    │       │   ├── common/
    │       │   │   ├── rg_button.dart
    │       │   │   ├── rg_card.dart
    │       │   │   └── rg_loader.dart
    │       │   │
    │       │   ├── trip/
    │       │   │   ├── trip_card.dart
    │       │   │   └── otp_dialog.dart
    │       │   │
    │       │   └── layout/
    │       │       └── side_profile_drawer.dart
    │       │
    │       └── state/                      # optional (future: Provider/BLoC)
    │           ├── admin_provider.dart
    │           └── trip_provider.dart
    │
    └── docs/                               # Documentation (optional but recommended)
        ├── API_DOCS.md                     # endpoints list + sample payloads
        ├── DB_SCHEMA.md                    # schema explanation
        └── FLOW.md                         # full system flow



---

## ✅ Tech Stack

### Frontend
- **Flutter** (Android/Web/Desktop)
- UI: Futuristic theme + background image support

### Backend
- **Flask** REST API
- **CORS enabled** (Flutter can call API)

### Database
- **SQLite**
- Schema: trips, employees, drivers, admins, sessions, route_numbers, etc.

---

## ✅ Setup Instructions

### 1) Backend Setup (Flask)

#### Step 1: Open terminal in backend folder
```bash
cd RG_TRAVEL_SOLUTION/backend
