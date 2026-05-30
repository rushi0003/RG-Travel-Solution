// flutter/lib/models/admin_model.dart
//
// RG Travel Solution — AdminModel
// Used by Admin dashboards + profile sheet + backend APIs.
//
// Supports both snake_case and camelCase JSON keys.

class AdminModel {
  final int id;

  String name;
  String mobile; // 10 digits
  String officeName;
  String officeAddress;

  AdminModel({
    required this.id,
    required this.name,
    required this.mobile,
    required this.officeName,
    required this.officeAddress,
  });

  // ------------------------------------------------------------
  // JSON Parsing Helpers
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

  /// Backend → AdminModel
  factory AdminModel.fromJson(Map<String, dynamic> json) {
    final id = _toInt(json["id"] ?? json["admin_id"] ?? json["adminId"]);

    return AdminModel(
      id: id,
      name: _toStr(json["name"]),
      mobile: _toStr(json["mobile"] ?? json["mo_no"] ?? json["moNo"]),
      officeName: _toStr(json["office_name"] ?? json["officeName"] ?? json["office"]),
      officeAddress: _toStr(json["office_address"] ?? json["officeAddress"] ?? json["address"]),
    );
  }

  /// AdminModel → JSON (General)
  Map<String, dynamic> toJson() {
    return {
      "id": id,
      "name": name,
      "mobile": mobile,
      "office_name": officeName,
      "office_address": officeAddress,
    };
  }

  /// ✅ Payload for PUT /api/admin/<id>/profile
  Map<String, dynamic> toUpdatePayload() {
    return {
      "name": name,
      "mobile": mobile,
      "office_name": officeName,
      "office_address": officeAddress,
    };
  }

  // ------------------------------------------------------------
  // Copy / Update helpers
  // ------------------------------------------------------------

  AdminModel copyWith({
    int? id,
    String? name,
    String? mobile,
    String? officeName,
    String? officeAddress,
  }) {
    return AdminModel(
      id: id ?? this.id,
      name: name ?? this.name,
      mobile: mobile ?? this.mobile,
      officeName: officeName ?? this.officeName,
      officeAddress: officeAddress ?? this.officeAddress,
    );
  }

  // ------------------------------------------------------------
  // Validation helpers (UI can reuse)
  // ------------------------------------------------------------

  static bool isMobile10(String value) {
    final v = value.trim();
    final reg = RegExp(r"^\d{10}$");
    return reg.hasMatch(v);
  }

  /// Returns list of validation errors (empty => valid)
  List<String> validate() {
    final errors = <String>[];

    if (name.trim().length < 2) {
      errors.add("Admin name must be at least 2 characters.");
    }
    if (!isMobile10(mobile)) {
      errors.add("Mobile must be exactly 10 digits.");
    }
    if (officeName.trim().isEmpty) {
      errors.add("Office name is required.");
    }
    if (officeAddress.trim().isEmpty) {
      errors.add("Office address is required.");
    }

    return errors;
  }

  // ------------------------------------------------------------
  // Debug / Display helpers
  // ------------------------------------------------------------

  @override
  String toString() {
    return "AdminModel(id: $id, name: $name, mobile: $mobile, officeName: $officeName)";
  }
}
