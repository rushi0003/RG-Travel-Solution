// flutter/lib/core/utils/constants.dart
//
// RG Travel Solution Ã¢â‚¬â€ Constants
//
// Ã¢Å“â€¦ Purpose:
// - Single place for UI + app constants
// - Shared enums/labels used across screens
// - Standard keys for API payloads (route_no, otp_type, etc.)
//
// NOTE:
// - Full API endpoints are in ApiConfig (core/config/api_config.dart)
// - constants.dart should not duplicate endpoints (avoid mismatch).

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class AppInfo {
  AppInfo._();

  static const String appName = 'RG Travel Solution';
  static const String companyShort = 'RG';
  static const String tagline = 'Commute Management System';

  // For PPT/Docs
  static const String projectTitle = 'RG Travel Solution';
  static const String author = 'Rushi Gund';
  static const String department =
      'AIML — Stage 1: Live Tracking, OTP & Auto-Routing';
}

class AppAssets {
  AppAssets._();

  static const String logo = 'assets/images/logo.png';
  static const bool hasBundledLogo = false;
}

class AppRoutes {
  AppRoutes._();

  // Main
  static const String login = '/login';

  // Admin
  static const String adminDashboard = '/admin/dashboard';
  static const String adminCreateGroup = '/admin/create-group';
  static const String adminLiveTrips = '/admin/live-trips';
  static const String adminDrivers = '/admin/drivers';
  static const String adminEmployees = '/admin/employees';
  static const String adminTripHistory = '/admin/trip-history';
  static const String adminLiveTracking = '/admin/live-tracking';
  static const String adminSos = '/admin/sos';
  static const String adminHelpdesk = '/admin/helpdesk';
  static const String adminNotifications = '/admin/notifications';

  // Driver
  static const String driverDashboard = '/driver/dashboard';
  static const String driverProfile = '/driver/profile';
  static const String driverAssignedTrip = '/driver/assigned-trip';
  static const String driverOtp = '/driver/otp';

  // Employee
  static const String employeeDashboard = '/employee/dashboard';
  static const String employeeMyTrip = '/employee/my-trip';
  static const String employeeTrackingView = '/employee/tracking';
}

// Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
// NOTE: AppColors and UIConstants have been REMOVED.
// Use the canonical design tokens from app_theme.dart instead:
//   Colors   Ã¢â€ â€™ AppThemeColors  (e.g. AppThemeColors.primary)
//   Spacing  Ã¢â€ â€™ AppSpacing      (e.g. AppSpacing.md)
//   Radius   Ã¢â€ â€™ AppRadius       (e.g. AppRadius.md)
//   Anim     Ã¢â€ â€™ AppAnimations   (e.g. AppAnimations.normal)
// Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

enum TripType { pickup, drop }

extension TripTypeX on TripType {
  String get label => this == TripType.pickup ? 'Pickup' : 'Drop';
  String get apiValue => this == TripType.pickup ? 'pickup' : 'drop';
}

enum TripStatus { pending, assigned, inProgress, completed, cancelled }

extension TripStatusX on TripStatus {
  String get label {
    switch (this) {
      case TripStatus.pending:
        return 'Pending';
      case TripStatus.assigned:
        return 'Assigned';
      case TripStatus.inProgress:
        return 'In Progress';
      case TripStatus.completed:
        return 'Completed';
      case TripStatus.cancelled:
        return 'Cancelled';
    }
  }

  String get apiValue {
    switch (this) {
      case TripStatus.pending:
        return 'pending';
      case TripStatus.assigned:
        return 'assigned';
      case TripStatus.inProgress:
        return 'in_progress';
      case TripStatus.completed:
        return 'completed';
      case TripStatus.cancelled:
        return 'cancelled';
    }
  }
}

enum RequestStatus { pending, approved, rejected }

extension RequestStatusX on RequestStatus {
  String get label {
    switch (this) {
      case RequestStatus.pending:
        return 'Pending';
      case RequestStatus.approved:
        return 'Approved';
      case RequestStatus.rejected:
        return 'Rejected';
    }
  }

  String get apiValue {
    switch (this) {
      case RequestStatus.pending:
        return 'pending';
      case RequestStatus.approved:
        return 'approved';
      case RequestStatus.rejected:
        return 'rejected';
    }
  }

  Color get color {
    switch (this) {
      case RequestStatus.pending:
        return AppThemeColors.warning;
      case RequestStatus.approved:
        return AppThemeColors.success;
      case RequestStatus.rejected:
        return AppThemeColors.error;
    }
  }
}

/// OTP types used in your flow
enum OtpType { start, end }

extension OtpTypeX on OtpType {
  String get label => this == OtpType.start ? 'Start OTP' : 'End OTP';
  String get apiValue => this == OtpType.start ? 'start' : 'end';
}

/// Vehicle type = group size selector
enum VehicleType { seater4, seater6 }

extension VehicleTypeX on VehicleType {
  String get label => this == VehicleType.seater4 ? '4 Seater' : '6 Seater';
  int get groupSize => this == VehicleType.seater4 ? 4 : 6;
  String get apiValue => this == VehicleType.seater4 ? '4' : '6';
}

/// Standard keys to avoid spelling mismatch in JSON payloads
class ApiKeys {
  ApiKeys._();

  // Common IDs
  static const String adminId = 'admin_id';
  static const String driverId = 'driver_id';
  static const String employeeId = 'employee_id';

  // Route/trip
  static const String routeNo =
      'route_no'; // IMPORTANT: use route_no everywhere
  static const String tripType = 'trip_type'; // pickup / drop
  static const String tripStatus = 'status';

  // OTP
  static const String otp = 'otp';
  static const String otpType = 'type'; // start / end

  // Tracking
  static const String lat = 'lat';
  static const String lng = 'lng';
  static const String timestamp = 'timestamp';

  // Grouping
  static const String groupSize = 'group_size'; // 4 or 6
  static const String employeeIds = 'employee_ids';
  static const String driverIds = 'driver_ids';
  static const String vehicleType = 'vehicle_type'; // 4 / 6
  static const String cabNo = 'cab_no';

  // History
  static const String totalKm = 'total_km';
  static const String startTime = 'start_time';
  static const String endTime = 'end_time';

  // Admin actions
  static const String reason = 'reason'; // cancel reason / notes

  // No-show
  static const String noShowEmployeeIds = 'no_show_employee_ids';
}

/// Route No format info (for UI display)
class RouteNoFormat {
  RouteNoFormat._();

  /// Your logic:
  /// 10 char route no:
  /// - first 4: year+date (YYDD)
  /// - next 4: random digits
  /// - last 2: month initials (first two letters)
  static const String description =
      '10-char Route No = first 4 (year+date), next 4 random digits, last 2 month letters';

  static const String example = '26014821FE';

  static const String note =
      'Route No is unique per trip/day and becomes invalid after trip completion.';
}
