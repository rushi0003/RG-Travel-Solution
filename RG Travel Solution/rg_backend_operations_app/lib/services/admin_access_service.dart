import 'admin_service.dart';

class AdminAccessService {
  const AdminAccessService._();

  static Future<List<Map<String, dynamic>>> fetchAdmins() {
    return AdminService.fetchList('/api/admin/admins');
  }

  static Future<void> createAdmin({
    required String name,
    required String mobile,
    required String password,
    String? email,
    String? officeName,
    String? officeLocation,
    String? officeAddress,
    double? officeLat,
    double? officeLng,
  }) async {
    await AdminService.post(
      '/api/admin/admins',
      body: {
        'name': name.trim(),
        'mobile': mobile.trim(),
        'password': password,
        'email': email?.trim(),
        'office_name': officeName?.trim(),
        'office_location': officeLocation?.trim(),
        'office_address': officeAddress?.trim(),
        'office_lat': officeLat,
        'office_lng': officeLng,
      },
    );
  }

  static Future<void> deleteAdmin(String adminId) async {
    await AdminService.delete('/api/admin/admins/$adminId');
  }

  static Future<void> updateAdmin({
    required String adminId,
    required String name,
    required String mobile,
    String? password,
    String? email,
    String? officeName,
    String? officeLocation,
    String? officeAddress,
    double? officeLat,
    double? officeLng,
  }) async {
    await AdminService.put(
      '/api/admin/$adminId',
      body: {
        'name': name.trim(),
        'mobile': mobile.trim(),
        if (password != null && password.trim().isNotEmpty)
          'password': password.trim(),
        'email': email?.trim(),
        'office_name': officeName?.trim(),
        'office_location': officeLocation?.trim(),
        'office_address': officeAddress?.trim(),
        'office_lat': officeLat,
        'office_lng': officeLng,
      },
    );
  }
}
