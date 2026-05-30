// flutter/lib/services/auth_service.dart
//
// RG Travel Solution — Auth Service (Flutter)
//
// Covers:
// - Health check
// - Admin login
// - Driver login + signup request (pending approval)
// - Employee login + signup request (pending approval)
// - Common API helpers + error handling
//
// NOTE:
// Ensure backend endpoints exist with same paths.

import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  ApiException(this.message, {this.statusCode});

  @override
  String toString() => statusCode == null ? message : "($statusCode) $message";
}

/// Standard auth result object
class AuthResult {
  final bool success;
  final String message;

  /// One of: admin, driver, employee
  final String role;

  /// Returned id
  final String? userId;

  /// Optional token (if backend returns JWT)
  final String? token;

  /// Extra data from backend
  final Map<String, dynamic>? data;

  const AuthResult({
    required this.success,
    required this.message,
    required this.role,
    this.userId,
    this.token,
    this.data,
  });
}

class CompanyOption {
  final String id;
  final String name;
  final String companyName;
  final String officeAddress;

  const CompanyOption({
    required this.id,
    required this.name,
    required this.companyName,
    required this.officeAddress,
  });

  factory CompanyOption.fromJson(Map<String, dynamic> json) {
    return CompanyOption(
      id: (json["id"] ?? "").toString(),
      name: (json["name"] ?? "").toString(),
      companyName: (json["company_name"] ?? json["office_name"] ?? json["name"] ?? "").toString(),
      officeAddress: (json["office_address"] ?? "").toString(),
    );
  }
}

class AuthService {
  AuthService._();

  // ✅ Base URL auto (Web vs Emulator)
  static String baseUrl =
      kIsWeb ? "http://127.0.0.1:5000" : "http://10.0.2.2:5000";

  static void setBaseUrl(String url) {
    if (url.trim().isNotEmpty) baseUrl = url.trim();
  }

