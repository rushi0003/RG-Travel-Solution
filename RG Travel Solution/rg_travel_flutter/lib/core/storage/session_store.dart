// flutter/lib/core/storage/session_store.dart
//
// RG Travel Solution — Session Store (SharedPreferences)
//
// ✅ Stores login session for Admin/Driver/Employee:
// - role
// - userId
// - token (optional)
// - name/mobile (optional)
// - lastRouteNo (optional)
//
// Dependencies (pubspec.yaml):
//   shared_preferences: ^2.3.2
//
// Usage:
//   await SessionStore.saveSession(
//     role: UserRole.admin,
//     userId: 1,
//     token: "abc", // optional
//     name: "RG Admin",
//     mobile: "9999999999",
//   );
//
//   final role = await SessionStore.getRole();
//   final uid = await SessionStore.getUserId();
//
//   await SessionStore.clear();

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

enum UserRole { admin, driver, employee }

class SessionStore {
  SessionStore._();

  // =========================
  // KEYS
  // =========================
  static const String _kLoggedIn = 'rg_logged_in';
  static const String _kRole = 'rg_role';
  static const String _kUserId = 'rg_user_id';
  static const String _kToken = 'rg_token';

  // Optional profile fields
  static const String _kName = 'rg_name';
  static const String _kMobile = 'rg_mobile';

  // Optional last route number
  static const String _kLastRouteNo = 'rg_last_route_no';

  // Optional: store any extra payload
  static const String _kExtraJson = 'rg_extra_json';

  // =========================
  // SAVE SESSION
  // =========================

  /// Save session after successful login.
  /// token optional (if backend doesn't use token)
  static Future<void> saveSession({
    required UserRole role,
    required String userId,
    String? token,
    String? name,
    String? mobile,
    Map<String, dynamic>? extra,
  }) async {
    final sp = await SharedPreferences.getInstance();
    final cleanedExtra = <String, dynamic>{...(extra ?? const <String, dynamic>{})};
    if (role != UserRole.driver) {
      cleanedExtra.remove('selected_admin_id');
    }

    await sp.setBool(_kLoggedIn, true);
    await sp.setString(_kRole, role.name);
    await sp.setString(_kUserId, userId);
    await sp.remove(_kLastRouteNo);

    if (token != null && token.trim().isNotEmpty) {
      await sp.setString(_kToken, token.trim());
    } else {
      await sp.remove(_kToken);
    }

    if (name != null) {
      await sp.setString(_kName, name);
    }
    if (mobile != null) {
      await sp.setString(_kMobile, mobile);
    }

    if (cleanedExtra.isNotEmpty) {
      await sp.setString(_kExtraJson, jsonEncode(cleanedExtra));
    } else {
      await sp.remove(_kExtraJson);
    }
  }

  // =========================
  // GETTERS
  // =========================

  static Future<bool> isLoggedIn() async {
    final sp = await SharedPreferences.getInstance();
    return sp.getBool(_kLoggedIn) ?? false;
  }

  static Future<UserRole?> getRole() async {
    final sp = await SharedPreferences.getInstance();
    final r = sp.getString(_kRole);
    if (r == null || r.isEmpty) return null;
    return _roleFromString(r);
  }

  static Future<String?> getUserId() async {
    final sp = await SharedPreferences.getInstance();
    final id = sp.getString(_kUserId);
    return id;
  }

  static Future<String?> getToken() async {
    final sp = await SharedPreferences.getInstance();
    final t = sp.getString(_kToken);
    if (t == null || t.trim().isEmpty) return null;
    return t;
  }

  static Future<String?> getName() async {
    final sp = await SharedPreferences.getInstance();
    final n = sp.getString(_kName);
    if (n == null || n.trim().isEmpty) return null;
    return n;
  }

  static Future<String?> getMobile() async {
    final sp = await SharedPreferences.getInstance();
    final m = sp.getString(_kMobile);
    if (m == null || m.trim().isEmpty) return null;
    return m;
  }

  static Future<Map<String, dynamic>?> getExtra() async {
    final sp = await SharedPreferences.getInstance();
    final s = sp.getString(_kExtraJson);
    if (s == null || s.trim().isEmpty) return null;
    try {
      final v = jsonDecode(s);
      if (v is Map<String, dynamic>) return v;
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<void> mergeExtra(Map<String, dynamic> values) async {
    final sp = await SharedPreferences.getInstance();
    final existing = await getExtra() ?? <String, dynamic>{};
    existing.addAll(values);
    await sp.setString(_kExtraJson, jsonEncode(existing));
  }

  static Future<String?> getSelectedAdminId() async {
    final extra = await getExtra();
    final id = extra?['selected_admin_id']?.toString().trim();
    if (id == null || id.isEmpty) return null;
    return id;
  }

  static Future<void> setSelectedAdminId(String? adminId) async {
    final sp = await SharedPreferences.getInstance();
    final existing = await getExtra() ?? <String, dynamic>{};
    if (adminId == null || adminId.trim().isEmpty) {
      existing.remove('selected_admin_id');
    } else {
      existing['selected_admin_id'] = adminId.trim();
    }
    await sp.setString(_kExtraJson, jsonEncode(existing));
  }

  // =========================
  // ROUTE NO HELPERS (optional)
  // =========================

  static Future<void> setLastRouteNo(String routeNo) async {
    final sp = await SharedPreferences.getInstance();
    await sp.setString(_kLastRouteNo, routeNo);
  }

  static Future<String?> getLastRouteNo() async {
    final sp = await SharedPreferences.getInstance();
    final r = sp.getString(_kLastRouteNo);
    if (r == null || r.trim().isEmpty) return null;
    return r;
  }

  // =========================
  // HEADERS HELPER (token auth)
  // =========================
  //
  // If you use token-based auth later, you can call:
  // final headers = await SessionStore.authHeaders();
  //
  static Future<Map<String, String>> authHeaders({
    Map<String, String>? baseHeaders,
  }) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (baseHeaders != null) ...baseHeaders,
    };

    final token = await getToken();
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  // =========================
  // CLEAR / LOGOUT
  // =========================

  static Future<void> clear() async {
    final sp = await SharedPreferences.getInstance();

    await sp.remove(_kLoggedIn);
    await sp.remove(_kRole);
    await sp.remove(_kUserId);
    await sp.remove(_kToken);
    await sp.remove(_kName);
    await sp.remove(_kMobile);
    await sp.remove(_kLastRouteNo);
    await sp.remove(_kExtraJson);
  }

  // =========================
  // INTERNAL UTILS
  // =========================

  static UserRole? _roleFromString(String s) {
    final v = s.trim().toLowerCase();
    if (v == 'admin') return UserRole.admin;
    if (v == 'driver') return UserRole.driver;
    if (v == 'employee') return UserRole.employee;
    return null;
  }
}
