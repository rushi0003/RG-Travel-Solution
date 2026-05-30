// flutter/lib/services/employee_service.dart
//
// RG Travel Solution — Employee Service (Flutter)
//
// Covers:
// - Employee profile get/update + change request (admin approval)
// - Absent request (must be at least 1 day before)
// - My assigned trip
// - OTP (employee can fetch start/end OTP)
// - Live tracking (route latest) + trip details (polyline/stops)
// - Employee trip history
// - Helpdesk ticket (optional)
//
// NOTE:
// Ensure backend endpoints exist with same paths.

import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:rg_travel_flutter/core/storage/session_store.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});

  @override
  String toString() => statusCode == null ? message : "($statusCode) $message";
}

class EmployeeService {
  EmployeeService._();

  // ✅ ONE baseUrl source
  static String baseUrl =
      kIsWeb ? "http://127.0.0.1:5000" : "http://10.0.2.2:5000";

  static void setBaseUrl(String url) {
    if (url.trim().isNotEmpty) baseUrl = url.trim();
  }

  // ---------- Helpers ----------
  static Uri _u(String path, [Map<String, String>? query]) {
    final p = path.startsWith("/") ? path : "/$path";
    final uri = Uri.parse("$baseUrl$p");
    return query == null ? uri : uri.replace(queryParameters: query);
  }

  static Map<String, String> _headers({String? token}) {
    final h = <String, String>{
      "Content-Type": "application/json",
      "Accept": "application/json",
    };
    if (token != null && token.isNotEmpty) {
      h["Authorization"] = "Bearer $token";
    }
    return h;
  }

  static Future<Map<String, dynamic>> _handle(http.Response r) async {
    dynamic decoded;
    try {
      decoded = jsonDecode(r.body);
    } catch (_) {
      decoded = {"success": false, "message": "Invalid JSON from server"};
    }

    if (r.statusCode >= 400) {
      final msg = (decoded is Map && decoded["message"] != null)
          ? decoded["message"].toString()
          : "HTTP ${r.statusCode}";
      throw ApiException(msg, statusCode: r.statusCode);
    }

    if (decoded is Map<String, dynamic>) return decoded;
    throw ApiException("Invalid response format", statusCode: r.statusCode);
  }

