// flutter/lib/services/admin_service.dart
//
// RG Travel Solution â€” Admin Service (Flutter)
// Centralized API calls for Admin module.
// - Supports Web (127.0.0.1) and Emulator (10.0.2.2)
// - Provides GET/POST/PUT helpers + consistent error handling
//
// NOTE:
// This file assumes your backend endpoints exist as documented.
// If any endpoint differs, change ONLY the path strings below.

import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb, debugPrint;
import 'package:flutter/services.dart' show Clipboard, ClipboardData;
import 'package:http/http.dart' as http;
import 'package:rg_travel_flutter/core/storage/session_store.dart';
import 'package:url_launcher/url_launcher.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});

  @override
  String toString() => statusCode == null ? message : "($statusCode) $message";
}

class AdminService {
  AdminService._();

  // âœ… ONE baseUrl source (override if needed)
  static String baseUrl =
      kIsWeb ? "http://127.0.0.1:5000" : "http://10.0.2.2:5000";

  static void setBaseUrl(String url) {
    if (url.trim().isNotEmpty) baseUrl = url.trim();
  }

  // -------------- Helpers --------------

  static Uri _u(String path, [Map<String, String>? query]) {
    final p = path.startsWith("/") ? path : "/$path";
    final uri = Uri.parse("$baseUrl$p");
    return query == null ? uri : uri.replace(queryParameters: query);
  }

