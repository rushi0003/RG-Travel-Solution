// flutter/lib/core/config/api_config.dart
//
// RG Travel Solution — API Config (Single source of truth)
//
// ✅ Purpose:
// - Keep ONLY ONE baseUrl in the whole app
// - Fix WEB vs Android Emulator host issue:
//   - Web:       http://127.0.0.1:5000  (NOT 10.0.2.2)
//   - Android:   http://10.0.2.2:5000
//   - iOS:       http://127.0.0.1:5000  (simulator usually works)
//   - Desktop:   http://127.0.0.1:5000
//
// ✅ Also provides endpoints constants for:
// - Auth, Admin, Driver, Employee
// - Grouping, Trips, OTP, Tracking, Emergency, Requests
//
// NOTE: Backend should ideally expose routes under "/api/..."
// If your backend currently uses "/admin/...", "/driver/..." etc,
// change the `apiPrefix` or the endpoint constants accordingly.

import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;

class ApiConfig {
  ApiConfig._(); // no instance

  // =========================
  // ENV SETTINGS
  // =========================

  /// Change this to false for production build.
  static const bool isDev = true;

  /// Backend default port
  static const int port = 5000;

  /// If backend uses "/api" prefix (recommended)
  static const String apiPrefix = '/api';

  // =========================
  // BASE URL (AUTO)
  // =========================

  /// Returns correct baseUrl based on platform.
  /// Web cannot access 10.0.2.2, so it uses 127.0.0.1.
  static String get baseUrl {
    if (!isDev) {
      // Production domain placeholder.
      return 'https://YOUR_PROD_DOMAIN.com';
    }

    if (kIsWeb) {
      // Flutter Web (Chrome/Edge) -> backend running on same PC
      return 'http://127.0.0.1:$port';
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      // Android emulator special loopback to host machine
      return 'http://10.0.2.2:$port';
    }

    // iOS simulator / Windows / macOS / Linux
    return 'http://127.0.0.1:$port';
  }

  /// Full API base like: http://127.0.0.1:5000/api
  static String get apiBase => '$baseUrl$apiPrefix';

  // =========================
  // COMMON HELPERS
  // =========================

  static String url(String path) {
    // Accept:
    // - "/api/admin/..." (absolute API path)
    // - "/admin/..." (auto prefixes apiBase)
    // - "admin/..." (auto prefixes apiBase + /)
    final p = path.trim();

    // If already absolute http(s)
    if (p.startsWith('http://') || p.startsWith('https://')) {
      return p;
    }

    // If already includes /api at start
    if (p.startsWith(apiPrefix)) {
      return '$baseUrl$p';
    }

    // Ensure begins with slash
    final normalized = p.startsWith('/') ? p : '/$p';

    // Attach /api prefix
    return '$apiBase$normalized';
  }

  // =========================
  // ENDPOINTS: AUTH
  // =========================

  static const String authLogin = '$apiPrefix/auth/login';
  static const String authLogout = '$apiPrefix/auth/logout';
  static const String authRegister = '$apiPrefix/auth/register';

  // =========================
  // ENDPOINTS: ADMIN
  // =========================

  static String adminProfile(int adminId) => '$apiPrefix/admin/$adminId';

  // Lists
  static const String adminDrivers = '$apiPrefix/admin/drivers';
  static const String adminEmployees = '$apiPrefix/admin/employees';

  // Requests
  static const String adminDriverRequests = '$apiPrefix/admin/driver-requests';
  static const String adminEmployeeRequests = '$apiPrefix/admin/employee-requests';

  static String approveDriverRequest(int driverId) =>
      '$apiPrefix/admin/driver-requests/$driverId/approve';
  static String rejectDriverRequest(int driverId) =>
      '$apiPrefix/admin/driver-requests/$driverId/reject';

  static String approveEmployeeRequest(int employeeId) =>
      '$apiPrefix/admin/employee-requests/$employeeId/approve';
  static String rejectEmployeeRequest(int employeeId) =>
      '$apiPrefix/admin/employee-requests/$employeeId/reject';

  // Hometown (go home) requests
  static const String adminDriverHomeTownRequests =
      '$apiPrefix/admin/driver-hometown-requests';

