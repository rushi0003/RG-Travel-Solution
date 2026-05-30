// flutter/lib/models/trip_model.dart
//
// RG Travel Solution — TripModel (Route No based)
//
// Key concepts:
// - routeNo: unique 10-character route number (PRIMARY identity)
// - tripType: pickup or drop
// - status: pending/assigned/in_progress/completed/cancelled
// - scheduledTime: "HH:mm" or ISO (backend decides)
// - stops: list of pickup/drop stops (4 or 6 employees)
// - polyline: google directions encoded polyline
// - totalKm: total distance (office -> waypoints -> last stop -> office) or as returned by backend
// - OTP: start/end OTP (employee sees OTP; driver verifies OTP)
// - No-show: driver can mark employee no-show
//
// Works for Admin / Driver / Employee dashboards.

enum TripType { pickup, drop, unknown }
enum TripStatus { pending, assigned, inProgress, completed, cancelled, unknown }

class TripModel {
  // Primary identity
  final String routeNo; // 10-char route number

  // Optional numeric DB id (backend might still keep)
  final int? id;

  TripType tripType;
  TripStatus status;

  // Time & Dates
  String? tripDate; // YYYY-MM-DD
  String? scheduledTime; // HH:mm or ISO
  String? startTime; // ISO
  String? endTime; // ISO

  // Office info (optional)
  String? officeName;
  String? officeAddress;
  double? officeLat;
  double? officeLng;

  // Cab + Driver
  String? cabNo;
  DriverSummary? driver;

  // Employees + Stops
  List<EmployeeSummary> employees; // members
  List<TripStop> stops;            // ordered stops/waypoints

  // Google routing
  String? polyline;       // encoded polyline string
  double? totalKm;        // numeric km
  int? totalDurationMin;  // total travel time minutes (optional)

  // OTP
  OtpInfo? startOtp;
  OtpInfo? endOtp;

  // No-show / absent
  List<int> noShowEmployeeIds; // employeeIds marked no-show by driver
  List<int> absentEmployeeIds; // optional if backend sends

  // Cancel
  String? cancelReason;
  String? cancelledAt;

  // Meta
  String? createdAt;
  String? updatedAt;

  TripModel({
    required this.routeNo,
    this.id,
    this.tripType = TripType.unknown,
    this.status = TripStatus.unknown,
    this.tripDate,
    this.scheduledTime,
    this.startTime,
    this.endTime,
    this.officeName,
    this.officeAddress,
    this.officeLat,
    this.officeLng,
    this.cabNo,
    this.driver,
    List<EmployeeSummary>? employees,
    List<TripStop>? stops,
    this.polyline,
    this.totalKm,
    this.totalDurationMin,
    this.startOtp,
    this.endOtp,
    List<int>? noShowEmployeeIds,
    List<int>? absentEmployeeIds,
    this.cancelReason,
    this.cancelledAt,
    this.createdAt,
    this.updatedAt,
  })  : employees = employees ?? <EmployeeSummary>[],
        stops = stops ?? <TripStop>[],
        noShowEmployeeIds = noShowEmployeeIds ?? <int>[],
        absentEmployeeIds = absentEmployeeIds ?? <int>[];

  // ------------------------------------------------------------
  // Parsing helpers
  // ------------------------------------------------------------

  static int? _toIntN(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    if (v is double) return v.toInt();
    if (v is String) return int.tryParse(v);
    return null;
  }