  static Map<String, String> _headers(
      {String? token, bool withJsonContentType = true}) {
    // If you later add JWT token, pass token here.
    final h = <String, String>{"Accept": "application/json"};
    if (withJsonContentType) h["Content-Type"] = "application/json";
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
      String msg = (decoded is Map && decoded["message"] != null)
          ? decoded["message"].toString()
          : "HTTP ${r.statusCode}";
      if (decoded is Map &&
          decoded["error"] is Map &&
          (decoded["error"]["code"]?.toString() ?? "") ==
              "HYBRID_PROVIDER_UNAVAILABLE") {
        msg =
            "Hybrid route provider unavailable. Please check /api/health/hybrid and backend route provider config.";
      }
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
      headers: _headers(token: effectiveToken, withJsonContentType: false),
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
      headers: _headers(token: effectiveToken, withJsonContentType: true),
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
      headers: _headers(token: effectiveToken, withJsonContentType: true),
      body: jsonEncode(body ?? {}),
    );
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _delete(
    String path, {
    Map<String, String>? query,
    String? token,
  }) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.delete(
      _u(path, query),
      headers: _headers(token: effectiveToken),
    );
    return _handle(r);
  }

  // -------------- Admin Profile --------------

  /// GET admin profile (supports multiple backend path variants)
  static Future<Map<String, dynamic>> getAdminProfile(int adminId,
      {String? token}) async {
    final paths = [
      "/api/admin/$adminId/profile",
      "/api/admin/profile/$adminId",
      "/api/admin/$adminId",
    ];
    Object? lastError;
    for (final p in paths) {
      try {
        final res = await _get(p, token: token);
        return (res["data"] is Map)
            ? (res["data"] as Map).cast<String, dynamic>()
            : {};
      } catch (e) {
        lastError = e;
      }
    }
    throw ApiException("Admin profile endpoint not available: $lastError");
  }

  static Future<Map<String, dynamic>> getAdminProfileById(String adminId,
      {String? token}) async {
    final normalized = adminId.trim();
    if (normalized.isEmpty) {
      throw ApiException("Admin id is required");
    }
    final paths = [
      "/api/admin/$normalized/profile",
      "/api/admin/profile/$normalized",
      "/api/admin/$normalized",
    ];
    Object? lastError;
    for (final p in paths) {
      try {
        final res = await _get(p, token: token);
        return (res["data"] is Map)
            ? (res["data"] as Map).cast<String, dynamic>()
            : {};
      } catch (e) {
        lastError = e;
      }
    }
    throw ApiException("Admin profile endpoint not available: $lastError");
  }

  /// PUT admin profile (supports multiple backend path variants)
  static Future<Map<String, dynamic>> updateAdminProfile(
    int adminId, {
    required String name,
    required String mobile,
    required String officeName,
    required String officeAddress,
    double? officeLat,
    double? officeLng,
    String? token,
  }) async {
    final body = {
      "name": name,
      "mobile": mobile,
      "office_name": officeName,
      "office_address": officeAddress,
      if (officeLat != null) "office_lat": officeLat,
      if (officeLng != null) "office_lng": officeLng,
    };
    final paths = [
      "/api/admin/$adminId/profile",
      "/api/admin/profile/$adminId",
      "/api/admin/$adminId",
    ];
    Object? lastError;
    for (final p in paths) {
      try {
        final res = await _put(p, token: token, body: body);
        return (res["data"] is Map)
            ? (res["data"] as Map).cast<String, dynamic>()
            : {};
      } catch (e) {
        lastError = e;
      }
    }
    throw ApiException(
        "Admin profile update endpoint not available: $lastError");
  }

  // -------------- Requests (Approvals) --------------

  /// GET /api/admin/driver-requests
  static Future<List<Map<String, dynamic>>> getDriverRequests(
      {String? token}) async {
    final res = await _get("/api/admin/driver-requests", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/driver-requests/<request_id>/approve
  static Future<void> approveDriverRequest(int requestId,
      {String? token}) async {
    await _post("/api/admin/driver-requests/$requestId/approve", token: token);
  }

  /// POST /api/admin/driver-requests/<request_id>/reject
  static Future<void> rejectDriverRequest(int requestId,
      {String? token, String reason = ""}) async {
    await _post(
      "/api/admin/driver-requests/$requestId/reject",
      token: token,
      body: {"reason": reason},
    );
  }

  /// GET /api/admin/employee-requests
  static Future<List<Map<String, dynamic>>> getEmployeeRequests(
      {String? token}) async {
    final res = await _get("/api/admin/employee-requests", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/employee-requests/<request_id>/approve
  static Future<void> approveEmployeeRequest(int requestId,
      {String? token}) async {
    await _post("/api/admin/employee-requests/$requestId/approve",
        token: token);
  }

  /// POST /api/admin/employee-requests/<request_id>/reject
  static Future<void> rejectEmployeeRequest(int requestId,
      {String? token, String reason = ""}) async {
    await _post(
      "/api/admin/employee-requests/$requestId/reject",
      token: token,
      body: {"reason": reason},
    );
  }

  // -------------- Employee Change Requests (Profile Updates) --------------

  /// GET /api/admin/employee-change-requests
  static Future<List<Map<String, dynamic>>> getEmployeeChangeRequests(
      {String? token, String status = "pending"}) async {
    final res = await _get(
      "/api/admin/employee-change-requests",
      token: token,
      query: {"status": status},
    );
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/employee-change-requests/<request_id>/approve
  static Future<void> approveEmployeeChange(int requestId,
      {String? token}) async {
    await _post("/api/admin/employee-change-requests/$requestId/approve",
        token: token);
  }

  /// POST /api/admin/employee-change-requests/<request_id>/reject
  static Future<void> rejectEmployeeChange(int requestId,
      {String? token, String reason = ""}) async {
    await _post(
      "/api/admin/employee-change-requests/$requestId/reject",
      token: token,
      body: {"reason": reason},
    );
  }

  // -------------- Driver Change Requests --------------

  /// GET /api/admin/driver-change-requests
  static Future<List<Map<String, dynamic>>> getDriverChangeRequests(
      {String? token}) async {
    final res = await _get("/api/admin/driver-change-requests", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/driver-change-requests/<request_id>/approve
  static Future<void> approveDriverChange(int requestId,
      {String? token}) async {
    await _post("/api/admin/driver-change-requests/$requestId/approve",
        token: token);
  }

  /// POST /api/admin/driver-change-requests/<request_id>/reject
  static Future<void> rejectDriverChange(int requestId, {String? token}) async {
    await _post("/api/admin/driver-change-requests/$requestId/reject",
        token: token);
  }

  // -------------- Swap Requests --------------

  /// GET /api/admin/swap-requests
  static Future<List<Map<String, dynamic>>> getSwapRequests(
      {String? token}) async {
    final res = await _get("/api/admin/swap-requests", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/swap-requests/<request_id>/approve
  static Future<void> approveSwapRequest(int requestId, {String? token}) async {
    await _post("/api/admin/swap-requests/$requestId/approve", token: token);
  }

  /// POST /api/admin/swap-requests/<request_id>/reject
  static Future<void> rejectSwapRequest(int requestId, {String? token}) async {
    await _post("/api/admin/swap-requests/$requestId/reject", token: token);
  }

  // -------------- Trip Cancel Requests (Driver -> Admin) --------------

  /// GET /api/admin/trip-cancel-requests
  static Future<List<Map<String, dynamic>>> getTripCancelRequests(
      {String? token}) async {
    final res = await _get("/api/admin/trip-cancel-requests", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/trip-cancel-requests/<request_id>/approve
  static Future<void> approveTripCancelRequest(
    int requestId, {
    String? note,
    String? adminId,
    String? token,
  }) async {
    await _post(
      "/api/admin/trip-cancel-requests/$requestId/approve",
      token: token,
      body: {
        if (note != null && note.trim().isNotEmpty) "note": note.trim(),
        if (adminId != null && adminId.trim().isNotEmpty)
          "admin_id": adminId.trim(),
      },
    );
  }

  /// POST /api/admin/trip-cancel-requests/<request_id>/reject
  static Future<void> rejectTripCancelRequest(
    int requestId, {
    String? note,
    String? adminId,
    String? token,
  }) async {
    await _post(
      "/api/admin/trip-cancel-requests/$requestId/reject",
      token: token,
      body: {
        if (note != null && note.trim().isNotEmpty) "note": note.trim(),
        if (adminId != null && adminId.trim().isNotEmpty)
          "admin_id": adminId.trim(),
      },
    );
  }

  // -------------- Absence Requests (Employee) --------------

  /// GET /api/admin/absence-requests
  static Future<List<Map<String, dynamic>>> getAbsenceRequests(
      {String? token}) async {
    final res = await _get("/api/admin/absence-requests", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/absence-requests/<request_id>/approve
  static Future<void> approveAbsenceRequest(int requestId,
      {String? token}) async {
    await _post("/api/admin/absence-requests/$requestId/approve", token: token);
  }

  /// POST /api/admin/absence-requests/<request_id>/reject
  static Future<void> rejectAbsenceRequest(int requestId,
      {String? token, String reason = ""}) async {
    await _post(
      "/api/admin/absence-requests/$requestId/reject",
      token: token,
      body: {"reason": reason},
    );
  }

  /// GET /api/admin/absent-employees
  static Future<List<Map<String, dynamic>>> getAbsentEmployees({
    String? token,
    String? onOrAfter,
  }) async {
    final query = <String, String>{};
    if (onOrAfter != null && onOrAfter.trim().isNotEmpty) {
      query["on_or_after"] = onOrAfter.trim();
    }
    final res = await _get(
      "/api/admin/absent-employees",
      token: token,
      query: query.isEmpty ? null : query,
    );
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/absent-employees/<employee_id>/remove
  static Future<void> removeAbsentEmployee(
    int employeeId, {
    required List<String> dates,
    String reason = "",
    String? adminId,
    String? token,
  }) async {
    await _post(
      "/api/admin/absent-employees/$employeeId/remove",
      token: token,
      body: {
        "dates": dates,
        if (reason.trim().isNotEmpty) "reason": reason.trim(),
        if (adminId != null && adminId.trim().isNotEmpty) "admin_id": adminId.trim(),
      },
    );
  }

  // -------------- Master Lists & CRUD --------------

  /// GET /api/admin/drivers
  static Future<List<Map<String, dynamic>>> getDrivers({String? token}) async {
    final res = await _get("/api/admin/drivers", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/drivers
  static Future<void> createDriver(Map<String, dynamic> data,
      {String? token}) async {
    await _post("/api/admin/drivers", body: data, token: token);
  }

  /// PUT /api/admin/drivers/<id>
  static Future<void> updateDriver(String driverId, Map<String, dynamic> data,
      {String? token}) async {
    await _put("/api/admin/drivers/$driverId", body: data, token: token);
  }

  /// DELETE /api/admin/drivers/<id>
  static Future<void> deleteDriver(String driverId, {String? token}) async {
    await _delete("/api/admin/drivers/$driverId", token: token);
  }

  /// GET /api/admin/drivers/search
  static Future<List<Map<String, dynamic>>> searchDrivers(String query,
      {String? token}) async {
    final res = await _get("/api/admin/drivers/search",
        query: {"query": query}, token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// GET /api/admin/employees
  static Future<List<Map<String, dynamic>>> getEmployees(
      {String? search, String? token}) async {
    final query = search != null ? {"search": search} : null;
    final res = await _get("/api/admin/employees", query: query, token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/employees
  static Future<Map<String, dynamic>> createEmployee(Map<String, dynamic> data,
      {String? token}) async {
    final res = await _post("/api/admin/employees", body: data, token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  /// PUT /api/admin/employees/<id>
  static Future<void> updateEmployee(String empId, Map<String, dynamic> data,
      {String? token}) async {
    await _put("/api/admin/employees/$empId", body: data, token: token);
  }

  /// DELETE /api/admin/employees/<id>
  static Future<void> deleteEmployee(String empId, {String? token}) async {
    await _delete("/api/admin/employees/$empId", token: token);
  }

  /// GET /api/admin/drivers/online
  static Future<List<Map<String, dynamic>>> getOnlineDrivers(
      {String? token}) async {
    final res = await _get("/api/admin/drivers/online", token: token);
    final data = res["data"];
    final list = (data is Map && data["online_drivers"] is List<dynamic>)
        ? (data["online_drivers"] as List<dynamic>)
        : (data is List<dynamic> ? data : const <dynamic>[]);
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  // -------------- Trip Management --------------

  // (Duplicate methods removed: getLiveTrips, completeTrip, cancelTrip - kept better int-based versions below at line ~425+)

  /// POST /api/admin/trips/<id>/swap-cab
  static Future<void> swapTripCab(String tripId, String cabNo,
      {String? token}) async {
    await _post("/api/admin/trips/$tripId/swap-cab",
        body: {"cab_no": cabNo}, token: token);
  }

  /// POST /api/admin/trips/<id>/add-employee
  static Future<void> addTripEmployee(String tripId, String empId,
      {String? token}) async {
    await _post("/api/admin/trips/$tripId/add-employee",
        body: {"employee_id": empId}, token: token);
  }

  /// POST /api/admin/trips/<id>/remove-employee
  static Future<void> removeTripEmployee(String tripId, String empId,
      {String? token}) async {
    await _post("/api/admin/trips/$tripId/remove-employee",
        body: {"employee_id": empId}, token: token);
  }

  // -------------- Grouping & Assign Trip --------------

  /// POST /api/admin/groups/auto
  ///
  /// payload:
  ///   trip_type: pickup/drop
  ///   vehicle_type: 4 or 6 (seat count)
  ///   scheduled_time: "HH:mm" or ISO datetime string
  ///   admin_id: admin UUID
  ///   office_lat, office_lng: office coordinates
  ///   employee_ids: [1,2,3] optional (admin manual selection)
  ///
  /// returns:
  ///   { data: { groups: [ ... ] } }
  static Future<Map<String, dynamic>> createAutoGroups({
    required String tripType,
    required List<int> vehicleTypes,
    required String scheduledTime,
    required String adminId,
    required double officeLat,
    required double officeLng,
    List<int>? employeeIds,
    List<int>? selectedVehicleIds,
    bool vehiclePriorityEnabled = true,
    String? token,
  }) async {
    final body = {
      "trip_type": tripType,
      "vehicle_types": vehicleTypes,
      "time_slot": scheduledTime,
      "selected_time": scheduledTime,
      "scheduled_time": scheduledTime,
      "admin_id": adminId,
      "office_lat": officeLat,
      "office_lng": officeLng,
      if (employeeIds != null) "employee_ids": employeeIds,
      if (employeeIds != null) "selected_employee_ids": employeeIds,
      if (selectedVehicleIds != null && selectedVehicleIds.isNotEmpty)
        "driver_ids": selectedVehicleIds,
      if (selectedVehicleIds != null && selectedVehicleIds.isNotEmpty)
        "selected_vehicle_ids": selectedVehicleIds,
      if (selectedVehicleIds != null && selectedVehicleIds.isNotEmpty)
        "vehicle_priority_enabled": vehiclePriorityEnabled,
    };

    const paths = [
      "/api/grouping/preview",
      "/api/groups/preview",
      "/api/admin/groups/auto",
      "/api/v2/trips/preview",
    ];

    Map<String, dynamic>? res;
    Object? lastError;
    for (final path in paths) {
      try {
        res = await _post(path, token: token, body: body);
        break;
      } catch (e) {
        lastError = e;
      }
    }
    if (res == null) {
      throw ApiException("Failed to generate groups: $lastError");
    }

    if (res["success"] == false) {
      String msg = res["message"]?.toString() ?? "Failed to generate groups";
      final data = res["data"];
      if (data is Map && data["exclusion_summary"] is List) {
        final summary = (data["exclusion_summary"] as List).join("\nâ€¢ ");
        msg += "\n\nExclusions:\nâ€¢ $summary";
      }
      throw ApiException(msg);
    }

    final data = (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    return data;
  }

  /// POST /api/v2/trips/create
  ///
  /// Create trip with OTP generation and driver assignment
  ///
  /// payload:
  ///   groups_to_create: list of groups with driver assignments
  ///   admin_id, trip_type, scheduled_time, vehicle_type
  ///   office location is resolved backend-side from admin profile
  ///
  /// returns:
  ///   { data: {
  ///       trip_id,
  ///       route_no,
  ///       start_otp,
  ///       end_otp,
  ///       otp_expiry,
  ///       status,
  ///       employee_count
  ///     } }
  static Future<Map<String, dynamic>> assignGroupTrip({
    required Map<String, dynamic> groupData,
    String? driverId,
    required String cabNo,
    required String adminId,
    required String tripType,
    required String scheduledTime,
    required List<int> vehicleTypes,
    String? tripDay,
    String? token,
  }) async {
    final res = await _post(
      "/api/v2/trips/create",
      token: token,
      body: {
        "groups_to_create": [
          {
            "group_data": groupData,
            if (driverId != null && driverId.trim().isNotEmpty)
              "driver_id": driverId,
            "cab_no": cabNo,
          }
        ],
        "admin_id": adminId,
        "trip_type": tripType,
        "selected_time": scheduledTime,
        "vehicle_types": vehicleTypes,
        if (tripDay != null && tripDay.isNotEmpty) "trip_day": tripDay,
      },
    );

    if (res["success"] == false) {
      throw ApiException(res["message"]?.toString() ?? "Failed to create trip");
    }

    // Response contains { data: { trips_created: [ ... ], summary: {...} } }
    if (res["data"] is Map) {
      final dataMap = (res["data"] as Map);
      if (dataMap["trips_created"] is List &&
          (dataMap["trips_created"] as List).isNotEmpty) {
        final tripData = (dataMap["trips_created"] as List)[0] as Map;
        return (tripData).cast<String, dynamic>();
      }
      return dataMap.cast<String, dynamic>();
    }

    return {};
  }

  /// POST /api/v2/trips/create
  ///
  /// Bulk variant of assignGroupTrip. Uses the same backend contract with
  /// multiple `groups_to_create` items so all trips can be assigned together.
  static Future<Map<String, dynamic>> assignMultipleGroupTrips({
    required List<Map<String, dynamic>> groupsToCreate,
    required String adminId,
    required String tripType,
    required String scheduledTime,
    required List<int> vehicleTypes,
    String? tripDay,
    String? token,
  }) async {
    final payloadGroups = groupsToCreate
        .map((entry) => {
              "group_data": entry["group_data"],
              if ((entry["driver_id"]?.toString().trim().isNotEmpty ?? false))
                "driver_id": entry["driver_id"].toString().trim(),
              "cab_no": (entry["cab_no"] ?? "").toString(),
            })
        .toList();

    final res = await _post(
      "/api/v2/trips/create",
      token: token,
      body: {
        "groups_to_create": payloadGroups,
        "admin_id": adminId,
        "trip_type": tripType,
        "selected_time": scheduledTime,
        "vehicle_types": vehicleTypes,
        if (tripDay != null && tripDay.isNotEmpty) "trip_day": tripDay,
      },
    );

    if (res["success"] == false) {
      throw ApiException(res["message"]?.toString() ?? "Failed to create trips");
    }

    if (res["data"] is Map) {
      return (res["data"] as Map).cast<String, dynamic>();
    }

    return {};
  }

  /// Utility: Copy text to clipboard
  static Future<void> copyToClipboard(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
  }

  static String buildTripHistoryExportUrl({
    String? q,
    String? status,
    String? type,
    String? fromDate,
    String? toDate,
    String? sort,
    String? driverId,
    int? employeeId,
  }) {
    final query = <String, String>{};
    if (q != null && q.trim().isNotEmpty) query["search"] = q.trim();
    if (status != null && status != "all") query["status"] = status;
    if (type != null && type != "all") query["type"] = type;
    if (fromDate != null && fromDate.trim().isNotEmpty) {
      query["from"] = fromDate.trim();
    }
    if (toDate != null && toDate.trim().isNotEmpty) query["to"] = toDate.trim();
    if (sort != null) query["sort"] = sort;
    if (driverId != null && driverId.trim().isNotEmpty) {
      query["driver_id"] = driverId.trim();
    }
    if (employeeId != null) query["employee_id"] = employeeId.toString();
    return _u("/api/v2/trips/history/export", query).toString();
  }

  static Future<void> exportTripHistory({
    String? q,
    String? status,
    String? type,
    String? fromDate,
    String? toDate,
    String? sort,
    String? driverId,
    int? employeeId,
  }) async {
    final url = buildTripHistoryExportUrl(
      q: q,
      status: status,
      type: type,
      fromDate: fromDate,
      toDate: toDate,
      sort: sort,
      driverId: driverId,
      employeeId: employeeId,
    );
    final uri = Uri.parse(url);
    final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!launched) {
      throw ApiException("Unable to open export URL");
    }
  }

  /// Optional: route no generation if you generate before assign
  /// POST /api/admin/route-no/generate
  static Future<String> generateRouteNo({String? token}) async {
    final res = await _post("/api/admin/route-no/generate", token: token);
    // expected: { data: { route_no: "2601...." } }
    final data = (res["data"] is Map<String, dynamic>)
        ? (res["data"] as Map<String, dynamic>)
        : const <String, dynamic>{};
    return (data["route_no"] ?? res["route_no"] ?? "").toString();
  }

  /// POST /api/admin/trips/assign
  ///
  /// payload:
  ///   group_id, driver_id, cab_no, trip_type, scheduled_time
  ///
  /// returns:
  ///   { data: { trip_id, route_no } }
  static Future<Map<String, dynamic>> assignTrip({
    required int groupId,
    required String driverId,
    required String cabNo,
    required String tripType,
    required String scheduledTime,
    String? routeNo, // if you pre-generated
    String? token,
  }) async {
    final res = await _post(
      "/api/admin/trips/assign",
      token: token,
      body: {
        "group_id": groupId,
        "driver_id": driverId,
        "cab_no": cabNo,
        "trip_type": tripType,
        "scheduled_time": scheduledTime,
        if (routeNo != null && routeNo.isNotEmpty) "route_no": routeNo,
      },
    );
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // -------------- Live Trips / History --------------

  /// GET /api/admin/trips/live
  static Future<List<Map<String, dynamic>>> getLiveTrips(
      {String? token}) async {
    final res = await _get("/api/admin/trips/live", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list
        .map((e) => _normalizeLiveTrip((e as Map).cast<String, dynamic>()))
        .toList();
  }

  static Map<String, dynamic> _normalizeLiveTrip(Map<String, dynamic> trip) {
    Map<String, dynamic>? normalizeDriver(dynamic raw) {
      if (raw is Map) {
        return raw.cast<String, dynamic>();
      }
      return null;
    }

    final rawEmployees = (trip["employees"] is List)
        ? (trip["employees"] as List)
        : ((trip["members"] is List) ? (trip["members"] as List) : <dynamic>[]);

    final employees = rawEmployees.map((e) {
      final m = (e as Map).cast<String, dynamic>();
      return {
        ...m,
        // Admin live endpoint often returns `is_no_show`; UI reads `no_show`.
        "no_show": m["no_show"] ?? m["is_no_show"] ?? 0,
      };
    }).toList();

    final currentDriver = normalizeDriver(trip["current_driver"]);
    final originalDriver = normalizeDriver(trip["original_driver"]);
    final allDrivers = (trip["all_drivers"] is List)
        ? (trip["all_drivers"] as List)
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => e.cast<String, dynamic>())
            .toList()
        : <Map<String, dynamic>>[];

    return {
      ...trip,
      "employees": employees,
      if (currentDriver != null) "current_driver": currentDriver,
      if (originalDriver != null) "original_driver": originalDriver,
      "all_drivers": allDrivers,
    };
  }

  /// GET /api/admin/trips/history
  ///
  /// query filters:
  ///   q, from, to, driver_id, employee_id
  static Future<Map<String, dynamic>> getTripHistory({
    String? q,
    String? status,
    String? type,
    String? fromDate, // YYYY-MM-DD
    String? toDate, // YYYY-MM-DD
    String? sort, // latest, km_desc, km_asc
    String? driverId,
    int? employeeId,
    int? limit,
    int? offset,
    String? token,
  }) async {
    final query = <String, String>{};
    if (q != null && q.trim().isNotEmpty) query["search"] = q.trim();
    if (status != null && status != "all") query["status"] = status;
    if (type != null && type != "all") query["type"] = type;
    if (fromDate != null && fromDate.trim().isNotEmpty)
      query["from"] = fromDate.trim();
    if (toDate != null && toDate.trim().isNotEmpty) query["to"] = toDate.trim();
    if (sort != null) query["sort"] = sort;
    if (driverId != null) query["driver_id"] = driverId;
    if (employeeId != null) query["employee_id"] = employeeId.toString();
    if (limit != null) query["limit"] = limit.toString();
    if (offset != null) query["offset"] = offset.toString();

    final res = await _get("/api/v2/trips/history", query: query, token: token);
    final data = res["data"];
    if (data is Map && data["trips"] is List) {
      final list = data["trips"] as List;
      return {
        "trips": list.map((e) => (e as Map).cast<String, dynamic>()).toList(),
        "total_count": data["total_count"] ?? list.length,
        "limit": data["limit"] ?? limit ?? list.length,
        "offset": data["offset"] ?? offset ?? 0,
      };
    }
    return {
      "trips": <Map<String, dynamic>>[],
      "total_count": 0,
      "limit": limit ?? 0,
      "offset": offset ?? 0,
    };
  }

  static Future<List<Map<String, dynamic>>> getBillingVehicleAssignments({
    String? search,
    String? token,
  }) async {
    final query = <String, String>{};
    if (search != null && search.trim().isNotEmpty) {
      query['search'] = search.trim();
    }
    final res = await _get(
      '/api/admin/billing/vehicles',
      query: query.isEmpty ? null : query,
      token: token,
    );
    final list = (res['data'] is List<dynamic>)
        ? (res['data'] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  static Future<Map<String, dynamic>> getBillingTrips({
    String? driverId,
    String? vehicleNo,
    String? fromDate,
    String? toDate,
    int? tripId,
    String? search,
    String? token,
  }) async {
    final query = <String, String>{};
    if (driverId != null && driverId.trim().isNotEmpty) {
      query['driver_id'] = driverId.trim();
    }
    if (vehicleNo != null && vehicleNo.trim().isNotEmpty) {
      query['vehicle_no'] = vehicleNo.trim();
    }
    if (fromDate != null && fromDate.trim().isNotEmpty) {
      query['from'] = fromDate.trim();
    }
    if (toDate != null && toDate.trim().isNotEmpty) {
      query['to'] = toDate.trim();
    }
    if (tripId != null) {
      query['trip_id'] = tripId.toString();
    }
    if (search != null && search.trim().isNotEmpty) {
      query['search'] = search.trim();
    }

    final res = await _get(
      '/api/admin/billing/trips',
      query: query.isEmpty ? null : query,
      token: token,
    );
    return (res['data'] is Map)
        ? (res['data'] as Map).cast<String, dynamic>()
        : <String, dynamic>{
            'trips': <Map<String, dynamic>>[],
            'summary': <String, dynamic>{},
          };
  }

  static Future<Map<String, dynamic>> getBillingPrefill({
    String? token,
  }) async {
    final res = await _get(
      '/api/admin/billing/prefill',
      token: token,
    );
    return (res['data'] is Map)
        ? (res['data'] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
  }

  static Future<Map<String, dynamic>> updateBillingSettings({
    required Map<String, dynamic> payload,
    String? token,
  }) async {
    final res = await _put(
      '/api/admin/billing/settings',
      body: payload,
      token: token,
    );
    return (res['data'] is Map)
        ? (res['data'] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
  }

  static Future<Map<String, dynamic>> createBillingRecord({
    required Map<String, dynamic> payload,
    String? token,
  }) async {
    final res = await _post(
      '/api/admin/billing/records',
      body: payload,
      token: token,
    );
    return (res['data'] is Map)
        ? (res['data'] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
  }

  static Future<List<Map<String, dynamic>>> getBillingRecords({
    int? limit,
    String? token,
  }) async {
    final query = <String, String>{};
    if (limit != null) {
      query['limit'] = limit.toString();
    }
    final res = await _get(
      '/api/admin/billing/records',
      query: query.isEmpty ? null : query,
      token: token,
    );
    final list = (res['data'] is List<dynamic>)
        ? (res['data'] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  // -------------- Trip Update / Cancel / Complete --------------

  /// PUT /api/admin/trips/<trip_id>
  /// Body can include:
  ///   cab_no, driver_id, add_employee_ids, remove_employee_ids, notes...
  static Future<void> updateTrip(
    int tripId, {
    String? cabNo,
    String? driverId,
    List<int>? addEmployeeIds,
    List<int>? removeEmployeeIds,
    String? notes,
    String? token,
  }) async {
    await _put(
      "/api/admin/trips/$tripId",
      token: token,
      body: {
        if (cabNo != null) "cab_no": cabNo,
        if (driverId != null) "driver_id": driverId,
        if (addEmployeeIds != null) "add_employee_ids": addEmployeeIds,
        if (removeEmployeeIds != null) "remove_employee_ids": removeEmployeeIds,
        if (notes != null) "notes": notes,
      },
    );
  }

  /// POST /api/admin/trips/<trip_id>/cancel
  static Future<void> cancelTrip(
    int tripId, {
    required String reason,
    String? token,
  }) async {
    await _post(
      "/api/admin/trips/$tripId/cancel",
      token: token,
      body: {"reason": reason},
    );
  }

  /// POST /api/v2/trips/<trip_id>/complete
  static Future<void> completeTrip(int tripId, String adminId,
      {String? token}) async {
    await _post("/api/v2/trips/$tripId/complete",
        body: {"admin_id": adminId}, token: token);
  }

  /// POST /api/v2/trips/<trip_id>/start
  static Future<Map<String, dynamic>> startTrip(int tripId,
      {String? by, String? token}) async {
    final body = <String, dynamic>{};
    if (by != null) body['by'] = by;
    final res =
        await _post("/api/v2/trips/$tripId/start", body: body, token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  /// POST /api/v2/trips/<trip_id>/complete with route summary and metadata
  static Future<Map<String, dynamic>> finishTrip(
    int tripId,
    String adminId, {
    double? totalKm,
    String? polyline,
    Map<String, dynamic>? routeJson,
    Map<String, dynamic>? tripMetadata,
    String? token,
  }) async {
    final body = <String, dynamic>{"admin_id": adminId};
    if (totalKm != null) body['total_km'] = totalKm;
    if (polyline != null) body['polyline'] = polyline;
    if (routeJson != null) body['route_json'] = routeJson;
    if (tripMetadata != null) body['trip_metadata'] = tripMetadata;

    final res =
        await _post("/api/v2/trips/$tripId/complete", body: body, token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // 15) GET /api/admin/helpdesk
  static Future<List<Map<String, dynamic>>> getHelpdeskTickets() async {
    final res = await _get("admin/helpdesk");
    final list = (res["data"] ?? res) as List;
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  // 16) POST /api/admin/helpdesk/<id>/resolve
  static Future<void> resolveHelpdeskTicket(int ticketId,
      {required String note, String? adminId}) async {
    await _post(
      "admin/helpdesk/$ticketId/resolve",
      query: adminId != null ? {"admin_id": adminId} : null,
      body: {"note": note},
    );
  }

  // 17) SOS Alerts
  /// GET /api/admin/sos-alerts
  static Future<List<Map<String, dynamic>>> getSOSAlerts(
      {String? token}) async {
    final res = await _get("/api/admin/sos-alerts", token: token);
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// POST /api/admin/sos-alerts/<id>/resolve
  static Future<void> resolveSOS(int sosId,
      {required String note, String? adminId, String? token}) async {
    await _post(
      "/api/admin/sos-alerts/$sosId/resolve",
      token: token,
      body: {
        "note": note,
        if (adminId != null) "admin_id": adminId,
      },
    );
  }

  /// POST /api/admin/trips (create new trip)
  static Future<Map<String, dynamic>> createTrip(Map<String, dynamic> tripData,
      {String? token}) async {
    final res = await _post("/api/admin/trips", body: tripData, token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // -------------- Tracking (by route) --------------

  /// GET /api/tracking/route/<route_no>/latest
  static Future<Map<String, dynamic>> getLatestTrackingByRoute(
    String routeNo, {
    String? token,
  }) async {
    final res = await _get("/api/tracking/route/$routeNo/latest", token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // -------------- Notifications --------------

  /// GET /api/notifications
  static Future<Map<String, dynamic>> getNotifications({
    required String adminId,
    int limit = 50,
    int offset = 0,
    String? token,
  }) async {
    final res = await _get(
      "/api/notifications/",
      query: {
        "admin_id": adminId,
        "limit": limit.toString(),
        "offset": offset.toString(),
      },
      token: token,
    );
    // Returns { notification: [], unread_count: 0 }
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  /// POST /api/notifications/<id>/read
  static Future<void> markNotificationRead(int notificationId, String adminId,
      {String? token}) async {
    await _post(
      "/api/notifications/$notificationId/read",
      body: {"admin_id": adminId},
      token: token,
    );
  }

  /// POST /api/notifications/read-all
  static Future<void> markAllNotificationsRead(String adminId,
      {String? token}) async {
    await _post(
      "/api/notifications/read-all",
      body: {"admin_id": adminId},
      token: token,
    );
  }

  // --- New Methods for Trip Override & Enhanced Grouping ---

  static Future<List<Map<String, dynamic>>> getAvailableDrivers({
    required String tripType,
    required String scheduledTime,
    int? vehicleType,
    Map<String, dynamic>? groupData,
    String? adminId,
    String? token,
  }) async {
    try {
      // If caller provides groupData or adminId, prefer POST (accepts complex payloads)
      if ((groupData != null && groupData.isNotEmpty) ||
          (adminId != null && adminId.isNotEmpty)) {
        final body = <String, dynamic>{
          if (groupData != null) "group_data": groupData,
          if (adminId != null) "admin_id": adminId,
          "trip_type": tripType,
          "selected_time": scheduledTime,
          if (vehicleType != null) "vehicle_type": vehicleType,
        };
        final res = await _post("/api/v2/trips/available-drivers",
            body: body, token: token);
        final list = (res["data"] is List<dynamic>)
            ? (res["data"] as List<dynamic>)
            : const <dynamic>[];
        return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
      }

      // Backwards-compatible GET behavior
      final query = {
        "trip_type": tripType,
        "scheduled_time": scheduledTime,
        if (vehicleType != null) "vehicle_type": vehicleType.toString(),
      };
      final res = await _get("/api/v2/trips/available-drivers",
          query: query, token: token);
      final List<dynamic> list = (res["data"] is List<dynamic>)
          ? (res["data"] as List<dynamic>)
          : const <dynamic>[];
      return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
    } catch (e) {
      debugPrint("getAvailableDrivers error: $e");
      return [];
    }
  }

  static Future<List<String>> getScheduledTimes({
    required String tripType,
    String? adminId,
    String? token,
  }) async {
    final query = {
      "trip_type": tripType,
      if (adminId != null && adminId.trim().isNotEmpty) "admin_id": adminId.trim(),
    };
    const paths = [
      "/api/admin/time-slots",
      "/api/v2/trips/scheduled-times",
    ];
    for (final path in paths) {
      try {
        final res = await _get(path, query: query, token: token);
        if (res["success"] == true) {
          if (res["data"] is Map && (res["data"] as Map)["slots"] is List) {
            return ((res["data"] as Map)["slots"] as List)
                .map((e) => e.toString())
                .toList();
          }
          final List<dynamic> list = (res["data"] is List<dynamic>)
              ? (res["data"] as List<dynamic>)
              : const <dynamic>[];
          return list.map((e) => e.toString()).toList();
        }
      } catch (e) {
        debugPrint("getScheduledTimes failed on $path: $e");
      }
    }
    return [];
  }

  static Future<Map<String, dynamic>> getTripById(int tripId,
      {String? token}) async {
    final res = await _get("/api/v2/trips/$tripId", token: token);
    return (res["data"] as Map?)?.cast<String, dynamic>() ?? {};
  }

  static Future<void> moveEmployee({
    required int fromTripId,
    required int employeeId,
    required int toTripId,
    required String adminId,
    String? token,
  }) async {
    await _post(
      "/api/v2/trips/$fromTripId/override/move-employee",
      token: token,
      body: {
        "admin_id": adminId,
        "employee_id": employeeId,
        "to_trip_id": toTripId.toString(),
      },
    );
  }

  static Future<void> swapDriver({
    required int tripId,
    required String newDriverId,
    required String adminId,
    String? token,
  }) async {
    await _post(
      "/api/v2/trips/$tripId/override/swap-driver",
      token: token,
      body: {
        "admin_id": adminId,
        "new_driver_id": newDriverId,
      },
    );
  }

  // --- New Request Lists for Step 7 & 9 ---

  static List<Map<String, dynamic>> _toMapList(dynamic data) {
    final list = (data is List<dynamic>) ? data : const <dynamic>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  /// GET /api/v2/drivers/go-home-requests
  static Future<List<Map<String, dynamic>>> getGoHomeRequests(
      {String? adminId, String? token}) async {
    const paths = [
      "/api/v2/drivers/go-home-requests",
      "/api/v2/trips/drivers/go-home-requests",
    ];
    for (final path in paths) {
      try {
        final res = await _get(
          path,
          token: token,
          query: {
            if (adminId != null && adminId.isNotEmpty) 'admin_id': adminId,
          },
        );
        if (res["success"] == true) {
          final list = _toMapList(res["data"]);
          return list.map((item) {
            final requestId = item["request_id"] ?? item["id"];
            return {
              ...item,
              if (requestId != null) "id": requestId,
              if (requestId != null) "request_id": requestId,
            };
          }).toList();
        }
      } catch (e) {
        debugPrint("getGoHomeRequests failed on $path: $e");
      }
    }
    return [];
  }

  /// POST /api/v2/drivers/go-home-requests/<id>/approve
  static Future<Map<String, dynamic>> approveGoHomeRequest({
    required int requestId,
    required int driverId,
    String? adminId,
    String? token,
  }) async {
    final body = <String, dynamic>{};
    if (adminId != null) body['admin_id'] = adminId;

    const paths = [
      "/api/v2/drivers/go-home-requests",
      "/api/v2/trips/drivers/go-home-requests",
    ];
    for (final base in paths) {
      try {
        final res = await _post(
          "$base/$requestId/approve",
          body: body,
          token: token,
        );
        return res.cast<String, dynamic>();
      } catch (_) {}
    }
    return {"success": false, "message": "Approve endpoint not available"};
  }

  /// POST /api/v2/drivers/go-home-requests/<id>/reject
  static Future<Map<String, dynamic>> rejectGoHomeRequest({
    required int requestId,
    required int driverId,
    String? adminId,
    String? token,
  }) async {
    final body = <String, dynamic>{};
    if (adminId != null) body['admin_id'] = adminId;

    const paths = [
      "/api/v2/drivers/go-home-requests",
      "/api/v2/trips/drivers/go-home-requests",
    ];
    for (final base in paths) {
      try {
        final res = await _post(
          "$base/$requestId/reject",
          body: body,
          token: token,
        );
        return res.cast<String, dynamic>();
      } catch (_) {}
    }
    return {"success": false, "message": "Reject endpoint not available"};
  }

  /// GET /api/v2/employees/no-trip-requests
  static Future<List<Map<String, dynamic>>> getNoTripRequests(
      {String? adminId, String? token}) async {
    const paths = [
      "/api/v2/trips/employees/no-trip-requests",
      "/api/v2/employees/no-trip-requests",
    ];
    for (final path in paths) {
      try {
        final res = await _get(
          path,
          token: token,
          query: {
            if (adminId != null && adminId.isNotEmpty) 'admin_id': adminId,
          },
        );
        if (res["success"] == true) return _toMapList(res["data"]);
      } catch (e) {
        debugPrint("getNoTripRequests failed on $path: $e");
      }
    }
    return [];
  }

  /// GET /api/v2/trips/vehicles/search/nlp
  /// NLP-powered vehicle/driver search with context
  static Future<List<Map<String, dynamic>>> searchVehiclesNLP({
    required String searchQuery,
    String? adminId,
    String? tripType,
    Map<String, dynamic>? context,
    int limit = 10,
    String? token,
  }) async {
    if (searchQuery.isEmpty) {
      return [];
    }

    try {
      final queryParams = {
        'q': searchQuery,
        if (adminId != null && adminId.isNotEmpty) 'admin_id': adminId,
        if (tripType != null && tripType.isNotEmpty) 'trip_type': tripType,
        'limit': limit.toString(),
        // New context parameters
        if (context != null && context['vehicle_types'] is List)
          'vehicle_types': (context['vehicle_types'] as List).join(','),
        if (context != null && context['scheduled_time'] != null)
          'scheduled_time': context['scheduled_time'].toString(),
        if (context != null && context['proximity_enabled'] == true)
          'proximity_enabled': 'true',
      };

      final queryString = queryParams.entries
          .map((e) =>
              '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
          .join('&');
      final url = "/api/v2/trips/vehicles/search/nlp?$queryString";

      final res = await _get(url, token: token);

      if (res["success"] == true) {
        final resultsData = res["data"];
        if (resultsData is Map && resultsData["results"] is List) {
          return (resultsData["results"] as List)
              .map((e) => (e as Map).cast<String, dynamic>())
              .toList();
        }
        return [];
      } else {
        throw ApiException(res["message"]?.toString() ?? "Search failed");
      }
    } catch (e) {
      debugPrint("NLP Search Error: $e");
      return [];
    }
  }

  /// GET /api/v2/trips/employees/search/nlp
  /// NLP-powered employee search for selected time slot
  static Future<List<Map<String, dynamic>>> searchEmployeesNLP({
    required String searchQuery,
    String? adminId,
    String? tripType,
    String? selectedTime,
    Map<String, dynamic>? context,
    int limit = 20,
    String? token,
  }) async {
    if (searchQuery.isEmpty) return [];
    try {
      final queryParams = {
        'q': searchQuery,
        if (adminId != null && adminId.isNotEmpty) 'admin_id': adminId,
        if (tripType != null && tripType.isNotEmpty) 'trip_type': tripType,
        if (selectedTime != null && selectedTime.isNotEmpty)
          'selected_time': selectedTime,
        'limit': limit.toString(),
        // New context parameters
        if (context != null && context['exclude_no_trip_users'] == true)
          'exclude_no_trip': 'true',
        if (context != null && context['exclude_on_leave'] == true)
          'exclude_on_leave': 'true',
        if (context != null && context['vehicle_types'] is List)
          'vehicle_types': (context['vehicle_types'] as List).join(','),
      };

      final queryString = queryParams.entries
          .map((e) =>
              '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
          .join('&');
      final url = "/api/v2/trips/employees/search/nlp?$queryString";

      final res = await _get(url, token: token);
      if (res["success"] == true) {
        final data = res["data"];
        if (data is Map && data["results"] is List) {
          return (data["results"] as List)
              .map((e) => (e as Map).cast<String, dynamic>())
              .toList();
        }
        return [];
      }
      return [];
    } catch (e) {
      debugPrint('searchEmployeesNLP error: $e');
      return [];
    }
  }

  /// GET /api/v2/employees/no-trip-requests (already exists)

  /// GET /api/v2/trips/assigned-employees
  static Future<List<int>> getAssignedEmployees({
    String? tripType,
    String? selectedTime,
    String? token,
  }) async {
    try {
      final queryParams = {
        if (tripType != null) 'trip_type': tripType,
        if (selectedTime != null) 'selected_time': selectedTime,
      };
      final queryString = queryParams.entries
          .map((e) =>
              '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
          .join('&');
      final urls = [
        "/api/v2/trips/assigned-employees${queryString.isNotEmpty ? '?$queryString' : ''}",
        "/api/v2/trips/trips/assigned-employees${queryString.isNotEmpty ? '?$queryString' : ''}",
      ];
      for (final url in urls) {
        try {
          final res = await _get(url, token: token);
          if (res["success"] == true && res["data"] is List) {
            return (res["data"] as List)
                .map((e) => int.tryParse(e.toString()) ?? 0)
                .where((v) => v > 0)
                .toList();
          }
        } catch (_) {}
      }
      return [];
    } catch (e) {
      debugPrint('getAssignedEmployees error: $e');
      return [];
    }
  }

  /// POST /api/v2/trips/create-groups
  static Future<Map<String, dynamic>> createGroups({
    required String adminId,
    required String tripType,
    required String selectedTime,
    required List<int> vehicleTypes,
    List<dynamic>? selectedDriverIds,
    List<int>? selectedEmployeeIds,
    bool vehiclePriorityEnabled = true,
    int? batchSize,
    String? tripDay,
    String? token,
  }) async {
    final body = {
      'admin_id': adminId,
      'trip_type': tripType,
      'selected_time': selectedTime,
      'time_slot': selectedTime,
      'vehicle_types': vehicleTypes,
      if (selectedDriverIds != null) 'driver_ids': selectedDriverIds,
      if (selectedDriverIds != null) 'selected_vehicle_ids': selectedDriverIds,
      if (selectedEmployeeIds != null) 'employee_ids': selectedEmployeeIds,
      if (selectedEmployeeIds != null)
        'selected_employee_ids': selectedEmployeeIds,
      'vehicle_priority_enabled': vehiclePriorityEnabled,
      if (batchSize != null && batchSize > 0) 'batch_size': batchSize,
      if (tripDay != null && tripDay.isNotEmpty) 'trip_day': tripDay,
    };
    const paths = [
      // Prefer persisted groups flow so View & Modify can fetch created groups.
      '/api/v2/trips/create-groups',
      '/api/v2/trips/createGroups',
      '/api/admin/groups/create',
      '/api/admin/groups/createGroups',
      // Canonical grouping flow
      '/api/grouping/create',
      '/api/grouping/createGroups',
    ];
    for (final path in paths) {
      try {
        return await _post(path, body: body, token: token);
      } on ApiException catch (e) {
        // Fail fast for mandatory hybrid provider issues (don't keep trying aliases).
        if ((e.statusCode ?? 0) == 503 ||
            e.toString().toLowerCase().contains('hybrid route provider')) {
          rethrow;
        }
        debugPrint('createGroups failed on $path: $e');
      } catch (e) {
        debugPrint('createGroups failed on $path: $e');
      }
    }
    throw ApiException('Create groups endpoint not available');
  }

  /// GET /api/health/hybrid
  static Future<Map<String, dynamic>> getHybridHealth({String? token}) async {
    final res = await _get('/api/health/hybrid', token: token);
    return (res['data'] is Map)
        ? (res['data'] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
  }

  /// GET /api/v2/trips/groups
  static Future<List<Map<String, dynamic>>> getGroups({
    required String adminId,
    String? tripType,
    String? selectedTime,
    String? tripDay,
    bool editableOnly = true,
    String? token,
  }) async {
    final query = {
      'admin_id': adminId,
      if (tripType != null && tripType.isNotEmpty) 'trip_type': tripType,
      if (selectedTime != null && selectedTime.isNotEmpty)
        'selected_time': selectedTime,
      if (tripDay != null && tripDay.isNotEmpty) 'trip_day': tripDay,
      if (editableOnly) 'editable_only': 'true',
    };

    const paths = [
      '/api/v2/trips/groups',
      '/api/v2/groups',
    ];
    try {
      for (final path in paths) {
        try {
          final res = await _get(path, query: query, token: token);
          if (res['success'] == true) return _toMapList(res['data']);
        } catch (e) {
          debugPrint('getGroups failed on $path: $e');
        }
      }
      return [];
    } catch (e) {
      debugPrint('getGroups error: $e');
      return [];
    }
  }

  /// POST /api/v2/drivers/{driver_id}/find-nearest-trip
  /// Find nearest available trip for a driver's go-home request
  static Future<Map<String, dynamic>> findNearestTripForDriver({
    required String driverId,
    required double homeLat,
    required double homeLng,
    required String tripType,
    double maxDistanceKm = 20,
    List<int>? excludeTripIds,
    String? adminId,
    String? token,
  }) async {
    final body = {
      'home_lat': homeLat,
      'home_lng': homeLng,
      'trip_type': tripType,
      'max_distance_km': maxDistanceKm,
      if (excludeTripIds != null) 'exclude_trip_ids': excludeTripIds,
      if (adminId != null) 'admin_id': adminId,
    };

    try {
      final res = await _post("/api/v2/drivers/$driverId/find-nearest-trip",
          body: body, token: token);
      return res;
    } catch (e) {
      debugPrint("findNearestTripForDriver error: $e");
      return {'success': false, 'message': e.toString()};
    }
  }

  /// POST /api/v2/drivers/{driver_id}/assign-go-home-trip
  /// Auto-assign a trip to driver from go-home request
  static Future<Map<String, dynamic>> assignGoHomeTripToDriver({
    required String driverId,
    required int goHomeRequestId,
    required int tripId,
    String? adminId,
    double? distanceFromHomeKm,
    bool overrideOriginalDriver = false,
    String? token,
  }) async {
    final body = {
      'go_home_request_id': goHomeRequestId,
      'trip_id': tripId,
      'override_original_driver': overrideOriginalDriver,
      if (adminId != null) 'admin_id': adminId,
      if (distanceFromHomeKm != null)
        'distance_from_home_km': distanceFromHomeKm,
    };

    try {
      final res = await _post("/api/v2/drivers/$driverId/assign-go-home-trip",
          body: body, token: token);
      return res;
    } catch (e) {
      debugPrint("assignGoHomeTripToDriver error: $e");
      return {'success': false, 'message': e.toString()};
    }
  }

  /// GET /api/v2/trips/available-vehicles
  /// Get all available vehicles for group creation
  static Future<List<Map<String, dynamic>>> getAvailableVehicles({
    required String adminId,
    String? tripType,
    String? scheduledTime,
    String? vehicleTypes,
    String? date,
    bool excludeAssigned = false,
    String? token,
  }) async {
    String? singleVehicleType;
    if (vehicleTypes != null && vehicleTypes.trim().isNotEmpty) {
      final normalized = vehicleTypes.toLowerCase().trim();
      if (normalized == '4' || normalized == '6' || normalized == 'both') {
        singleVehicleType = normalized;
      } else if (normalized.contains(',') ||
          normalized.contains(' ') ||
          normalized.contains(';')) {
        final has4 = normalized.contains('4');
        final has6 = normalized.contains('6');
        if (has4 && has6) {
          singleVehicleType = 'both';
        } else if (has6) {
          singleVehicleType = '6';
        } else if (has4) {
          singleVehicleType = '4';
        }
      }
    }

    final query = {
      'admin_id': adminId,
      if (tripType != null && tripType.isNotEmpty) 'trip_type': tripType,
      if (scheduledTime != null && scheduledTime.isNotEmpty)
        'time_slot': scheduledTime,
      if (scheduledTime != null && scheduledTime.isNotEmpty)
        'scheduled_time': scheduledTime,
      if (scheduledTime != null && scheduledTime.isNotEmpty)
        'selected_time': scheduledTime,
      if (singleVehicleType != null) 'vehicle_type': singleVehicleType,
      if (vehicleTypes != null && vehicleTypes.isNotEmpty)
        'vehicle_types': vehicleTypes,
      if (date != null && date.isNotEmpty) 'trip_day': date,
      if (excludeAssigned) 'exclude_assigned': 'true',
    };

    const paths = [
      '/api/admin/available-vehicles',
      '/api/v2/trips/available-vehicles',
    ];
    for (final path in paths) {
      try {
        final res = await _get(path, query: query, token: token);
        if (res['success'] != true) continue;
        if (res['data'] is List) {
          return (res['data'] as List)
              .map((e) =>
                  _normalizeVehicleRecord((e as Map).cast<String, dynamic>()))
              .toList();
        }
        if (res['data'] is Map) {
          final data = (res['data'] as Map).cast<String, dynamic>();
          final rawVehicles = (data['vehicles'] is List)
              ? (data['vehicles'] as List)
              : <dynamic>[];
          final transformed = <Map<String, dynamic>>[];
          for (final item in rawVehicles) {
            if (item is! Map) continue;
            final vehicle = item.cast<String, dynamic>();
            final driver = vehicle['driver'];
            final rawId = vehicle['driver_id'] ??
                (driver is Map ? driver['driver_id'] : null) ??
                vehicle['id'];
            if (rawId == null) continue;
            final rawIdStr = rawId.toString().trim();
            if (rawIdStr.isEmpty) continue;
            final did = _asIntLocal(rawIdStr) ?? _stablePositiveId(rawIdStr);
            transformed.add({
              'driver_id': did,
              'id': did,
              'driver_id_raw': rawIdStr,
              'driver_name': (driver is Map
                      ? (driver['name'] ?? vehicle['driver_name'])
                      : vehicle['driver_name']) ??
                  'Unknown',
              'name': (driver is Map
                      ? (driver['name'] ?? vehicle['driver_name'])
                      : vehicle['driver_name']) ??
                  'Unknown',
              'mobile': (driver is Map
                      ? (driver['phone'] ?? vehicle['mobile'])
                      : vehicle['mobile']) ??
                  '',
              'cab_no': vehicle['vehicle_no'] ?? vehicle['cab_no'] ?? '',
              'vehicle_no': vehicle['vehicle_no'] ?? '',
              'vehicle_id': vehicle['vehicle_id'],
              'vehicle_type': vehicle['vehicle_type'],
              'status': 'available',
              'is_available': vehicle['is_available'] ?? true,
              'go_home_request': vehicle['go_home_request'] == true,
            });
          }
          return transformed;
        }
      } catch (e) {
        debugPrint("getAvailableVehicles failed on $path: $e");
      }
    }
    return [];
  }

  static Future<List<Map<String, dynamic>>> getAvailableEmployees({
    String? adminId,
    required String tripType,
    required String timeSlot,
    String? tripDay,
    String? token,
  }) async {
    final query = {
      if (adminId != null && adminId.isNotEmpty) 'admin_id': adminId,
      'trip_type': tripType,
      'time_slot': timeSlot,
      'selected_time': timeSlot,
      if (tripDay != null && tripDay.isNotEmpty) 'trip_day': tripDay,
    };
    const paths = [
      '/api/admin/available-employees',
      '/api/v2/trips/available-employees',
    ];

    for (final path in paths) {
      try {
        final res = await _get(path, query: query, token: token);
        if (res['success'] != true) continue;
        if (res['data'] is List) {
          return (res['data'] as List)
              .map((e) => (e as Map).cast<String, dynamic>())
              .toList();
        }
        if (res['data'] is Map) {
          final data = (res['data'] as Map).cast<String, dynamic>();
          final list = (data['employees'] is List)
              ? (data['employees'] as List)
              : <dynamic>[];
          return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
        }
      } catch (e) {
        debugPrint("getAvailableEmployees failed on $path: $e");
      }
    }
    return [];
  }

  static int? _asIntLocal(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    final s = v.toString().trim();
    return int.tryParse(s);
  }

  static int _stablePositiveId(String s) {
    // Deterministic non-zero integer surrogate for string driver IDs.
    var hash = 2166136261;
    for (final u in s.codeUnits) {
      hash ^= u;
      hash = (hash * 16777619) & 0x7fffffff;
    }
    return hash == 0 ? 1 : hash;
  }

  static Map<String, dynamic> _normalizeVehicleRecord(
      Map<String, dynamic> item) {
    final driver = item['driver'];
    final rawId = item['driver_id'] ??
        item['id'] ??
        (driver is Map ? driver['driver_id'] : null);
    if (rawId == null) return item;
    final rawIdStr = rawId.toString().trim();
    if (rawIdStr.isEmpty) return item;
    return {
      ...item,
      'driver_id': _asIntLocal(rawIdStr) ?? _stablePositiveId(rawIdStr),
      'id': _asIntLocal(rawIdStr) ?? _stablePositiveId(rawIdStr),
      'driver_id_raw': rawIdStr,
    };
  }

  /// POST /api/v2/trips/groups/{group_id}/remove-employee
  static Future<bool> removeEmployeeFromGroup({
    required int groupId,
    required int employeeId,
    String? token,
  }) async {
    try {
      final res = await _post('/api/v2/trips/groups/$groupId/remove-employee',
          body: {'employee_id': employeeId}, token: token);
      return res['success'] == true;
    } catch (e) {
      debugPrint('removeEmployeeFromGroup error: $e');
      return false;
    }
  }

  /// POST /api/v2/trips/groups/{group_id}/add-employee
  static Future<bool> addEmployeeToGroup({
    required int groupId,
    required int employeeId,
    String? token,
  }) async {
    try {
      final res = await _post('/api/v2/trips/groups/$groupId/add-employee',
          body: {'employee_id': employeeId}, token: token);
      return res['success'] == true;
    } catch (e) {
      debugPrint('addEmployeeToGroup error: $e');
      return false;
    }
  }

  /// POST /api/v2/trips/groups/{group_id}/change-vehicle
  static Future<Map<String, dynamic>> changeGroupVehicle({
    required int groupId,
    required int vehicleType,
    String? tripType,
    String? selectedTime,
    String? tripDay,
    String? token,
  }) async {
    try {
      final res = await _post('/api/v2/trips/groups/$groupId/change-vehicle',
          body: {
            'vehicle_type': vehicleType,
            if (tripType != null && tripType.isNotEmpty) 'trip_type': tripType,
            if (selectedTime != null && selectedTime.isNotEmpty)
              'selected_time': selectedTime,
            if (tripDay != null && tripDay.isNotEmpty) 'trip_day': tripDay,
          },
          token: token);
      return {
        'success': res['success'] == true,
        'message': (res['message'] ?? '').toString(),
        'data': res['data'],
      };
    } catch (e) {
      debugPrint('changeGroupVehicle error: $e');
      return {
        'success': false,
        'message': e.toString(),
      };
    }
  }

  /// DELETE /api/v2/trips/groups/{group_id}
  /// Fallback POST /api/v2/trips/groups/{group_id}/delete
  static Future<bool> deleteGroup({
    required int groupId,
    String? token,
  }) async {
    try {
      final res = await _delete('/api/v2/trips/groups/$groupId', token: token);
      return res['success'] == true;
    } catch (e) {
      debugPrint('deleteGroup DELETE error: $e');
      try {
        final res = await _post('/api/v2/trips/groups/$groupId/delete',
            body: {}, token: token);
        return res['success'] == true;
      } catch (e2) {
        debugPrint('deleteGroup POST fallback error: $e2');
        return false;
      }
    }
  }

  /// POST /api/v2/trips/groups/swap-employees
  static Future<bool> swapEmployees({
    required int groupA,
    required int employeeA,
    required int groupB,
    required int employeeB,
    String? token,
  }) async {
    try {
      final res = await _post('/api/v2/trips/groups/swap-employees',
          body: {
            'group_a': groupA,
            'employee_a': employeeA,
            'group_b': groupB,
            'employee_b': employeeB,
          },
          token: token);
      return res['success'] == true;
    } catch (e) {
      debugPrint('swapEmployees error: $e');
      return false;
    }
  }
}
