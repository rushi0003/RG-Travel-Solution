import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/config/env.dart';
import '../core/storage/session_store.dart';
import '../models/driver_model.dart';
import '../models/driver_request.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? code;
  final Map<String, dynamic>? data;
  ApiException(this.message, {this.statusCode, this.code, this.data});

  @override
  String toString() {
    final codePart = (code != null && code!.isNotEmpty) ? "[$code] " : "";
    return statusCode == null
        ? "$codePart$message"
        : "($statusCode) $codePart$message";
  }
}

class DriverService {
  DriverService._();

  static final DriverService instance = DriverService._();

  // Mutable to allow runtime updates from Dashboard
  static String _baseUrl = Env.baseUrl;

  static String get baseUrl => _baseUrl;

  static void setBaseUrl(String url) {
    if (url.trim().isNotEmpty) {
      _baseUrl = url.trim();
    }
  }

  static Uri _u(String path, [Map<String, String>? query]) {
    final p = path.startsWith("/") ? path : "/$path";
    // Replicate Env.apiBase logic: base + /api + path
    // But check if path already has /api (some legacy might)
    // Actually, Env.apiBase is "$baseUrl$apiPrefix".
    // Let's assume the service methods pass paths relative to "api/" or root?
    // Looking at methods: "admin/driver-requests", "driver/$id/profile"
    // These look like they need /api prefix.

    final fullUrl = "$_baseUrl${Env.apiPrefix}$p";
    final uriObj = Uri.parse(fullUrl);
    return query == null ? uriObj : uriObj.replace(queryParameters: query);
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
      // If void response or error, handled below
      if (r.body.isEmpty && r.statusCode < 300) return {};
      decoded = {"success": false, "message": "Invalid JSON from server"};
    }

    if (r.statusCode >= 400) {
      final payload = (decoded is Map)
          ? decoded.cast<String, dynamic>()
          : <String, dynamic>{};
      final errorMap = (payload["error"] is Map)
          ? (payload["error"] as Map).cast<String, dynamic>()
          : null;
      final msg = (payload["message"] != null)
          ? payload["message"].toString()
          : (errorMap?["message"]?.toString() ?? "HTTP ${r.statusCode}");
      final payloadData = (payload["data"] is Map)
          ? (payload["data"] as Map).cast<String, dynamic>()
          : null;
      final code = payload["code"]?.toString() ??
          payload["error_code"]?.toString() ??
          errorMap?["code"]?.toString() ??
          payloadData?["error_code"]?.toString();
      throw ApiException(
        msg,
        statusCode: r.statusCode,
        code: code,
        data: payload.isEmpty ? null : payload,
      );
    }