  static double? _toDoubleN(dynamic v) {
    if (v == null) return null;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  static String? _toStrN(dynamic v) {
    if (v == null) return null;
    final s = v.toString();
    return s.isEmpty ? null : s;
  }

  static List<dynamic> _toList(dynamic v) {
    if (v is List) return v;
    return const [];
  }

  static TripType _parseTripType(dynamic v) {
    final s = (v ?? "").toString().toLowerCase().trim();
    if (s == "pickup") return TripType.pickup;
    if (s == "drop") return TripType.drop;
    return TripType.unknown;
  }

  static TripStatus _parseTripStatus(dynamic v) {
    final s = (v ?? "").toString().toLowerCase().trim();
    switch (s) {
      case "pending":
        return TripStatus.pending;
      case "assigned":
        return TripStatus.assigned;
      case "in_progress":
      case "inprogress":
      case "running":
        return TripStatus.inProgress;
      case "completed":
      case "done":
        return TripStatus.completed;
      case "cancelled":
      case "canceled":
        return TripStatus.cancelled;
      default:
        return TripStatus.unknown;
    }
  }

  static String tripTypeToString(TripType t) {
    switch (t) {
      case TripType.pickup:
        return "pickup";
      case TripType.drop:
        return "drop";
      default:
        return "unknown";
    }
  }

  static String tripStatusToString(TripStatus s) {
    switch (s) {
      case TripStatus.pending:
        return "pending";
      case TripStatus.assigned:
        return "assigned";
      case TripStatus.inProgress:
        return "in_progress";
      case TripStatus.completed:
        return "completed";
      case TripStatus.cancelled:
        return "cancelled";
      default:
        return "unknown";
    }
  }

  // ------------------------------------------------------------
  // fromJson / toJson
  // ------------------------------------------------------------

  factory TripModel.fromJson(Map<String, dynamic> json) {
    // Route No is primary
    final routeNo = (json["route_no"] ?? json["routeNo"] ?? json["route"] ?? "").toString();

    // Employees
    final empList = _toList(json["employees"] ?? json["members"]);
    final employees = empList
        .whereType<Map<String, dynamic>>()
        .map((e) => EmployeeSummary.fromJson(e))
        .toList();

    // Stops / waypoints
    final stopList = _toList(json["stops"] ?? json["waypoints"] ?? json["pickup_points"]);
    final stops = stopList
        .whereType<Map<String, dynamic>>()
        .map((e) => TripStop.fromJson(e))
        .toList();

    // No-show/absent ids
    final noShowIds = _toList(json["no_show_employee_ids"] ?? json["noShowEmployeeIds"])
        .map((e) => _toIntN(e))
        .whereType<int>()
        .toList();

    final absentIds = _toList(json["absent_employee_ids"] ?? json["absentEmployeeIds"])
        .map((e) => _toIntN(e))
        .whereType<int>()
        .toList();

    // Driver
    final driverJson = json["driver"] ?? json["driver_info"] ?? json["driverInfo"];
    DriverSummary? driver;
    if (driverJson is Map) {
      driver = DriverSummary.fromJson(driverJson.cast<String, dynamic>());
    }

    // OTP
    final startOtpJson = json["start_otp"] ?? json["startOtp"];
    final endOtpJson = json["end_otp"] ?? json["endOtp"];
    OtpInfo? startOtp;
    OtpInfo? endOtp;
    if (startOtpJson is Map) startOtp = OtpInfo.fromJson(startOtpJson.cast<String, dynamic>());
    if (endOtpJson is Map) endOtp = OtpInfo.fromJson(endOtpJson.cast<String, dynamic>());

    return TripModel(
      routeNo: routeNo,
      id: _toIntN(json["id"] ?? json["trip_id"] ?? json["tripId"]),
      tripType: _parseTripType(json["trip_type"] ?? json["tripType"]),
      status: _parseTripStatus(json["status"]),
      tripDate: _toStrN(json["trip_date"] ?? json["tripDate"] ?? json["date"]),
      scheduledTime: _toStrN(json["scheduled_time"] ?? json["scheduledTime"] ?? json["time"]),
      startTime: _toStrN(json["start_time"] ?? json["startTime"]),
      endTime: _toStrN(json["end_time"] ?? json["endTime"]),
      officeName: _toStrN(json["office_name"] ?? json["officeName"]),
      officeAddress: _toStrN(json["office_address"] ?? json["officeAddress"]),
      officeLat: _toDoubleN(json["office_lat"] ?? json["officeLat"]),
      officeLng: _toDoubleN(json["office_lng"] ?? json["officeLng"]),
      cabNo: _toStrN(json["cab_no"] ?? json["cabNo"] ?? json["vehicle_no"] ?? json["vehicleNo"]),
      driver: driver,
      employees: employees,
      stops: stops,
      polyline: _toStrN(json["polyline"] ?? json["route_polyline"] ?? json["routePolyline"]),
      totalKm: _toDoubleN(json["total_km"] ?? json["totalKm"] ?? json["km"]),
      totalDurationMin: _toIntN(json["total_duration_min"] ?? json["totalDurationMin"]),
      startOtp: startOtp,
      endOtp: endOtp,
      noShowEmployeeIds: noShowIds,
      absentEmployeeIds: absentIds,
      cancelReason: _toStrN(json["cancel_reason"] ?? json["cancelReason"]),
      cancelledAt: _toStrN(json["cancelled_at"] ?? json["cancelledAt"]),
      createdAt: _toStrN(json["created_at"] ?? json["createdAt"]),
      updatedAt: _toStrN(json["updated_at"] ?? json["updatedAt"]),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "route_no": routeNo,
      if (id != null) "id": id,
      "trip_type": tripTypeToString(tripType),
      "status": tripStatusToString(status),
      if (tripDate != null) "trip_date": tripDate,
      if (scheduledTime != null) "scheduled_time": scheduledTime,
      if (startTime != null) "start_time": startTime,
      if (endTime != null) "end_time": endTime,
      if (officeName != null) "office_name": officeName,
      if (officeAddress != null) "office_address": officeAddress,
      if (officeLat != null) "office_lat": officeLat,
      if (officeLng != null) "office_lng": officeLng,
      if (cabNo != null) "cab_no": cabNo,
      if (driver != null) "driver": driver!.toJson(),
      "employees": employees.map((e) => e.toJson()).toList(),
      "stops": stops.map((s) => s.toJson()).toList(),
      if (polyline != null) "polyline": polyline,
      if (totalKm != null) "total_km": totalKm,
      if (totalDurationMin != null) "total_duration_min": totalDurationMin,
      if (startOtp != null) "start_otp": startOtp!.toJson(),
      if (endOtp != null) "end_otp": endOtp!.toJson(),
      "no_show_employee_ids": noShowEmployeeIds,
      "absent_employee_ids": absentEmployeeIds,
      if (cancelReason != null) "cancel_reason": cancelReason,
      if (cancelledAt != null) "cancelled_at": cancelledAt,
      if (createdAt != null) "created_at": createdAt,
      if (updatedAt != null) "updated_at": updatedAt,
    };
  }

  // ------------------------------------------------------------
  // Convenience helpers for UI logic
  // ------------------------------------------------------------

  bool get isPickup => tripType == TripType.pickup;
  bool get isDrop => tripType == TripType.drop;

  bool get isLive => status == TripStatus.inProgress || status == TripStatus.assigned;
  bool get isCompleted => status == TripStatus.completed;
  bool get isCancelled => status == TripStatus.cancelled;

  bool isEmployeeNoShow(int employeeId) => noShowEmployeeIds.contains(employeeId);
  bool isEmployeeAbsent(int employeeId) => absentEmployeeIds.contains(employeeId);

  /// Driver can start trip only when start OTP verified (for pickup)
  /// Backend will control actual.
  bool get requiresStartOtp => isPickup;

  /// End OTP required for both pickup & drop (as per your spec: pickup both; drop end only)
  bool get requiresEndOtp => true;
}

// ===================================================================
// Nested small models (Driver/Employee summaries, Stops, OTP info)
// ===================================================================

class DriverSummary {
  final int id;
  final String name;
  final String mobile;
  final String? cabNo;
  final int? vehicleType; // 4/6
  final String? homeTown;