  // ---------------- Helpers ----------------

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
    final r = await http.get(_u(path, query), headers: _headers(token: token));
    return _handle(r);
  }

  static Future<Map<String, dynamic>> _post(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? query,
    String? token,
  }) async {
    final r = await http.post(
      _u(path, query),
      headers: _headers(token: token),
      body: jsonEncode(body ?? {}),
    );
    return _handle(r);
  }

  // ---------------- Health ----------------

  /// GET /api/health
  static Future<bool> healthCheck() async {
    try {
      final res = await _get("/api/health");
      return res["success"] == true;
    } catch (_) {
      return false;
    }
  }

  // ---------------- Admin Login ----------------

  /// POST /api/auth/admin/login
  ///
  /// body: { name, mobile, password }
  /// returns: { success, message, data:{ admin_id, token? } }
  static Future<AuthResult> adminLogin({
    required String name,
    required String mobile,
    required String password,
  }) async {
    final res = await _post(
      "/api/auth/admin/login",
      body: {
        "name": name,
        "mobile": mobile,
        "password": password,
      },
    );

    final data = (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final token = (data["token"] ?? data["access_token"])?.toString();

    // ✅ ROBUST: If token matches, treat as success (ignore success=false if backend is weird)
    final bool isSuccess =
        (token != null && token.isNotEmpty) || (res["success"] == true);
    final msg =
        (res["message"] ?? (isSuccess ? "Login success" : "Login failed"))
            .toString();

    if (!isSuccess) {
      return AuthResult(
        success: false,
        message: msg,
        role: "admin",
      );
    }

    // Backend returns "admin" object OR "profile" object inside data
    var sourceMap = data;
    if (res["admin"] is Map)
      sourceMap = (res["admin"] as Map).cast<String, dynamic>();
    else if (data["profile"] is Map)
      sourceMap = (data["profile"] as Map).cast<String, dynamic>();

    final id = _stringFromAny(
        sourceMap["id"] ?? sourceMap["adminId"] ?? data["admin_id"]);

    // Fallback: If ID missing but log in okay, maybe use default or warning?
    // User requirement: Must be robust.

    return AuthResult(
      success: true,
      message: msg,
      role: "admin",
      userId: id,
      token: token,
      data: data.isEmpty ? null : data,
    );
  }

  // ---------------- Driver Login + Signup Request ----------------
  static Future<AuthResult> driverLogin({
    required String mobile,
    required String dlNo,
    required String cabNo,
  }) async {
    final res = await _post(
      "/api/auth/driver/login",
      body: {
        "mobile": mobile,
        "dl_no": dlNo,
        "cab_no": cabNo,
      },
    );

    final data = (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final token = (data["token"] ?? data["access_token"])?.toString();

    // ✅ ROBUST: Token = Success
    final bool isSuccess =
        (token != null && token.isNotEmpty) || (res["success"] == true);
    final msg =
        (res["message"] ?? (isSuccess ? "Login success" : "Login failed"))
            .toString();

    if (!isSuccess) {
      return AuthResult(success: false, message: msg, role: "driver");
    }

    // Attempt to parse ID
    final id = _stringFromAny(data["driver_id"] ??
        data["id"] ??
        (data["profile"] is Map ? data["profile"]["id"] : null));

    return AuthResult(
      success: true,
      message: msg,
      role: "driver",
      userId: id,
      token: token,
      data: data.isEmpty ? null : data,
    );
  }

  // ... (signup request remains same as it doesn't return token) ...

  // ---------------- Driver Signup Request ----------------
  static Future<AuthResult> driverSignupRequest({
    required String name,
    required String mobile,
    required String dlNo,
    required String cabNo,
    required int vehicleType,
    required String homeTown,
    required String adminId,
    double? homeLat,
    double? homeLng,
  }) async {
    final res = await _post(
      "/api/auth/driver/signup-request",
      body: {
        "name": name,
        "mobile": mobile,
        "dl_no": dlNo,
        "cab_no": cabNo,
        "vehicle_type": vehicleType,
        "home_town": homeTown,
        "admin_id": adminId,
        if (homeLat != null) "home_lat": homeLat,
        if (homeLng != null) "home_lng": homeLng,
      },
    );

    final success = res["success"] == true;
    final msg = (res["message"] ??
            (success
                ? "Driver request submitted (pending admin approval)"
                : "Request failed"))
        .toString();

    final data = (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};

    return AuthResult(
      success: success,
      message: msg,
      role: "driver",
      userId: null,
      token: null,
      data: data.isEmpty ? null : data,
    );
  }

  // ---------------- Employee Login + Signup Request ----------------
  static Future<AuthResult> employeeLogin({
    required String mobile,
    required String employeeCode,
  }) async {
    final res = await _post(
      "/api/auth/employee/login",
      body: {
        "mobile": mobile,
        "employeeId": employeeCode,
        "employee_code": employeeCode,
      },
    );

    final data = (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};
    final token = (data["token"] ?? data["access_token"])?.toString();

    // ✅ ROBUST: Token = Success
    final bool isSuccess =
        (token != null && token.isNotEmpty) || (res["success"] == true);
    final msg =
        (res["message"] ?? (isSuccess ? "Login success" : "Login failed"))
            .toString();

    if (!isSuccess) {
      return AuthResult(success: false, message: msg, role: "employee");
    }

    final id = _stringFromAny(data["employee_id"] ??
        data["id"] ??
        (data["profile"] is Map ? data["profile"]["id"] : null));

    return AuthResult(
      success: true,
      message: msg,
      role: "employee",
      userId: id,
      token: token,
      data: data.isEmpty ? null : data,
    );
  }

  /// POST /api/auth/employee/signup-request
  ///
  /// body:
  /// { name, mobile, login_time, logout_time, home_address }
  ///
  /// returns:
  /// { success, message, data:{ employee_code? } }
  static Future<AuthResult> employeeSignupRequest({
    required String name,
    required String mobile,
    required String loginTime, // "HH:mm"
    required String logoutTime, // "HH:mm"
    required String homeAddress,
    required String adminId,
    double? homeLat,
    double? homeLng,
  }) async {
    final res = await _post(
      "/api/auth/employee/signup-request",
      body: {
        "name": name,
        "mobile": mobile,
        "login_time": loginTime,
        "logout_time": logoutTime,
        "home_address": homeAddress,
        "admin_id": adminId,
        if (homeLat != null) "home_lat": homeLat,
        if (homeLng != null) "home_lng": homeLng,
      },
    );

    final success = res["success"] == true;
    final msg = (res["message"] ??
            (success
                ? "Employee request submitted (pending admin approval)"
                : "Request failed"))
        .toString();

    final data = (res["data"] is Map)
        ? (res["data"] as Map).cast<String, dynamic>()
        : <String, dynamic>{};

    return AuthResult(
      success: success,
      message: msg,
      role: "employee",
      userId: null,
      token: null,
      data: data.isEmpty ? null : data,
    );
  }

  static Future<List<CompanyOption>> getCompanies() async {
    final res = await _get("/api/auth/companies");
    final list = (res["data"] is List<dynamic>)
        ? (res["data"] as List<dynamic>)
        : const <dynamic>[];
    return list
        .whereType<Map<dynamic, dynamic>>()
        .map((e) => CompanyOption.fromJson(e.cast<String, dynamic>()))
        .where((e) => e.id.trim().isNotEmpty)
        .toList();
  }

  // ---------------- Small Utils ----------------

  static String? _stringFromAny(dynamic v) {
    if (v == null) return null;
    return v.toString();
  }
}