    if (decoded is List) return {"data": decoded}; // Wrap list
    if (decoded is Map<String, dynamic>) return decoded;
    return {}; // fallback
  }

  static Future<Map<String, dynamic>> _get(String path,
      {Map<String, String>? query, String? token}) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.get(
      _u(path, query),
      headers: _headers(token: effectiveToken),
    );
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _post(String path,
      {Map<String, String>? query, Map<String, dynamic>? body, String? token}) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.post(
      _u(path, query),
      headers: _headers(token: effectiveToken),
      body: jsonEncode(body ?? {}),
    );
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _put(String path,
      {Map<String, dynamic>? body, String? token}) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.put(
      _u(path),
      headers: _headers(token: effectiveToken),
      body: jsonEncode(body ?? {}),
    );
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _delete(String path,
      {String? token}) async {
    final effectiveToken = token ?? await SessionStore.getToken();
    final r = await http.delete(
      _u(path),
      headers: _headers(token: effectiveToken),
    );
    return _handle(r);
  }

  static Map<String, dynamic> _normalizeTripPayload(Map<String, dynamic> trip) {
    final normalized = <String, dynamic>{...trip};

    if (normalized["id"] == null && normalized["trip_id"] != null) {
      normalized["id"] = normalized["trip_id"];
    }
    if (normalized["scheduled_time"] == null &&
        normalized["schedule_time"] != null) {
      normalized["scheduled_time"] = normalized["schedule_time"];
    }

    final employeesRaw = normalized["employees"];
    final passengersRaw = normalized["passengers"];
    if (employeesRaw is! List && passengersRaw is List) {
      normalized["employees"] = passengersRaw;
    }
    if (passengersRaw is! List && employeesRaw is List) {
      normalized["passengers"] = employeesRaw;
    }

    return normalized;
  }

  // ===========================================================================
  // NEW ADMIN METHODS (For DriversScreen)
  // ===========================================================================

  // 1) GET /api/admin/driver-requests
  Future<List<DriverRequest>> getPendingRequests() async {
    try {
      final res = await _get("admin/driver-requests");
      // Res might be { data: [...] } or just [...] wrapped by _handle
      final list = (res["data"] ?? res) as List;
      return list
          .map((e) => DriverRequest.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      rethrow;
    }
  }

  // 2) POST /api/admin/driver-requests/{id}/approve
  Future<void> approveRequest(String id) async {
    await _post("admin/driver-requests/$id/approve");
  }

  // 3) POST /api/admin/driver-requests/{id}/reject
  Future<void> rejectRequest(String id, {String? reason}) async {
    await _post("admin/driver-requests/$id/reject", body: {
      if (reason != null && reason.isNotEmpty) "reason": reason,
    });
  }

  // 4) POST /api/admin/drivers
  Future<void> createDriver(DriverModel driver) async {
    // Send specific fields with correct keys matching backend
    await _post("admin/drivers", body: {
      'name': driver.name,
      'mobile': driver.mobile,
      'dl_no': driver.licenseNo, // Backend expects dl_no
      'cab_no':
          driver.vehicleNo, // Backend expects cab_no (maps to vehicle_no in DB)
      'home_town': driver.hometownAddress, // Backend expects home_town
      'hometown': driver.hometownAddress,
      'home_address': driver.hometownAddress,
      'vehicle_type': driver.vehicleType, // Backend supports and expects this
      if (driver.homeLat != null) 'home_lat': driver.homeLat,
      if (driver.homeLng != null) 'home_lng': driver.homeLng,
      if (driver.homeLat != null) 'hometown_lat': driver.homeLat,
      if (driver.homeLng != null) 'hometown_lng': driver.homeLng,
      if (driver.homeLat != null) 'lat': driver.homeLat,
      if (driver.homeLng != null) 'lng': driver.homeLng,
    });
  }

  // 5) GET /api/admin/drivers
  Future<List<DriverModel>> getAllDrivers() async {
    final res = await _get("admin/drivers");
    final list = (res["data"] ?? res) as List;
    return list
        .map((e) => DriverModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // 6) PUT /api/admin/drivers/{id}
  Future<void> updateDriver(String id, DriverModel driver) async {
    await _put("admin/drivers/$id", body: {
      'name': driver.name,
      'mobile': driver.mobile,
      'dl_no': driver.licenseNo, // Backend expects dl_no
      'cab_no': driver.vehicleNo, // Backend expects cab_no
      'home_town': driver.hometownAddress, // Backend expects home_town
      'hometown': driver.hometownAddress,
      'home_address': driver.hometownAddress,
      'vehicle_type': driver.vehicleType, // Backend expects vehicle_type
      if (driver.homeLat != null) 'home_lat': driver.homeLat,
      if (driver.homeLng != null) 'home_lng': driver.homeLng,
      if (driver.homeLat != null) 'hometown_lat': driver.homeLat,
      if (driver.homeLng != null) 'hometown_lng': driver.homeLng,
      if (driver.homeLat != null) 'lat': driver.homeLat,
      if (driver.homeLng != null) 'lng': driver.homeLng,
    });
  }

  // 7) DELETE /api/admin/drivers/{id}
  Future<void> deleteDriver(String id) async {
    await _delete("admin/drivers/$id");
  }

  // 8) GET /api/admin/drivers/search?query={query}
  Future<List<DriverModel>> searchDrivers(String query) async {
    final res = await _get("admin/drivers/search", query: {"query": query});
    final list = (res["data"] ?? res) as List;
    return list
        .map((e) => DriverModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // 9) GET /api/admin/driver-change-requests
  Future<List<Map<String, dynamic>>> getDriverChangeRequests() async {
    final res = await _get("admin/driver-change-requests");
    final list = (res["data"] ?? res) as List;
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  // 10) POST /api/admin/driver-change-requests/{id}/approve
  Future<void> approveDriverChange(int id) async {
    await _post("admin/driver-change-requests/$id/approve");
  }

  // 11) POST /api/admin/driver-change-requests/{id}/reject
  Future<void> rejectDriverChange(int id) async {
    await _post("admin/driver-change-requests/$id/reject");
  }

  // 12) GET /api/admin/swap-requests
  Future<List<Map<String, dynamic>>> getSwapRequests() async {
    final res = await _get("admin/swap-requests");
    final list = (res["data"] ?? res) as List;
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  // 13) POST /api/admin/swap-requests/{id}/approve
  Future<void> approveSwap(int id) async {
    await _post("admin/swap-requests/$id/approve");
  }

  // 14) POST /api/admin/swap-requests/{id}/reject
  Future<void> rejectSwap(int id) async {
    await _post("admin/swap-requests/$id/reject");
  }

  // ===========================================================================
  // LEGACY METHODS (Restored for compatibility)
  // ===========================================================================

  static Future<Map<String, dynamic>> getDriverProfile(String driverId,
      {String? token, String? adminId}) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    final query = <String, String>{
      if (selectedAdminId != null && selectedAdminId.isNotEmpty)
        'admin_id': selectedAdminId,
    };
    final profilePaths = <String>[
      // Current driver blueprint
      "driver/profile/$driverId",
      // Legacy variants
      "driver/$driverId/profile",
      "driver/$driverId",
    ];

    Map<String, dynamic>? res;
    ApiException? lastError;
    for (final path in profilePaths) {
      try {
        res = await _get(path, token: token, query: query.isEmpty ? null : query);
        break;
      } on ApiException catch (e) {
        lastError = e;
      }
    }

    if (res == null) {
      // Final fallback: derive drawer profile from assigned-trip payload.
      final trip = await getAssignedTrip(driverId, token: token);
      if (trip != null && trip.isNotEmpty) {
        return <String, dynamic>{
          "name": (trip["driver_name"] ?? "Driver").toString(),
          "mobile": (trip["driver_mobile"] ?? "").toString(),
          "cab_no": (trip["cab_no"] ?? trip["vehicle_no"] ?? "").toString(),
          "hometown": (trip["hometown"] ?? trip["home_town"] ?? "").toString(),
        };
      }
      if (lastError != null) throw lastError;
      return <String, dynamic>{};
    }

    final profileData = res["data"];
    final raw = (profileData is Map)
        ? profileData.cast<String, dynamic>()
        : <String, dynamic>{};
    if (raw.isEmpty) return raw;

    return <String, dynamic>{
      ...raw,
      "cab_no": raw["cab_no"] ?? raw["vehicle_no"] ?? raw["cabNo"],
      "hometown": raw["hometown"] ?? raw["home_town"] ?? raw["homeTown"],
      "home_address": raw["home_address"] ?? raw["hometown"] ?? raw["home_town"] ?? raw["homeTown"],
    };
  }

  static Future<Map<String, dynamic>> updateDriverProfile(
    String driverId, {
    required String name,
    required String mobile,
    required String dlNo,
    required String cabNo,
    required int vehicleType,
    required String homeTown,
    String? token,
  }) async {
    final payload = {
      "name": name,
      "mobile": mobile,
      "dl_no": dlNo,
      "cab_no": cabNo,
      "vehicle_type": vehicleType,
      "hometown": homeTown,
    };

    Map<String, dynamic> res;
    try {
      res = await _put("driver/profile/$driverId", token: token, body: payload);
    } on ApiException catch (e) {
      if (e.statusCode != 404) rethrow;
      res = await _put("driver/$driverId/profile", token: token, body: {
        ...payload,
        "home_town": homeTown,
      });
    }
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  static Future<void> requestProfileChange(
    String driverId, {
    String? name,
    String? mobile,
    String? dlNo,
    String? cabNo,
    int? vehicleType,
    String? homeTown,
    double? homeLat,
    double? homeLng,
    String? token,
  }) async {
    final payload = {
      if (name != null) "name": name,
      if (mobile != null) "mobile": mobile,
      if (dlNo != null) "dl_no": dlNo,
      if (cabNo != null) "cab_no": cabNo,
      if (vehicleType != null) "vehicle_type": vehicleType,
      if (homeTown != null) "hometown": homeTown,
      if (homeLat != null) "home_lat": homeLat,
      if (homeLng != null) "home_lng": homeLng,
    };

    try {
      await _post(
        "driver/profile/$driverId/change-request",
        token: token,
        body: payload,
      );
    } on ApiException catch (e) {
      if (e.statusCode != 404) rethrow;
      await _post(
        "driver/$driverId/profile-change-request",
        token: token,
        body: {
          ...payload,
          if (homeTown != null) "home_town": homeTown,
          if (homeLat != null) "home_lat": homeLat,
          if (homeLng != null) "home_lng": homeLng,
        },
      );
    }
  }

  // 14) Hometown Change (Step 15)
  static Future<void> requestHometownChange(
    String driverId, {
    required String newHometown,
    String? token,
  }) async {
    final cleanTown = newHometown.trim();
    if (cleanTown.isEmpty) {
      throw ApiException("Hometown is required");
    }

    final attempts = <Map<String, dynamic>>[
      {
        "path": "driver/$driverId/hometown-request",
        "body": {"home_town": cleanTown, "home_address": cleanTown},
      },
      {
        "path": "driver/$driverId/hometown_request",
        "body": {"requested_home_town": cleanTown, "home_address": cleanTown},
      },
      {
        "path": "driver/profile/$driverId/change-request",
        "body": {"hometown": cleanTown},
      },
    ];

    ApiException? lastApiError;
    Object? lastError;
    for (final attempt in attempts) {
      try {
        await _post(
          attempt["path"].toString(),
          token: token,
          body: (attempt["body"] as Map<String, dynamic>),
        );
        return;
      } on ApiException catch (e) {
        lastApiError = e;
        if (e.statusCode != 404) {
          continue;
        }
      } catch (e) {
        lastError = e;
      }
    }

    if (lastApiError != null) throw lastApiError;
    if (lastError != null) throw ApiException(lastError.toString());
    throw ApiException("Hometown request endpoint not available");
  }

  // 15) Emergency Swap (Step 15)
  static Future<void> requestEmergencySwap(
    String driverId, {
    required int tripId,
    required String reason,
    String? photoBase64,
    String? newDriverName,
    String? newDriverMobile,
    String? newCabNo,
    String? token,
  }) async {
    // Backward-compatible wrapper for old callers.
    // Canonical backend API: /api/driver/<driver_id>/trip/<trip_id>/swap-request
    await createSwapRequest(
      driverId,
      tripId: tripId,
      reason: reason,
      newDriverName: newDriverName ?? "",
      newDriverMobile: newDriverMobile ?? "",
      newCabNo: newCabNo ?? "",
      photoBase64: photoBase64,
      token: token,
    );
  }

  // GET /api/driver/<id>/my-trips
  static Future<List<Map<String, dynamic>>> getMyTrips(String driverId,
      {String? token, String? adminId}) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    final query = <String, String>{
      if (selectedAdminId != null && selectedAdminId.isNotEmpty)
        'admin_id': selectedAdminId,
    };
    final res = await _get(
      "driver/$driverId/my-trips",
      token: token,
      query: query.isEmpty ? null : query,
    );
    final data = res["data"];
    if (data is Map && data["trips"] is List) {
      return (data["trips"] as List)
          .whereType<Map<dynamic, dynamic>>()
          .map((e) => _normalizeTripPayload(e.cast<String, dynamic>()))
          .toList();
    }
    return [];
  }

  static Future<Map<String, dynamic>?> getAssignedTrip(String driverId,
      {String? token, String? adminId}) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    final query = <String, String>{
      if (selectedAdminId != null && selectedAdminId.isNotEmpty)
        'admin_id': selectedAdminId,
    };
    final res = await _get(
      "driver/$driverId/assigned-trip",
      token: token,
      query: query.isEmpty ? null : query,
    );
    if (res["success"] == false) return null;
    return (res["data"] is Map)
        ? _normalizeTripPayload((res["data"] as Map).cast<String, dynamic>())
        : null;
  }

  static Future<Map<String, dynamic>> getDriverCompanies(
    String driverId, {
    String? token,
  }) async {
    final res = await _get("driver/$driverId/companies", token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
  }

  static Future<Map<String, dynamic>> switchDriverCompany(
    String driverId, {
    required String adminId,
    String? token,
  }) async {
    final res = await _post(
      "driver/$driverId/switch-company",
      token: token,
      body: {'admin_id': adminId},
    );
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
  }

  static Future<Map<String, dynamic>?> getHometownRequestStatus(
    String driverId, {
    String? token,
  }) async {
    final paths = [
      "driver/$driverId/hometown-request-status",
      "driver/$driverId/hometown_request_status",
    ];
    for (final path in paths) {
      try {
        final res = await _get(path, token: token);
        if (res["success"] == true) {
          final data = res["data"];
          if (data is Map) return data.cast<String, dynamic>();
          return null;
        }
      } on ApiException catch (e) {
        if (e.statusCode != 404) rethrow;
      }
    }
    return null;
  }

  static Future<void> markNoShow(
    String driverId, {
    required int tripId,
    required int employeeId,
    String? adminId,
    String? token,
  }) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    await _post(
      "driver/$driverId/trip/$tripId/no-show",
      token: token,
      query: {
        if (selectedAdminId != null && selectedAdminId.isNotEmpty)
          "admin_id": selectedAdminId,
      },
      body: {
        "employee_id": employeeId,
      },
    );
  }

  static Future<void> verifyTripOtp(
    int tripId, {
    required String type,
    required String otp,
    required String driverId,
    int? employeeId,
    String? adminId,
    String? token,
  }) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    await _post(
      "driver/$driverId/trip/$tripId/otp/verify",
      token: token,
      query: {
        if (selectedAdminId != null && selectedAdminId.isNotEmpty)
          "admin_id": selectedAdminId,
      },
      body: {
        "otp_type": type,
        "otp": otp,
        if (employeeId != null) "employee_id": employeeId,
      },
    );
  }

  static Future<void> startTrip(int tripId,
      {required String driverId, String? adminId, String? token}) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    await _post(
      "driver/$driverId/trip/$tripId/start",
      token: token,
      query: {
        if (selectedAdminId != null && selectedAdminId.isNotEmpty)
          "admin_id": selectedAdminId,
      },
    );
  }

  static Future<void> completeTrip(int tripId,
      {required String driverId, String? adminId, String? token}) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    await _post(
      "driver/$driverId/trip/$tripId/complete",
      token: token,
      query: {
        if (selectedAdminId != null && selectedAdminId.isNotEmpty)
          "admin_id": selectedAdminId,
      },
    );
  }

  static Future<void> sendGpsUpdate(
    String driverId, {
    required String routeNo,
    required double lat,
    required double lng,
    String? token,
  }) async {
    await _post(
      "driver/$driverId/gps",
      token: token,
      body: {
        "route_no": routeNo,
        "lat": lat,
        "lng": lng,
      },
    );
  }

  static Future<void> createSwapRequest(
    String driverId, {
    required int tripId,
    required String reason,
    required String newDriverName,
    required String newDriverMobile,
    required String newCabNo,
    String? photoBase64,
    String? adminId,
    String? token,
  }) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    await _post(
      "driver/$driverId/trip/$tripId/swap-request",
      token: token,
      query: {
        if (selectedAdminId != null && selectedAdminId.isNotEmpty)
          "admin_id": selectedAdminId,
      },
      body: {
        "reason": reason,
        "new_driver_name": newDriverName,
        "new_driver_mobile": newDriverMobile,
        "new_cab_no": newCabNo,
        "photo_base64": photoBase64,
      },
    );
  }

  static Future<void> createTripCancelRequest(
    String driverId, {
    required int tripId,
    required String reason,
    String? adminId,
    String? token,
  }) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    await _post(
      "driver/$driverId/trip/$tripId/cancel-request",
      token: token,
      query: {
        if (selectedAdminId != null && selectedAdminId.isNotEmpty)
          "admin_id": selectedAdminId,
      },
      body: {
        "reason": reason,
      },
    );
  }

  static Future<List<Map<String, dynamic>>> getDriverTripHistory(
    String driverId, {
    String? fromDate,
    String? toDate,
    String? q,
    String? adminId,
    String? token,
  }) async {
    final selectedAdminId = adminId ?? await SessionStore.getSelectedAdminId();
    final query = <String, String>{};
    if (fromDate != null && fromDate.trim().isNotEmpty)
      query["from"] = fromDate.trim();
    if (toDate != null && toDate.trim().isNotEmpty) query["to"] = toDate.trim();
    if (q != null && q.trim().isNotEmpty) query["q"] = q.trim();
    if (selectedAdminId != null && selectedAdminId.isNotEmpty) {
      query["admin_id"] = selectedAdminId;
    }

    final res = await _get("driver/$driverId/trip-history",
        token: token, query: query.isEmpty ? null : query);
    final list = (res["data"] is List)
        ? (res["data"] as List).cast<Map<String, dynamic>>()
        : <Map<String, dynamic>>[];
    return list.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  static Future<Map<String, dynamic>> getTripDetailsByRoute(String routeNo,
      {String? token}) async {
    final res = await _get("trip/$routeNo", token: token);
    return (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : {};
  }

  // 14) POST /api/driver/{id}/helpdesk
  static Future<void> createHelpdeskTicket(
    String driverId, {
    required String subject,
    required String message,
    String priority = "normal",
    String? token,
  }) async {
    await _post(
      "driver/$driverId/helpdesk",
      token: token,
      body: {
        "subject": subject,
        "message": message,
        "priority": priority,
      },
    );
  }

  static Future<bool> checkHealth() async {
    try {
      final res = await _get("health");
      return res["status"] == "ok";
    } catch (_) {
      return false;
    }
  }
}
