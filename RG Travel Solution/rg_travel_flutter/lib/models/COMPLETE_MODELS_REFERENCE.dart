/// flutter/lib/models/complete_models_example.dart
/// 
/// Complete example implementation showing how all models should be structured
/// for proper JSON serialization/deserialization
///

// helper parsing utilities
String _str(dynamic v) => v == null ? '' : v.toString();
String? _strNullable(dynamic v) => v == null ? null : v.toString();
int _int(dynamic v) {
  if (v == null) return 0;
  if (v is int) return v;
  return int.tryParse(v.toString()) ?? 0;
}

// ==================== ADMIN MODEL ====================
class AdminModel {
  final String id;
  final String name;
  final String mobile;
  final String? email;
  final String? officeName;
  final String? officeAddress;
  final String? createdAt;
  final String? updatedAt;

  AdminModel({
    required this.id,
    required this.name,
    required this.mobile,
    this.email,
    this.officeName,
    this.officeAddress,
    this.createdAt,
    this.updatedAt,
  });

  factory AdminModel.fromJson(Map<String, dynamic> json) {
    return AdminModel(
      id: _str(json['id']),
      name: _str(json['name']),
      mobile: _str(json['mobile']),
      email: _strNullable(json['email']),
      officeName: _strNullable(json['office_name'] ?? json['officeName']),
      officeAddress: _strNullable(json['office_address'] ?? json['officeAddress']),
      createdAt: _strNullable(json['created_at']),
      updatedAt: _strNullable(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'mobile': mobile,
      'email': email,
      'office_name': officeName,
      'office_address': officeAddress,
      'created_at': createdAt,
      'updated_at': updatedAt,
    };
  }
}

// ==================== DRIVER MODEL ====================
class DriverModel {
  final String id;
  final String name;
  final String mobile;
  final String dlNo;
  final String vehicleNo;
  final String? vehicleType;
  final String? homeTown;
  final int isApproved;
  final String? dlExpiry;
  final String? createdAt;
  final String? updatedAt;

  DriverModel({
    required this.id,
    required this.name,
    required this.mobile,
    required this.dlNo,
    required this.vehicleNo,
    this.vehicleType,
    this.homeTown,
    this.isApproved = 0,
    this.dlExpiry,
    this.createdAt,
    this.updatedAt,
  });

  factory DriverModel.fromJson(Map<String, dynamic> json) {
    return DriverModel(
      id: _str(json['id']),
      name: _str(json['name']),
      mobile: _str(json['mobile']),
      dlNo: _str(json['dl_no']),
      vehicleNo: _str(json['vehicle_no']),
      vehicleType: _strNullable(json['vehicle_type']),
      homeTown: _strNullable(json['home_town']),
      isApproved: _int(json['is_approved']),
      dlExpiry: _strNullable(json['dl_expiry']),
      createdAt: _strNullable(json['created_at']),
      updatedAt: _strNullable(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'mobile': mobile,
      'dl_no': dlNo,
      'vehicle_no': vehicleNo,
      'vehicle_type': vehicleType,
      'home_town': homeTown,
      'is_approved': isApproved,
      'dl_expiry': dlExpiry,
      'created_at': createdAt,
      'updated_at': updatedAt,
    };
  }

  bool get isApprovedStatus => isApproved == 1;
}

// ==================== EMPLOYEE MODEL ====================
class EmployeeModel {
  final String id;
  final String name;
  final String mobile;
  final String? email;
  final String? empCode;
  final String? department;
  final int isApproved;
  final String? createdAt;
  final String? updatedAt;

  EmployeeModel({
    required this.id,
    required this.name,
    required this.mobile,
    this.email,
    this.empCode,
    this.department,
    this.isApproved = 0,
    this.createdAt,
    this.updatedAt,
  });

  factory EmployeeModel.fromJson(Map<String, dynamic> json) {
    return EmployeeModel(
      id: _str(json['id']),
      name: _str(json['name']),
      mobile: _str(json['mobile']),
      email: _strNullable(json['email']),
      empCode: _strNullable(json['emp_code']),
      department: _strNullable(json['department']),
      isApproved: _int(json['is_approved']),
      createdAt: _strNullable(json['created_at']),
      updatedAt: _strNullable(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'mobile': mobile,
      'email': email,
      'emp_code': empCode,
      'department': department,
      'is_approved': isApproved,
      'created_at': createdAt,
      'updated_at': updatedAt,
    };
  }

  bool get isApprovedStatus => isApproved == 1;
}

// ==================== TRIP EMPLOYEE SUMMARY ====================
class TripEmployeeSummary {
  final String id;
  final String name;
  final String mobile;
  final String? pickupLocation;
  final String status;
  final bool otpStartVerified;
  final bool otpEndVerified;

