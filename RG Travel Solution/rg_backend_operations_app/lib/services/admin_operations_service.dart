import '../models/admin_operations_snapshot.dart';
import 'admin_service.dart';

class AdminOperationsService {
  const AdminOperationsService._();

  static Future<int> _safeCount(String path) async {
    try {
      return await AdminService.countFromList(path);
    } catch (_) {
      return 0;
    }
  }

  static Future<AdminOperationsSnapshot> loadSnapshot() async {
    final results = await Future.wait<int>([
      _safeCount('/api/admin/trips/live'),
      _safeCount('/api/admin/driver-requests'),
      _safeCount('/api/admin/employee-requests'),
      _safeCount('/api/admin/driver-change-requests'),
      _safeCount('/api/admin/employee-change-requests'),
      _safeCount('/api/admin/swap-requests'),
      _safeCount('/api/admin/trip-cancel-requests'),
      _safeCount('/api/admin/absence-requests'),
      _safeCount('/api/admin/drivers'),
      _safeCount('/api/admin/employees'),
      _safeCount('/api/admin/drivers/online'),
      _safeCount('/api/admin/sos-alerts'),
      _safeCount('/api/admin/helpdesk'),
    ]);

    return AdminOperationsSnapshot(
      liveTrips: results[0],
      driverRequests: results[1],
      employeeRequests: results[2],
      driverChanges: results[3],
      employeeChanges: results[4],
      swapRequests: results[5],
      tripCancels: results[6],
      absenceRequests: results[7],
      drivers: results[8],
      employees: results[9],
      onlineDrivers: results[10],
      sos: results[11],
      helpdesk: results[12],
    );
  }
}
