// flutter/lib/models/employee_model.dart
//
// RG Travel Solution — EmployeeModel
// Used in employee dashboard + admin employees screen + backend APIs.
//
// Supports snake_case and camelCase JSON keys.
// Includes validations for:
// - Mobile (10 digits)
// - Employee Code (permanent) e.g. "EMP001" or "RGEMP0001" (flexible)
// - Time format "HH:mm" for login/logout
//
// Optional workflow fields:
// - status: pending/approved/rejected
// - absent flags / absent requests

class EmployeeModel {
  final int id;

  String name;
  String mobile; // 10 digits
  String employeeCode; // permanent (used for login)

  String loginTime;  // "HH:mm"
  String logoutTime; // "HH:mm"

  String homeAddress; // address/location text

  // Optional status / workflow fields
  String? status; // "pending" | "approved" | "rejected"
  bool? isAbsent; // current-day absent flag if backend provides
  String? absentDate; // "YYYY-MM-DD" (if relevant)
  String? createdAt;
  String? updatedAt;

  EmployeeModel({
    required this.id,
    required this.name,
    required this.mobile,
    required this.employeeCode,
    required this.loginTime,
    required this.logoutTime,
    required this.homeAddress,
    this.status,
    this.isAbsent,
    this.absentDate,
    this.createdAt,
    this.updatedAt,
  });

  // ------------------------------------------------------------
  // JSON Helpers
  // ------------------------------------------------------------

  static int _toInt(dynamic v, {int fallback = 0}) {
    if (v == null) return fallback;
    if (v is int) return v;
    if (v is double) return v.toInt();
    if (v is String) return int.tryParse(v) ?? fallback;
    return fallback;
  }

  static String _toStr(dynamic v, {String fallback = ""}) {
    if (v == null) return fallback;
    return v.toString();
  }

  static bool? _toBool(dynamic v) {
    if (v == null) return null;
    if (v is bool) return v;
    if (v is int) return v == 1;
    if (v is String) {
      final s = v.toLowerCase().trim();
      if (s == "true" || s == "1" || s == "yes") return true;
      if (s == "false" || s == "0" || s == "no") return false;
    }
    return null;
  }

  /// Backend → EmployeeModel
  factory EmployeeModel.fromJson(Map<String, dynamic> json) {
    final id = _toInt(json["id"] ?? json["employee_id"] ?? json["employeeId"]);

    return EmployeeModel(
      id: id,
      name: _toStr(json["name"]),
      mobile: _toStr(json["mobile"] ?? json["mo_no"] ?? json["moNo"]),
      employeeCode: _toStr(
        json["employee_code"] ?? json["employeeCode"] ?? json["code"] ?? json["emp_code"],
      ),
      loginTime: _toStr(json["login_time"] ?? json["loginTime"]),
      logoutTime: _toStr(json["logout_time"] ?? json["logoutTime"]),
      homeAddress: _toStr(json["home_address"] ?? json["homeAddress"] ?? json["address"]),
      status: (json["status"] ?? json["approval_status"])?.toString(),
      isAbsent: _toBool(json["is_absent"] ?? json["isAbsent"]),
      absentDate: (json["absent_date"] ?? json["absentDate"])?.toString(),
      createdAt: (json["created_at"] ?? json["createdAt"])?.toString(),
      updatedAt: (json["updated_at"] ?? json["updatedAt"])?.toString(),
    );
  }

  /// EmployeeModel → JSON (general)
  Map<String, dynamic> toJson() {
    return {
      "id": id,
      "name": name,
      "mobile": mobile,
      "employee_code": employeeCode,
      "login_time": loginTime,
      "logout_time": logoutTime,
      "home_address": homeAddress,
      if (status != null) "status": status,
      if (isAbsent != null) "is_absent": isAbsent,
      if (absentDate != null) "absent_date": absentDate,
      if (createdAt != null) "created_at": createdAt,
      if (updatedAt != null) "updated_at": updatedAt,
    };
  }

  /// ✅ Payload for PUT /api/employee/<id>/profile
  /// (employee_code is permanent; backend should ignore if you send)
  Map<String, dynamic> toUpdatePayload() {
    return {
      "name": name,
      "mobile": mobile,
      "login_time": loginTime,
      "logout_time": logoutTime,
      "home_address": homeAddress,
      // Do NOT change employee_code in update by default
    };
  }

  /// ✅ Payload for POST /api/auth/employee/signup-request
  /// (admin approves and generates employee_code)
  Map<String, dynamic> toSignupRequestPayload() {
    return {
      "name": name,
      "mobile": mobile,
      "login_time": loginTime,
      "logout_time": logoutTime,
      "home_address": homeAddress,
    };
  }