  TripEmployeeSummary({
    required this.id,
    required this.name,
    required this.mobile,
    this.pickupLocation,
    this.status = 'pending',
    this.otpStartVerified = false,
    this.otpEndVerified = false,
  });

  factory TripEmployeeSummary.fromJson(Map<String, dynamic> json) {
    return TripEmployeeSummary(
      id: _str(json['id']),
      name: _str(json['name']),
      mobile: _str(json['mobile']),
      pickupLocation: _strNullable(json['pickup_location']),
      status: _str(json['status']).isNotEmpty ? _str(json['status']) : 'pending',
      otpStartVerified: json['otp_start_verified'] == true || json['otp_start_verified'] == 1,
      otpEndVerified: json['otp_end_verified'] == true || json['otp_end_verified'] == 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'mobile': mobile,
      'pickup_location': pickupLocation,
      'status': status,
      'otp_start_verified': otpStartVerified,
      'otp_end_verified': otpEndVerified,
    };
  }
}

// ==================== TRIP DRIVER SUMMARY ====================
class TripDriverSummary {
  final String id;
  final String name;
  final String mobile;

  TripDriverSummary({
    required this.id,
    required this.name,
    required this.mobile,
  });

  factory TripDriverSummary.fromJson(Map<String, dynamic> json) {
    return TripDriverSummary(
      id: _str(json['id']),
      name: _str(json['name']),
      mobile: _str(json['mobile']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'mobile': mobile,
    };
  }
}

// ==================== TRIP STOP ====================
class TripStop {
  final String employeeId;
  final String employeeName;
  final String location;
  final double? lat;
  final double? lng;
  final String status;

  TripStop({
    required this.employeeId,
    required this.employeeName,
    required this.location,
    this.lat,
    this.lng,
    this.status = 'pending',
  });

  factory TripStop.fromJson(Map<String, dynamic> json) {
    return TripStop(
      employeeId: _str(json['employee_id']),
      employeeName: _str(json['employee_name']),
      location: _str(json['location']),
      lat: json['lat'] != null ? double.tryParse(json['lat'].toString()) : null,
      lng: json['lng'] != null ? double.tryParse(json['lng'].toString()) : null,
      status: _str(json['status']).isNotEmpty ? _str(json['status']) : 'pending',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'employee_id': employeeId,
      'employee_name': employeeName,
      'location': location,
      'lat': lat,
      'lng': lng,
      'status': status,
    };
  }
}

// ==================== TRIP MODEL (COMPLETE) ====================
enum TripMode { pickup, drop, unknown }
enum TripStatus { assigned, inProgress, completed, cancelled, unknown }

class TripModel {
  final String routeNo;
  final int? id;
  final TripMode mode;
  final TripStatus status;
  final String? tripDate;
  final String? scheduledTime;
  final String? startTime;
  final String? endTime;
  final String? officeName;
  final String? officeAddress;
  final double? officeLat;
  final double? officeLng;
  final String? cabNo;
  final TripDriverSummary? driver;
  final List<TripEmployeeSummary> employees;
  final List<TripStop> stops;
  final String? polyline;
  final double? totalKm;
  final int? totalDurationMin;
  final OtpInfo? startOtp;
  final OtpInfo? endOtp;
  final List<String> noShowEmployeeIds;
  final List<String> absentEmployeeIds;
  final String? cancelReason;
  final String? cancelledAt;
  final String? createdAt;
  final String? updatedAt;

  TripModel({
    required this.routeNo,
    this.id,
    this.mode = TripMode.unknown,
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
    List<TripEmployeeSummary>? employees,
    List<TripStop>? stops,
    this.polyline,
    this.totalKm,
    this.totalDurationMin,
    this.startOtp,
    this.endOtp,
    List<String>? noShowEmployeeIds,
    List<String>? absentEmployeeIds,
    this.cancelReason,
    this.cancelledAt,
    this.createdAt,
    this.updatedAt,
  })  : employees = employees ?? [],
        stops = stops ?? [],
        noShowEmployeeIds = noShowEmployeeIds ?? [],
        absentEmployeeIds = absentEmployeeIds ?? [];