  DriverSummary({
    required this.id,
    required this.name,
    required this.mobile,
    this.cabNo,
    this.vehicleType,
    this.homeTown,
  });

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

  factory DriverSummary.fromJson(Map<String, dynamic> json) {
    return DriverSummary(
      id: _toInt(json["id"] ?? json["driver_id"] ?? json["driverId"]),
      name: _toStr(json["name"]),
      mobile: _toStr(json["mobile"] ?? json["mo_no"] ?? json["moNo"]),
      cabNo: (json["cab_no"] ?? json["cabNo"] ?? json["vehicle_no"] ?? json["vehicleNo"])?.toString(),
      vehicleType: (json["vehicle_type"] ?? json["vehicleType"] ?? json["seats"]) is int
          ? (json["vehicle_type"] ?? json["vehicleType"] ?? json["seats"]) as int
          : int.tryParse((json["vehicle_type"] ?? json["vehicleType"] ?? json["seats"] ?? "").toString()),
      homeTown: (json["home_town"] ?? json["homeTown"])?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "id": id,
      "name": name,
      "mobile": mobile,
      if (cabNo != null) "cab_no": cabNo,
      if (vehicleType != null) "vehicle_type": vehicleType,
      if (homeTown != null) "home_town": homeTown,
    };
  }
}

class EmployeeSummary {
  final int id;
  final String name;
  final String mobile;
  final String? employeeCode;
  final String? homeAddress;
  final String? loginTime;
  final String? logoutTime;