  static String approveDriverHomeTown(int driverId) =>
      '$apiPrefix/admin/driver-hometown/$driverId/approve';
  static String rejectDriverHomeTown(int driverId) =>
      '$apiPrefix/admin/driver-hometown/$driverId/reject';

  // Grouping + assign
  static const String adminCreateGroups = '$apiPrefix/admin/groups/create';
  static const String adminAssignTrip = '$apiPrefix/admin/trips/assign';

  // Trips
  static const String adminLiveTrips = '$apiPrefix/admin/trips/live';
  static const String adminTripHistory = '$apiPrefix/admin/trips/history';

  static String adminTripTracking(String routeNo) =>
      '$apiPrefix/admin/trips/$routeNo/tracking';

  static String adminCancelTrip(String routeNo) =>
      '$apiPrefix/admin/trips/$routeNo/cancel';
  static String adminCompleteTrip(String routeNo) =>
      '$apiPrefix/admin/trips/$routeNo/complete';

  // Live tracking
  static const String adminOnlineDrivers = '$apiPrefix/admin/drivers/online';

  // Emergency swap requests
  static const String adminEmergencyRequests = '$apiPrefix/admin/emergency-requests';
  static String adminApproveEmergency(String reqId) =>
      '$apiPrefix/admin/emergency-requests/$reqId/approve';
  static String adminRejectEmergency(String reqId) =>
      '$apiPrefix/admin/emergency-requests/$reqId/reject';

  // Absence approvals (optional)
  static String adminApproveAbsence(int employeeId) =>
      '$apiPrefix/admin/absence/$employeeId/approve';
  static String adminRejectAbsence(int employeeId) =>
      '$apiPrefix/admin/absence/$employeeId/reject';

  // =========================
  // ENDPOINTS: DRIVER
  // =========================

  static String driverProfile(int driverId) => '$apiPrefix/driver/$driverId';

  static String driverAssignedTrip(int driverId) =>
      '$apiPrefix/driver/$driverId/assigned-trip';

  static String driverVerifyOtp(int driverId, String routeNo) =>
      '$apiPrefix/driver/$driverId/trips/$routeNo/verify-otp';

  static String driverStartTrip(int driverId, String routeNo) =>
      '$apiPrefix/driver/$driverId/trips/$routeNo/start';

  static String driverCompleteTrip(int driverId, String routeNo) =>
      '$apiPrefix/driver/$driverId/trips/$routeNo/complete';

  static String driverNoShow(int driverId, String routeNo) =>
      '$apiPrefix/driver/$driverId/trips/$routeNo/no-show';

  static String driverSendLocation(int driverId, String routeNo) =>
      '$apiPrefix/driver/$driverId/trips/$routeNo/location';

  static String driverEmergencySwap(int driverId, String routeNo) =>
      '$apiPrefix/driver/$driverId/trips/$routeNo/emergency-swap';

  // Driver view tracking (optional unified endpoint)
  static String driverTripTracking(String routeNo) =>
      '$apiPrefix/driver/trips/$routeNo/tracking';

  // =========================
  // ENDPOINTS: EMPLOYEE
  // =========================

  static String employeeProfile(int employeeId) => '$apiPrefix/employee/$employeeId';

  static String employeeMyTrip(int employeeId) =>
      '$apiPrefix/employee/$employeeId/my-trip';

  /// Employee OTP GET:
  /// /api/employee/{id}/otp?route_no=...&type=start|end
  static String employeeGetOtp(int employeeId) => '$apiPrefix/employee/$employeeId/otp';

  static String employeeTripTracking(int employeeId, String routeNo) =>
      '$apiPrefix/employee/$employeeId/trips/$routeNo/tracking';

  // Employee absence (request) (optional)
  static String employeeAbsentRequest(int employeeId) =>
      '$apiPrefix/employee/$employeeId/absent';

  static String employeeTripHistory(int employeeId) =>
      '$apiPrefix/employee/$employeeId/history';

  // =========================
  // HEALTH
  // =========================
  static const String health = '$apiPrefix/health';

  // =========================
  // DEBUG PRINT (optional)
  // =========================
  static String debugSummary() {
    return 'ApiConfig(baseUrl=$baseUrl, apiBase=$apiBase, isDev=$isDev)';
  }
}