  factory TripModel.fromJson(Map<String, dynamic> json) {
    final modeStr = json['mode']?.toString().toLowerCase() ?? '';
    final mode = modeStr == 'pickup' ? TripMode.pickup
        : modeStr == 'drop' ? TripMode.drop
        : TripMode.unknown;

    final statusStr = json['status']?.toString().toLowerCase() ?? '';
    final status = statusStr == 'assigned' ? TripStatus.assigned
        : statusStr == 'in_progress' ? TripStatus.inProgress
        : statusStr == 'completed' ? TripStatus.completed
        : statusStr == 'cancelled' ? TripStatus.cancelled
        : TripStatus.unknown;

    return TripModel(
      routeNo: _str(json['route_no']),
      id: json['id'] is int ? json['id'] as int : (int.tryParse(json['id']?.toString() ?? '')),
      mode: mode,
      status: status,
      tripDate: _strNullable(json['trip_date']),
      scheduledTime: _strNullable(json['scheduled_time']),
      startTime: _strNullable(json['start_time']),
      endTime: _strNullable(json['end_time']),
      officeName: _strNullable(json['office_name']),
      officeAddress: _strNullable(json['office_address']),
      officeLat: json['office_lat'] != null ? double.tryParse(json['office_lat'].toString()) : null,
      officeLng: json['office_lng'] != null ? double.tryParse(json['office_lng'].toString()) : null,
      cabNo: _strNullable(json['cab_no']),
      driver: json['driver'] != null ? TripDriverSummary.fromJson(json['driver'] as Map<String, dynamic>) : null,
      employees: json['employees'] != null
        ? List<TripEmployeeSummary>.from(
          (json['employees'] as List).map((e) => TripEmployeeSummary.fromJson(e as Map<String, dynamic>)))
        : [],
      stops: json['stops'] != null
        ? List<TripStop>.from((json['stops'] as List).map((e) => TripStop.fromJson(e as Map<String, dynamic>)))
        : [],
        polyline: _strNullable(json['polyline']),
        totalKm: json['total_km'] != null ? double.tryParse(json['total_km'].toString()) : null,
        totalDurationMin: json['total_duration_min'] is int
          ? json['total_duration_min'] as int
          : (json['total_duration_min'] != null ? int.tryParse(json['total_duration_min'].toString()) : null),
      startOtp: json['start_otp'] != null ? OtpInfo.fromJson(json['start_otp'] as Map<String, dynamic>) : null,
      endOtp: json['end_otp'] != null ? OtpInfo.fromJson(json['end_otp'] as Map<String, dynamic>) : null,
        noShowEmployeeIds: json['no_show_employee_ids'] != null
          ? List<String>.from(json['no_show_employee_ids'] as List<dynamic>)
          : [],
        absentEmployeeIds: json['absent_employee_ids'] != null
          ? List<String>.from(json['absent_employee_ids'] as List<dynamic>)
          : [],
        cancelReason: _strNullable(json['cancel_reason']),
        cancelledAt: _strNullable(json['cancelled_at']),
        createdAt: _strNullable(json['created_at']),
        updatedAt: _strNullable(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'route_no': routeNo,
      'id': id,
      'mode': mode == TripMode.pickup ? 'pickup' : mode == TripMode.drop ? 'drop' : null,
      'status': status == TripStatus.assigned ? 'assigned'
          : status == TripStatus.inProgress ? 'in_progress'
          : status == TripStatus.completed ? 'completed'
          : status == TripStatus.cancelled ? 'cancelled'
          : null,
      'trip_date': tripDate,
      'scheduled_time': scheduledTime,
      'start_time': startTime,
      'end_time': endTime,
      'office_name': officeName,
      'office_address': officeAddress,
      'office_lat': officeLat,
      'office_lng': officeLng,
      'cab_no': cabNo,
      'driver': driver?.toJson(),
      'employees': employees.map((e) => e.toJson()).toList(),
      'stops': stops.map((e) => e.toJson()).toList(),
      'polyline': polyline,
      'total_km': totalKm,
      'total_duration_min': totalDurationMin,
      'start_otp': startOtp?.toJson(),
      'end_otp': endOtp?.toJson(),
      'no_show_employee_ids': noShowEmployeeIds,
      'absent_employee_ids': absentEmployeeIds,
      'cancel_reason': cancelReason,
      'cancelled_at': cancelledAt,
      'created_at': createdAt,
      'updated_at': updatedAt,
    };
  }
}

// ==================== OTP INFO ====================
class OtpInfo {
  final String otp;
  final String expiresAt;
  final bool isVerified;

  OtpInfo({
    required this.otp,
    required this.expiresAt,
    this.isVerified = false,
  });

  factory OtpInfo.fromJson(Map<String, dynamic> json) {
    return OtpInfo(
      otp: _str(json['otp']),
      expiresAt: _str(json['expires_at']),
      isVerified: json['is_verified'] == true || json['is_verified'] == 1,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'otp': otp,
      'expires_at': expiresAt,
      'is_verified': isVerified,
    };
  }
}