  EmployeeSummary({
    required this.id,
    required this.name,
    required this.mobile,
    this.employeeCode,
    this.homeAddress,
    this.loginTime,
    this.logoutTime,
  });

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

  factory EmployeeSummary.fromJson(Map<String, dynamic> json) {
    return EmployeeSummary(
      id: _toInt(json["id"] ?? json["employee_id"] ?? json["employeeId"]),
      name: _toStr(json["name"]),
      mobile: _toStr(json["mobile"] ?? json["mo_no"] ?? json["moNo"]),
      employeeCode: (json["employee_code"] ?? json["employeeCode"] ?? json["code"])?.toString(),
      homeAddress: (json["home_address"] ?? json["homeAddress"] ?? json["address"])?.toString(),
      loginTime: (json["login_time"] ?? json["loginTime"])?.toString(),
      logoutTime: (json["logout_time"] ?? json["logoutTime"])?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "id": id,
      "name": name,
      "mobile": mobile,
      if (employeeCode != null) "employee_code": employeeCode,
      if (homeAddress != null) "home_address": homeAddress,
      if (loginTime != null) "login_time": loginTime,
      if (logoutTime != null) "logout_time": logoutTime,
    };
  }
}

class TripStop {
  /// order index in route (0..n-1)
  final int order;

  /// Employee for this stop (optional for office stops)
  final int? employeeId;
  final String? employeeName;
  final String? address;

  /// coordinates (optional)
  final double? lat;
  final double? lng;

  TripStop({
    required this.order,
    this.employeeId,
    this.employeeName,
    this.address,
    this.lat,
    this.lng,
  });

  static int _toInt(dynamic v, {int fallback = 0}) {
    if (v == null) return fallback;
    if (v is int) return v;
    if (v is double) return v.toInt();
    if (v is String) return int.tryParse(v) ?? fallback;
    return fallback;
  }

  static double? _toDouble(dynamic v) {
    if (v == null) return null;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  factory TripStop.fromJson(Map<String, dynamic> json) {
    return TripStop(
      order: _toInt(json["order"] ?? json["seq"] ?? json["index"], fallback: 0),
      employeeId: (json["employee_id"] ?? json["employeeId"]) == null
          ? null
          : _toInt(json["employee_id"] ?? json["employeeId"], fallback: 0),
      employeeName: (json["employee_name"] ?? json["employeeName"] ?? json["name"])?.toString(),
      address: (json["address"] ?? json["location"])?.toString(),
      lat: _toDouble(json["lat"] ?? json["latitude"]),
      lng: _toDouble(json["lng"] ?? json["longitude"]),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "order": order,
      if (employeeId != null) "employee_id": employeeId,
      if (employeeName != null) "employee_name": employeeName,
      if (address != null) "address": address,
      if (lat != null) "lat": lat,
      if (lng != null) "lng": lng,
    };
  }
}

class OtpInfo {
  /// backend may return otp in response for employee view (NOT store in DB plaintext)
  final String? otp;
  final String? expiresAt; // ISO string
  final bool? verified;
  final String? verifiedAt;

  OtpInfo({
    this.otp,
    this.expiresAt,
    this.verified,
    this.verifiedAt,
  });

  factory OtpInfo.fromJson(Map<String, dynamic> json) {
    return OtpInfo(
      otp: (json["otp"] ?? json["code"])?.toString(),
      expiresAt: (json["expires_at"] ?? json["expiresAt"])?.toString(),
      verified: (json["verified"] is bool) ? json["verified"] as bool : null,
      verifiedAt: (json["verified_at"] ?? json["verifiedAt"])?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (otp != null) "otp": otp,
      if (expiresAt != null) "expires_at": expiresAt,
      if (verified != null) "verified": verified,
      if (verifiedAt != null) "verified_at": verifiedAt,
    };
  }
}
