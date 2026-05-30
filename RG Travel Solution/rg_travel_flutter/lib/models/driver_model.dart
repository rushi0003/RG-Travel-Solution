// flutter/lib/models/driver_model.dart
//
// RG Travel Solution — DriverModel
// Used in driver dashboard + admin drivers screen + backend APIs.
//
// Updated to support alias fields for new Admin Driver Screen.

class DriverModel {
  final String id;

  String name;
  String mobile; // 10 digits
  String dlNo; // 2 letters + 13 digits (as per your spec)
  String cabNo; // vehicle number format
  int vehicleType; // 4 or 6
  String homeTown; // address/location text
  double? homeLat;
  double? homeLng;

  // Optional workflow/status fields (admin approval system)
  String? status; // "pending" | "approved" | "rejected"
  bool? goHomeRequested; // driver requested go-home
  String? createdAt;
  String? updatedAt;

  // ---------------------------------------------------------------------------
  // ALIASES for New Driver Screen Compatibility
  // ---------------------------------------------------------------------------
  String get licenseNo => dlNo;
  String get vehicleNo => cabNo;
  String get hometownAddress => homeTown;

  DriverModel({
    required this.id,
    required this.name,
    required this.mobile,
    required this.dlNo,
    required this.cabNo,
    required this.vehicleType,
    required this.homeTown,
    this.homeLat,
    this.homeLng,
    this.status,
    this.goHomeRequested,
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

  static double? _toDouble(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString().trim());
  }

  /// Backend → DriverModel
  factory DriverModel.fromJson(Map<String, dynamic> json) {
    final id = _toStr(json["id"] ?? json["driver_id"] ?? json["driverId"]);

    // Map new keys to old keys if old keys are missing
    return DriverModel(
      id: id,
      name: _toStr(json["name"]),
      mobile: _toStr(json["mobile"] ?? json["mo_no"] ?? json["moNo"]),
      dlNo: _toStr(
          json["dl_no"] ?? json["dlNo"] ?? json["dl"] ?? json["license_no"]),
      cabNo: _toStr(json["cab_no"] ??
          json["cabNo"] ??
          json["vehicle_no"] ??
          json["vehicleNo"]),
      vehicleType: _toInt(
          json["vehicle_type"] ?? json["vehicleType"] ?? json["seats"],
          fallback: 4),
      homeTown: _toStr(json["home_town"] ??
          json["homeTown"] ??
          json["hometown"] ??
          json["hometown_address"]),
      homeLat:
          _toDouble(json["home_lat"] ?? json["hometown_lat"] ?? json["lat"]),
      homeLng:
          _toDouble(json["home_lng"] ?? json["hometown_lng"] ?? json["lng"]),
      status: (json["status"] ?? json["approval_status"])?.toString(),
      goHomeRequested:
          _toBool(json["go_home_requested"] ?? json["goHomeRequested"]),
      createdAt: (json["created_at"] ?? json["createdAt"])?.toString(),
      updatedAt: (json["updated_at"] ?? json["updatedAt"])?.toString(),
    );
  }

  /// DriverModel → JSON (general)
  Map<String, dynamic> toJson() {
    return {
      "id": id,
      "name": name,
      "mobile": mobile,
      "dl_no": dlNo,
      "cab_no": cabNo,
      "vehicle_type": vehicleType,
      "home_town": homeTown,
      if (homeLat != null) "home_lat": homeLat,
      if (homeLng != null) "home_lng": homeLng,

      // Add new keys just in case backend expects them now
      "license_no": dlNo,
      "vehicle_no": cabNo,
      "hometown_address": homeTown,
      if (homeLat != null) "hometown_lat": homeLat,
      if (homeLng != null) "hometown_lng": homeLng,

      if (status != null) "status": status,
      if (goHomeRequested != null) "go_home_requested": goHomeRequested,
      if (createdAt != null) "created_at": createdAt,
      if (updatedAt != null) "updated_at": updatedAt,
    };
  }

  // ------------------------------------------------------------
  // Helper Methods (Restored)
  // ------------------------------------------------------------

  Map<String, dynamic> toUpdatePayload() {
    return {
      "name": name,
      "mobile": mobile,
      "dl_no": dlNo,
      "cab_no": cabNo,
      "vehicle_type": vehicleType,
      "home_town": homeTown,
      if (homeLat != null) "home_lat": homeLat,
      if (homeLng != null) "home_lng": homeLng,
    };
  }
}

// ----------------------------------------------------------------
// Alias Class for 'Driver'
// This ensures that code importing 'Driver' (from my new screen) works
// while utilizing the same underlying DriverModel logic/file.
// ----------------------------------------------------------------
typedef Driver = DriverModel;
