import 'package:intl/intl.dart';

enum BillingMode {
  dateRange,
  specificTrip,
}

class BillableVehicleAssignment {
  final String driverId;
  final String driverName;
  final String driverMobile;
  final String vehicleNo;
  final String? vehicleType;

  const BillableVehicleAssignment({
    required this.driverId,
    required this.driverName,
    required this.driverMobile,
    required this.vehicleNo,
    this.vehicleType,
  });

  String get label {
    final type = (vehicleType ?? '').trim();
    if (type.isEmpty) {
      return '$vehicleNo | $driverName';
    }
    return '$vehicleNo | $driverName | $type';
  }

  factory BillableVehicleAssignment.fromJson(Map<String, dynamic> json) {
    return BillableVehicleAssignment(
      driverId: (json['driver_id'] ?? '').toString(),
      driverName: (json['driver_name'] ?? '').toString(),
      driverMobile: (json['driver_mobile'] ?? '').toString(),
      vehicleNo: (json['vehicle_no'] ?? '').toString(),
      vehicleType: json['vehicle_type']?.toString(),
    );
  }
}

class BillableTripSummary {
  final int tripId;
  final String routeNo;
  final String tripDate;
  final String scheduleTime;
  final String driverId;
  final String driverName;
  final String driverMobile;
  final String vehicleNo;
  final String status;
  final double totalKm;
  final int employeeCount;
  final int noShowCount;

  const BillableTripSummary({
    required this.tripId,
    required this.routeNo,
    required this.tripDate,
    required this.scheduleTime,
    required this.driverId,
    required this.driverName,
    required this.driverMobile,
    required this.vehicleNo,
    required this.status,
    required this.totalKm,
    required this.employeeCount,
    required this.noShowCount,
  });

  bool get isCancelled => status.trim().toLowerCase() == 'cancelled';
  int get billedEmployeeCount {
    final value = employeeCount - noShowCount;
    return value < 0 ? 0 : value;
  }

  factory BillableTripSummary.fromJson(Map<String, dynamic> json) {
    double parseDouble(dynamic value) {
      if (value is num) {
        return value.toDouble();
      }
      return double.tryParse(value?.toString() ?? '') ?? 0;
    }

    int parseInt(dynamic value) {
      if (value is int) {
        return value;
      }
      return int.tryParse(value?.toString() ?? '') ?? 0;
    }

    return BillableTripSummary(
      tripId: parseInt(json['trip_id'] ?? json['id']),
      routeNo: (json['route_no'] ?? '').toString(),
      tripDate: (json['trip_date'] ?? json['trip_day'] ?? '').toString(),
      scheduleTime: (json['schedule_time'] ?? '').toString(),
      driverId: (json['driver_id'] ?? '').toString(),
      driverName: (json['driver_name'] ?? '').toString(),
      driverMobile: (json['driver_mobile'] ?? '').toString(),
      vehicleNo: (json['vehicle_no'] ?? json['cab_no'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      totalKm: parseDouble(json['total_km']),
      employeeCount: parseInt(json['employee_count']),
      noShowCount: parseInt(json['no_show_count']),
    );
  }
}

class BillingCalculation {
  final double subtotal;
  final double gstPercent;
  final double gstAmount;
  final double advancePaid;
  final double grandTotal;
  final double payableAmount;

  const BillingCalculation({
    required this.subtotal,
    required this.gstPercent,
    required this.gstAmount,
    required this.advancePaid,
    required this.grandTotal,
    required this.payableAmount,
  });
}

class BillingDraft {
  final BillableVehicleAssignment? assignment;
  final BillingMode mode;
  final DateTime? fromDate;
  final DateTime? toDate;
  final List<BillableTripSummary> trips;
  final String companyName;
  final String companyAddress;
  final String contactPerson;
  final String clientGstNo;
  final String companyEmail;
  final String serviceType;
  final String officeAddress;
  final String rgGstNo;
  final String totalEmployees;
  final String notes;
  final String bankName;
  final String accountNumber;
  final String ifscCode;
  final String upiId;
  final double perKmAmount;
  final double advancePaid;
  final double gstPercent;

  const BillingDraft({
    required this.assignment,
    required this.mode,
    required this.fromDate,
    required this.toDate,
    required this.trips,
    required this.companyName,
    required this.companyAddress,
    required this.contactPerson,
    required this.clientGstNo,
    required this.companyEmail,
    required this.serviceType,
    required this.officeAddress,
    required this.rgGstNo,
    required this.totalEmployees,
    required this.notes,
    required this.bankName,
    required this.accountNumber,
    required this.ifscCode,
    required this.upiId,
    required this.perKmAmount,
    required this.advancePaid,
    required this.gstPercent,
  });

  List<BillableTripSummary> get includedTrips =>
      trips.where((trip) => !trip.isCancelled).toList(growable: false);

  int get totalTrips => includedTrips.length;

  double get totalKm =>
      includedTrips.fold<double>(0, (sum, trip) => sum + trip.totalKm);

  int get calculatedEmployees => includedTrips.fold<int>(
        0,
        (sum, trip) => sum + trip.billedEmployeeCount,
      );

  BillingCalculation get calculation {
    final subtotal = totalKm * perKmAmount;
    final gstAmount = subtotal * (gstPercent / 100);
    final grandTotal = subtotal + gstAmount;
    final payableAmount = grandTotal - advancePaid;
    return BillingCalculation(
      subtotal: subtotal,
      gstPercent: gstPercent,
      gstAmount: gstAmount,
      advancePaid: advancePaid,
      grandTotal: grandTotal,
      payableAmount: payableAmount < 0 ? 0 : payableAmount,
    );
  }

  String get rangeLabel {
    if (fromDate == null || toDate == null) {
      return 'Select duration';
    }
    final formatter = DateFormat('dd MMM yyyy');
    return '${formatter.format(fromDate!)} - ${formatter.format(toDate!)}';
  }
}
