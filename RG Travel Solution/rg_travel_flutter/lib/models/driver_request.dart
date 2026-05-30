class DriverRequest {
  final String id;
  final String name;
  final String mobile;
  final String licenseNo; // Maps from dl_no
  final String vehicleNo; // Maps from cab_no
  final String? vehicleType; // Backend sends this
  final String? homeTown; // Backend sends home_town
  final String? status; // Pending, Approved, Rejected
  final String? createdAt;

  DriverRequest({
    required this.id,
    required this.name,
    required this.mobile,
    required this.licenseNo,
    required this.vehicleNo,
    this.vehicleType,
    this.homeTown,
    this.status,
    this.createdAt,
  });

  factory DriverRequest.fromJson(Map<String, dynamic> json) {
    return DriverRequest(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      mobile: json['mobile']?.toString() ?? '',
      // Backend sends dl_no and cab_no (not license_no/vehicle_no)
      licenseNo: json['dl_no']?.toString() ?? json['license_no']?.toString() ?? '',
      vehicleNo: json['cab_no']?.toString() ?? json['vehicle_no']?.toString() ?? '',
      vehicleType: json['vehicle_type']?.toString(),
      homeTown: json['home_town']?.toString(),
      status: json['status']?.toString(),
      createdAt: json['created_at']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'mobile': mobile,
      'dl_no': licenseNo, // Send as dl_no to backend
      'cab_no': vehicleNo, // Send as cab_no to backend
      if (vehicleType != null) 'vehicle_type': vehicleType,
      if (homeTown != null) 'home_town': homeTown,
      if (status != null) 'status': status,
      if (createdAt != null) 'created_at': createdAt,
    };
  }
}