  /// ✅ Payload for POST /api/employee/<id>/profile-change-request
  /// (send only changed fields to backend)
  Map<String, dynamic> toChangeRequestPayload({
    bool includeName = true,
    bool includeMobile = true,
    bool includeLoginTime = true,
    bool includeLogoutTime = true,
    bool includeHomeAddress = true,
  }) {
    return {
      if (includeName) "name": name,
      if (includeMobile) "mobile": mobile,
      if (includeLoginTime) "login_time": loginTime,
      if (includeLogoutTime) "logout_time": logoutTime,
      if (includeHomeAddress) "home_address": homeAddress,
    };
  }

  /// ✅ Payload for Absent request:
  /// POST /api/employee/<id>/absent/request
  Map<String, dynamic> toAbsentRequestPayload({
    required String date, // YYYY-MM-DD
    String reason = "Absent",
  }) {
    return {
      "date": date,
      "reason": reason,
    };
  }

  // ------------------------------------------------------------
  // Copy Helper
  // ------------------------------------------------------------

  EmployeeModel copyWith({
    int? id,
    String? name,
    String? mobile,
    String? employeeCode,
    String? loginTime,
    String? logoutTime,
    String? homeAddress,
    String? status,
    bool? isAbsent,
    String? absentDate,
    String? createdAt,
    String? updatedAt,
  }) {
    return EmployeeModel(
      id: id ?? this.id,
      name: name ?? this.name,
      mobile: mobile ?? this.mobile,
      employeeCode: employeeCode ?? this.employeeCode,
      loginTime: loginTime ?? this.loginTime,
      logoutTime: logoutTime ?? this.logoutTime,
      homeAddress: homeAddress ?? this.homeAddress,
      status: status ?? this.status,
      isAbsent: isAbsent ?? this.isAbsent,
      absentDate: absentDate ?? this.absentDate,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  // ------------------------------------------------------------
  // Validation Helpers
  // ------------------------------------------------------------

  /// Exactly 10 digits
  static bool isMobile10(String value) {
    final v = value.trim();
    return RegExp(r"^\d{10}$").hasMatch(v);
  }

  /// Employee code (flexible):
  /// Accept: EMP001, RGEMP0001, E12345, etc.
  /// For strict rules, update regex.
  static bool isEmployeeCodeValid(String value) {
    final v = value.trim().toUpperCase();
    // at least 3 chars, alphanumeric, allow _ or -
    return RegExp(r"^[A-Z0-9_-]{3,20}$").hasMatch(v);
  }

  /// Time must be "HH:mm" 24-hour
  static bool isTimeHHmm(String value) {
    final v = value.trim();
    final m = RegExp(r"^(\d{2}):(\d{2})$").firstMatch(v);
    if (m == null) return false;
    final hh = int.tryParse(m.group(1)!);
    final mm = int.tryParse(m.group(2)!);
    if (hh == null || mm == null) return false;
    if (hh < 0 || hh > 23) return false;
    if (mm < 0 || mm > 59) return false;
    return true;
  }

  /// Returns validation errors list (empty => valid)
  List<String> validate({
    bool validateCode = true,
  }) {
    final errors = <String>[];

    if (name.trim().length < 2) {
      errors.add("Employee name must be at least 2 characters.");
    }
    if (!isMobile10(mobile)) {
      errors.add("Mobile must be exactly 10 digits.");
    }
    if (validateCode && employeeCode.trim().isNotEmpty) {
      if (!isEmployeeCodeValid(employeeCode)) {
        errors.add("Employee code is invalid.");
      }
    }
    if (!isTimeHHmm(loginTime)) {
      errors.add("Login time must be HH:mm (24-hour).");
    }
    if (!isTimeHHmm(logoutTime)) {
      errors.add("Logout time must be HH:mm (24-hour).");
    }
    if (homeAddress.trim().isEmpty) {
      errors.add("Home address/location is required.");
    }

    return errors;
  }

  // ------------------------------------------------------------
  // Simple NLP-like Search helper (for UI lists)
  // ------------------------------------------------------------

  /// Helps admin search box:
  /// matches by name/mobile/code/address (contains)
  bool matchesQuery(String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return true;

    final fields = [
      name,
      mobile,
      employeeCode,
      loginTime,
      logoutTime,
      homeAddress,
    ].join(" ").toLowerCase();

    return fields.contains(q);
  }

  // ------------------------------------------------------------
  // Debug
  // ------------------------------------------------------------

  @override
  String toString() {
    return "EmployeeModel(id: $id, name: $name, mobile: $mobile, code: $employeeCode, login: $loginTime, logout: $logoutTime)";
  }
}