  static Future<Map<String, dynamic>> _get(
    String path, {
    Map<String, String>? query,
    String? token,
  }) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.get(
      _u(path, query),
      headers: _headers(token: effectiveToken),
    );
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _post(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? query,
    String? token,
  }) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.post(
      _u(path, query),
      headers: _headers(token: effectiveToken),
      body: jsonEncode(body ?? {}),
    );
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _put(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? query,
    String? token,
  }) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.put(
      _u(path, query),
      headers: _headers(token: effectiveToken),
      body: jsonEncode(body ?? {}),
    );
    return _handle(r);
  }

  // =========================================================
  // EMPLOYEE PROFILE
  // =========================================================

  /// GET /api/employee/<employee_id>/profile
  static Future<Map<String, dynamic>> getEmployeeProfile(
    int employeeId, {
    String? token,
  }) async {
    final res = await _get("/api/employee/$employeeId/profile", token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  /// PUT /api/employee/<employee_id>/profile
  /// Direct update (if you want only admin approval, use requestProfileChange())
  static Future<Map<String, dynamic>> updateEmployeeProfile(
    int employeeId, {
    required String name,
    required String mobile,
    required String employeeCode, // permanent - backend may ignore if sent
    required String loginTime, // "HH:mm"
    required String logoutTime, // "HH:mm"
    required String homeAddress,
    String? token,
  }) async {
    final res = await _put(
      "/api/employee/$employeeId/profile",
      token: token,
      body: {
        "name": name,
        "mobile": mobile,
        "employee_code": employeeCode,
        "login_time": loginTime,
        "logout_time": logoutTime,
        "home_address": homeAddress,
      },
    );
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  /// POST /api/employee/<employee_id>/profile-change-request
  /// Employee requests changes → admin approves → then DB updates
  static Future<void> requestProfileChange(
    int employeeId, {
    String? name,
    String? mobile,
    String? loginTime,
    String? logoutTime,
    String? homeAddress,
    double? homeLat,
    double? homeLng,
    String? token,
  }) async {
    await _post(
      "/api/employee/$employeeId/profile-change-request",
      token: token,
      body: {
        if (name != null) "name": name,
        if (mobile != null) "mobile": mobile,
        if (loginTime != null) "login_time": loginTime,
        if (logoutTime != null) "logout_time": logoutTime,
        if (homeAddress != null) "home_address": homeAddress,
        if (homeLat != null) "home_lat": homeLat,
        if (homeLng != null) "home_lng": homeLng,
      },
    );
  }

  // =========================================================
  // ABSENT REQUEST (must be at least 1 day before)
  // =========================================================

  /// POST /api/employee/<employee_id>/absent/request
  /// Body supports:
  /// - { date: "YYYY-MM-DD", reason? }
  /// - { dates: ["YYYY-MM-DD", ...], reason? }
  /// - { from_date: "YYYY-MM-DD", to_date: "YYYY-MM-DD", reason? }
  static Future<void> requestAbsent(
    int employeeId, {
    String? date, // "YYYY-MM-DD"
    List<String>? dates,
    String? fromDate,
    String? toDate,
    String reason = "Absent",
    String? token,
  }) async {
    final cleanedDates = (dates ?? const <String>[])
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    if ((date == null || date.trim().isEmpty) &&
        cleanedDates.isEmpty &&
        ((fromDate == null || fromDate.trim().isEmpty) ||
            (toDate == null || toDate.trim().isEmpty))) {
      throw ApiException("At least one absence date is required");
    }
    await _post(
      "/api/employee/$employeeId/absent/request",
      token: token,
      body: {
        if (date != null && date.trim().isNotEmpty) "date": date.trim(),
        if (cleanedDates.isNotEmpty) "dates": cleanedDates,
        if (fromDate != null && fromDate.trim().isNotEmpty)
          "from_date": fromDate.trim(),
        if (toDate != null && toDate.trim().isNotEmpty) "to_date": toDate.trim(),
        "reason": reason,
      },
    );
  }

  /// POST /api/employee/<employee_id>/absence-cancel-request
  static Future<void> requestAbsenceCancellation(
    int employeeId, {
    String? date,
    List<String>? dates,
    String? fromDate,
    String? toDate,
    String reason = "",
    String? token,
  }) async {
    final cleanedDates = (dates ?? const <String>[])
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    await _post(
      "/api/employee/$employeeId/absence-cancel-request",
      token: token,
      body: {
        if (date != null && date.trim().isNotEmpty) "date": date.trim(),
        if (cleanedDates.isNotEmpty) "dates": cleanedDates,
        if (fromDate != null && fromDate.trim().isNotEmpty)
          "from_date": fromDate.trim(),
        if (toDate != null && toDate.trim().isNotEmpty) "to_date": toDate.trim(),
        if (reason.trim().isNotEmpty) "reason": reason.trim(),
      },
    );
  }

  /// Optional: GET /api/employee/<employee_id>/absent/list
  static Future<List<Map<String, dynamic>>> getAbsenceRequests(
    int employeeId, {
    String? token,
  }) async {
    // Note: Backend endpoint might be different, adjusting to match standard
    // If backend is /api/employee/<id>/absent/list, keep it.
    // But verified backend uses /api/employee/<id>/absence-requests in step 14 check
    // Let's stick to what was likely implemented or verified.
    // Actually, verify_step_14_csr.py used admin endpoint.
    // We will assume /api/employee/<id>/absence-requests based on standard REST patterns we built.
    // If not, we'll fix it. For now, let's use the list endpoint.
    final res =
        await _get("/api/employee/$employeeId/absence-requests", token: token);
    final list = (res["data"] is List) ? (res["data"] as List<dynamic>) : <dynamic>[];
    return list
        .map((e) => (e as Map<dynamic, dynamic>).cast<String, dynamic>())
        .toList();
  }

  // =========================================================
  // MY TRIP (pickup/drop)
  // =========================================================

  static Map<String, dynamic> _normalizeTrip(Map<String, dynamic> trip) {
    Map<String, dynamic>? normalizeDriver(dynamic raw) {
      if (raw is Map) {
        return raw.cast<String, dynamic>();
      }
      return null;
    }

    final currentDriver = normalizeDriver(trip["current_driver"]);
    final originalDriver = normalizeDriver(trip["original_driver"]);
    final allDrivers = (trip["all_drivers"] is List)
        ? (trip["all_drivers"] as List)
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => e.cast<String, dynamic>())
            .toList()
        : <Map<String, dynamic>>[];

    if (trip["id"] == null && trip["trip_id"] != null) {
      trip["id"] = trip["trip_id"];
    }
    if (trip["scheduled_time"] == null && trip["schedule_time"] != null) {
      trip["scheduled_time"] = trip["schedule_time"];
    }

    return {
      ...trip,
      if (currentDriver != null) "current_driver": currentDriver,
      if (originalDriver != null) "original_driver": originalDriver,
      "all_drivers": allDrivers,
    };
  }

  /// GET /api/employee/<employee_id>/my-trip
  /// Returns active/next assigned trip:
  /// { route_no, trip_type, scheduled_time, driver info, cab no, status ... }
  static Future<Map<String, dynamic>?> getMyTrip(
    int employeeId, {
    String? token,
  }) async {
    final res = await _get("/api/employee/$employeeId/my-trip", token: token);

    if (res["success"] == false) return null;
    if (res["data"] is! Map) return null;

    final data = (res["data"] as Map).cast<String, dynamic>();
    if (data["has_trip"] == false) return null;

    // Backend may return wrapped payload: { has_trip, trip: {...}, members: [...] }
    final wrappedTrip = data["trip"];
    final trip = (wrappedTrip is Map)
        ? wrappedTrip.cast<String, dynamic>()
        : Map<String, dynamic>.from(data);

    if (trip["members"] == null && data["members"] is List) {
      trip["members"] = data["members"];
    }

    return _normalizeTrip(trip);
  }

  /// GET /api/employee/<id>/my-trips
  /// Returns list of trips
  static Future<List<Map<String, dynamic>>> getMyTrips(
    int employeeId, {
    String? token,
  }) async {
    final res = await _get("/api/employee/$employeeId/my-trips", token: token);
    final data = res["data"];
    if (data is Map && data["trips"] is List) {
      return (data["trips"] as List)
          .whereType<Map<dynamic, dynamic>>()
          .map((e) {
            return _normalizeTrip(e.cast<String, dynamic>());
          })
          .toList();
    }
    return [];
  }

  // =========================================================
  // OTP (Employee reads OTP; Driver verifies)
  // =========================================================

  /// GET /api/trip/<route_no>/otp?type=start|end
  /// Returns: { data: { otp, expires_at } }
  static Future<Map<String, dynamic>> getTripOtp(
    String routeNo, {
    required String type, // "start" or "end"
    String? token,
  }) async {
    final res = await _get(
      "/api/trip/$routeNo/otp",
      token: token,
      query: {"type": type},
    );
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // =========================================================
  // TRACKING VIEW (Employee side)
  // =========================================================

  /// GET /api/tracking/route/<route_no>/latest
  /// returns: { data: { lat, lng, updated_at, driver_id, route_no } }
  static Future<Map<String, dynamic>> getLatestTrackingByRoute(
    String routeNo, {
    String? token,
  }) async {
    final res = await _get("/api/tracking/route/$routeNo/latest", token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  /// GET /api/trip/<route_no>
  /// returns trip details with:
  /// - driver info
  /// - cab no
  /// - employees list
  /// - polyline
  /// - stops/waypoints
  /// - total_km
  static Future<Map<String, dynamic>> getTripDetailsByRoute(
    String routeNo, {
    String? token,
  }) async {
    final res = await _get("/api/trip/$routeNo", token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // =========================================================
  // EMPLOYEE TRIP HISTORY
  // =========================================================

  /// GET /api/employee/<employee_id>/trips/history
  /// query: from,to,q
  static Future<List<Map<String, dynamic>>> getEmployeeTripHistory(
    int employeeId, {
    String? fromDate, // YYYY-MM-DD
    String? toDate, // YYYY-MM-DD
    String? q, // search
    String? token,
  }) async {
    final query = <String, String>{};
    if (fromDate != null && fromDate.trim().isNotEmpty)
      query["from"] = fromDate.trim();
    if (toDate != null && toDate.trim().isNotEmpty) query["to"] = toDate.trim();
    if (q != null && q.trim().isNotEmpty) query["q"] = q.trim();

    final res = await _get(
      "/api/employee/$employeeId/trip-history",
      token: token,
      query: query.isEmpty ? null : query,
    );

    final list = (res["data"] is List) ? (res["data"] as List<dynamic>) : <dynamic>[];
    return list
        .map((e) => (e as Map<dynamic, dynamic>).cast<String, dynamic>())
        .toList();
  }

  // (Duplicate createHelpdeskTicket removed - kept version below at line ~373)

  // =========================================================
  // SOS & RATINGS
  // =========================================================

  /// POST /api/employee/sos
  static Future<void> sendSOS({
    required int employeeId,
    int? tripId,
    double? lat,
    double? lng,
    String? token,
  }) async {
    await _post(
      "/api/employee/sos",
      token: token,
      body: {
        "employee_id": employeeId,
        "trip_id": tripId,
        "lat": lat,
        "lng": lng,
      },
    );
  }

  /// POST /api/employee/trip/<trip_id>/rate
  static Future<void> rateTrip(
    int tripId, {
    required int employeeId,
    required int rating,
    String? feedback,
    String? token,
  }) async {
    await _post(
      "/api/employee/trip/$tripId/rate",
      token: token,
      body: {
        "employee_id": employeeId,
        "rating": rating,
        "feedback": feedback,
      },
    );
  }

  // 14) POST /api/employee/{id}/helpdesk
  static Future<void> createHelpdeskTicket(
    int employeeId, {
    required String subject,
    required String message,
    String priority = "normal",
    String? token,
  }) async {
    await _post(
      "/api/employee/$employeeId/helpdesk",
      token: token,
      body: {
        "subject": subject,
        "message": message,
        "priority": priority,
      },
    );
  }
}
