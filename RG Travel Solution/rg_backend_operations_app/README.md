# RG Backend Operations App

Standalone Flutter app for backend operations monitoring and control.

## Scope

- Separate from the main `rg_travel_flutter` app
- Focused on backend/admin operations
- Uses the existing Flask backend APIs

## Current Structure

- `lib/main.dart`
- `lib/app.dart`
- `lib/screens/backend_operations_dashboard.dart`
- `lib/screens/ops_login_screen.dart`
- `lib/screens/trip_operations_screen.dart`
- `lib/screens/request_queue_screen.dart`
- `lib/screens/fleet_operations_screen.dart`
- `lib/screens/support_operations_screen.dart`
- `lib/screens/operations_ui.dart`
- `lib/services/admin_service.dart`
- `lib/services/admin_operations_service.dart`
- `lib/services/ops_auth_service.dart`
- `lib/services/ops_session_store.dart`
- `lib/models/admin_operations_snapshot.dart`

## Notes

- This app is intentionally separate from the main employee/driver/admin app.
- It currently contains a standalone operations shell with separate detail screens for overview, trips, requests, fleet, and support.
- It now includes its own login/session flow using the backend admin login API.
- It talks directly to the existing Flask backend endpoints for counts and status.
- Platform folders are not yet present in this repo folder.

## Initialize The App

From this folder:

```powershell
.\setup_ops_app.ps1
```

This will generate:

- `android/`
- `web/`
- `windows/`

without overwriting the custom `lib/` code.

## Run The App

After initialization:

```powershell
.\run_ops_web.ps1
```

Or manually:

```powershell
flutter pub get
flutter run -d chrome
```
