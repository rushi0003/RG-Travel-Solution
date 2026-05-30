// flutter/lib/state/admin_provider.dart
//
// RG Travel Solution — AdminProvider (ChangeNotifier)
//
// Responsibilities (Admin side):
// - Admin profile fetch/update
// - Drivers/employees lists + requests approval
// - Grouping + trip assignment
// - Live trips + history
// - Live tracking polling (drivers / trips)
//
// NOTE:
// Uses http package for API calls.
// Add in pubspec.yaml:
//   dependencies:
//     http: ^1.2.2
//     provider: ^6.1.2
//
// Base URL should be ONE place in project.
// This provider expects you pass baseUrl from config or set here.

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:rg_travel_flutter/core/storage/session_store.dart';

import '../models/admin_model.dart';
import '../models/driver_model.dart';
import '../models/employee_model.dart';
import '../models/trip_model.dart';

class AdminProvider extends ChangeNotifier {
  // =========================
  // CONFIG
  // =========================
  final String baseUrl;

  AdminProvider({required this.baseUrl});

  // =========================
  // COMMON STATE
  // =========================
  bool _busy = false;
  String? _error;

  bool get isBusy => _busy;
  String? get error => _error;

  void _setBusy(bool v) {
    _busy = v;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void _setError(Object e) {
    _error = e.toString().replaceFirst('Exception: ', '');
    notifyListeners();
  }

  List<Map<String, dynamic>> _mapListFrom(dynamic payload) {
    final rawList = payload is List
        ? payload
        : (payload is Map<String, dynamic> && payload['data'] is List
            ? payload['data'] as List
            : const <dynamic>[]);
    return rawList
        .whereType<Map<dynamic, dynamic>>()
        .map((e) => e.cast<String, dynamic>())
        .toList();
  }

  Map<String, dynamic> _mapFrom(dynamic payload) {
    if (payload is Map<String, dynamic>) return payload;
    if (payload is Map) return payload.cast<String, dynamic>();
    return <String, dynamic>{};
  }

  // =========================
  // ADMIN PROFILE
  // =========================
  AdminModel? _admin;
  AdminModel? get admin => _admin;

  Future<void> fetchAdminProfile({required int adminId}) async {
    _setBusy(true);
    _error = null;

    try {
      final res = await _get('/api/admin/profile/$adminId');
      _admin = AdminModel.fromJson((res['data'] ?? res) as Map<String, dynamic>);
    } catch (e) {
      _setError(e);
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> updateAdminProfile({
    required int adminId,
    required String name,
    required String mobile,
    required String officeName,
    required String officeAddress,
    double? officeLat,
    double? officeLng,
  }) async {
    _setBusy(true);
    _error = null;

    try {
      final body = {
        'name': name,
        'mobile': mobile,
        'office_name': officeName,
        'office_address': officeAddress,
        if (officeLat != null) 'office_lat': officeLat,
        if (officeLng != null) 'office_lng': officeLng,
      };
      final res = await _put('/api/admin/profile/$adminId', body);
      _admin = AdminModel.fromJson((res['data'] ?? res) as Map<String, dynamic>);
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVERS + REQUESTS
  // =========================
  List<DriverModel> _drivers = [];
  List<DriverModel> get drivers => _drivers;

  List<DriverModel> _driverRequests = [];
  List<DriverModel> get driverRequests => _driverRequests;

  List<DriverModel> _driverHomeTownRequests = [];
  List<DriverModel> get driverHomeTownRequests => _driverHomeTownRequests;

  Future<void> fetchDrivers() async {
    try {
      final res = await _get('/api/admin/drivers');
      final list = _mapListFrom(res['data'] ?? res);
      _drivers = list.map((e) => DriverModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<void> fetchDriverRequests() async {
    try {
      final res = await _get('/api/admin/driver-requests');
      final list = _mapListFrom(res['data'] ?? res);
      _driverRequests = list.map((e) => DriverModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  /// Driver "go home" / hometown request list
  Future<void> fetchDriverHomeTownRequests() async {
    try {
      final res = await _get('/api/admin/driver-hometown-requests');
      final list = _mapListFrom(res['data'] ?? res);
      _driverHomeTownRequests = list.map((e) => DriverModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<bool> approveDriverRequest({required int driverId}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/driver-requests/$driverId/approve', {});
      await fetchDriverRequests();
      await fetchDrivers();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> rejectDriverRequest({required int driverId, String? reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/driver-requests/$driverId/reject', {
        if (reason != null) 'reason': reason,
      });
      await fetchDriverRequests();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> approveDriverHomeTown({required int driverId}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/driver-hometown/$driverId/approve', {});
      await fetchDriverHomeTownRequests();
      await fetchDrivers();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> rejectDriverHomeTown({required int driverId, String? reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/driver-hometown/$driverId/reject', {
        if (reason != null) 'reason': reason,
      });
      await fetchDriverHomeTownRequests();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // EMPLOYEES + REQUESTS
  // =========================
  List<EmployeeModel> _employees = [];
  List<EmployeeModel> get employees => _employees;

  List<EmployeeModel> _employeeRequests = [];
  List<EmployeeModel> get employeeRequests => _employeeRequests;

  Future<void> fetchEmployees() async {
    try {
      final res = await _get('/api/admin/employees');
      final list = _mapListFrom(res['data'] ?? res);
      _employees = list.map((e) => EmployeeModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<void> fetchEmployeeRequests() async {
    try {
      final res = await _get('/api/admin/employee-requests');
      final list = _mapListFrom(res['data'] ?? res);
      _employeeRequests = list.map((e) => EmployeeModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<bool> approveEmployeeRequest({required int employeeId}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/employee-requests/$employeeId/approve', {});
      await fetchEmployeeRequests();
      await fetchEmployees();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> rejectEmployeeRequest({required int employeeId, String? reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/employee-requests/$employeeId/reject', {
        if (reason != null) 'reason': reason,
      });
      await fetchEmployeeRequests();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> approveAbsence({required int employeeId, required String date}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/absence/$employeeId/approve', {'date': date});
      await fetchEmployees();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> rejectAbsence({required int employeeId, required String date, String? reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/absence/$employeeId/reject', {'date': date, if (reason != null) 'reason': reason});
      await fetchEmployees();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // GROUPING + ASSIGN TRIP
  // =========================

  /// Created groups preview (before assign trip)
  /// Typically: [{group_id, employee_ids, stops, estimated_km}]
  List<Map<String, dynamic>> _createdGroups = [];
  List<Map<String, dynamic>> get createdGroups => _createdGroups;

  /// Create groups (auto grouping default)
  /// pickupOrDrop: "pickup" | "drop"
  /// vehicleType: 4 or 6
  /// scheduledTime: admin selected
  /// selectedEmployeeIds: if admin override, pass selected list; else empty => backend auto selects
  /// selectedDriverIds: optional list for preferred drivers
  Future<bool> createGroups({
    required String pickupOrDrop,
    required int vehicleType,
    required String scheduledTime,
    List<int> selectedEmployeeIds = const [],
    List<int> selectedDriverIds = const [],
    bool adminOverride = false,
  }) async {
    _setBusy(true);
    _error = null;

    try {
      final body = {
        // legacy payload
        'mode': pickupOrDrop,
        'vehicle_type': vehicleType,
        'scheduled_time': scheduledTime,
        'admin_override': adminOverride,
        'employee_ids': selectedEmployeeIds,
        'preferred_driver_ids': selectedDriverIds,
        // v2 payload compatibility
        'admin_id': (_admin?.id ?? '').toString(),
        'trip_type': pickupOrDrop,
        'selected_time': scheduledTime,
        'vehicle_types': [vehicleType],
        'driver_ids': selectedDriverIds,
      };

      Map<String, dynamic>? res;
      final paths = [
        '/api/admin/groups/create',
        '/api/v2/trips/create-groups',
      ];
      Object? lastError;
      for (final p in paths) {
        try {
          res = await _post(p, body);
          break;
        } catch (e) {
          lastError = e;
        }
      }
      if (res == null) {
        throw Exception(lastError?.toString() ?? 'Create groups endpoint unavailable');
      }

      final payload = res['data'];
      final dynamic listLike = (payload is Map && payload['groups'] is List)
          ? payload['groups']
          : (payload is List
              ? payload
              : (res['groups'] is List ? res['groups'] : const <dynamic>[]));
      final list = listLike as List<dynamic>;
      _createdGroups = list.map((e) => (e as Map).cast<String, dynamic>()).toList();
      notifyListeners();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  /// Assign trip for a group:
  /// Backend should:
  /// - generate unique route_no (10 char)
  /// - assign driver + cab
  /// - compute multi-stop route (google)
  /// - generate OTP start/end
  /// - save trip + km
  Future<bool> assignTripForGroup({
    required String groupId,
    required int driverId,
    required String cabNo,
    required String pickupOrDrop,
    required String scheduledTime,
  }) async {
    _setBusy(true);
    _error = null;

    try {
      await _post('/api/admin/trips/assign', {
        'group_id': groupId,
        'driver_id': driverId,
        'cab_no': cabNo,
        'mode': pickupOrDrop,
        'scheduled_time': scheduledTime,
      });

      // After assigning, refresh live trips
      await fetchLiveTrips();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  void clearCreatedGroups() {
    _createdGroups = [];
    notifyListeners();
  }

  // =========================
  // LIVE TRIPS + HISTORY
  // =========================
  List<TripModel> _liveTrips = [];
  List<TripModel> get liveTrips => _liveTrips;

  List<TripModel> _tripHistory = [];
  List<TripModel> get tripHistory => _tripHistory;

  Future<void> fetchLiveTrips() async {
    try {
      final res = await _get('/api/admin/trips/live');
      final list = _mapListFrom(res['data'] ?? res);
      _liveTrips = list.map((e) => TripModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<void> fetchTripHistory({
    String? query,
    String? fromDate,
    String? toDate,
    int? driverId,
  }) async {
    try {
      final res = await _get('/api/admin/trips/history', queryParams: {
        if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
        if (fromDate != null) 'from': fromDate,
        if (toDate != null) 'to': toDate,
        if (driverId != null) 'driver_id': driverId.toString(),
      });

      final payload = _mapFrom(res['data'] ?? res);
      final list = _mapListFrom(payload['trips'] ?? payload);
      _tripHistory = list.map((e) => TripModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<bool> cancelTrip({required String routeNo, required String reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/trips/$routeNo/cancel', {'reason': reason});
      await fetchLiveTrips();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> completeTrip({required String routeNo}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/trips/$routeNo/complete', {});
      await fetchLiveTrips();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // LIVE TRACKING (Polling)
  // =========================

  /// Latest locations for drivers
  /// format: {"driver_id":..., "lat":..., "lng":..., "updated_at":...}
  List<Map<String, dynamic>> _onlineDrivers = [];
  List<Map<String, dynamic>> get onlineDrivers => _onlineDrivers;

  /// Trip tracking detail for a route
  Map<String, dynamic>? _tripTracking;
  Map<String, dynamic>? get tripTracking => _tripTracking;

  Timer? _driversPollTimer;
  Timer? _tripPollTimer;

  bool _trackingEnabled = false;
  bool get trackingEnabled => _trackingEnabled;

  Future<void> startDriversPolling({Duration interval = const Duration(seconds: 5)}) async {
    stopDriversPolling();
    _trackingEnabled = true;
    notifyListeners();

    // immediate fetch
    await fetchOnlineDrivers();

    _driversPollTimer = Timer.periodic(interval, (_) async {
      try {
        await fetchOnlineDrivers();
      } catch (_) {}
    });
  }

  void stopDriversPolling() {
    _driversPollTimer?.cancel();
    _driversPollTimer = null;
    _trackingEnabled = false;
    notifyListeners();
  }

  Future<void> fetchOnlineDrivers() async {
    try {
      final res = await _get('/api/admin/drivers/online');
      final payload = _mapFrom(res['data'] ?? res);
      _onlineDrivers = _mapListFrom(payload['online_drivers'] ?? payload);
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<void> startTripTrackingPolling({
    required String routeNo,
    Duration interval = const Duration(seconds: 5),
  }) async {
    stopTripTrackingPolling();

    // immediate fetch
    await fetchTripTracking(routeNo: routeNo);

    _tripPollTimer = Timer.periodic(interval, (_) async {
      try {
        await fetchTripTracking(routeNo: routeNo);
      } catch (_) {}
    });
  }

  void stopTripTrackingPolling() {
    _tripPollTimer?.cancel();
    _tripPollTimer = null;
    _tripTracking = null;
    notifyListeners();
  }

  Future<void> fetchTripTracking({required String routeNo}) async {
    try {
      final res = await _get('/api/admin/trips/$routeNo/tracking');
      _tripTracking = _mapFrom(res['data'] ?? res);
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  // Call this from screen dispose
  @override
  void dispose() {
    _driversPollTimer?.cancel();
    _tripPollTimer?.cancel();
    super.dispose();
  }

  // =========================
  // HTTP HELPERS
  // =========================

  Uri _uri(String path, {Map<String, String>? queryParams}) {
    final base = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$base$p').replace(queryParameters: queryParams);
  }

  Future<Map<String, dynamic>> _get(String path, {Map<String, String>? queryParams}) async {
    final u = _uri(path, queryParams: queryParams);
    final res = await http.get(u, headers: await _headers());
    return _decode(res);
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final u = _uri(path);
    final res = await http.post(u, headers: await _headers(), body: jsonEncode(body));
    return _decode(res);
  }

  Future<Map<String, dynamic>> _put(String path, Map<String, dynamic> body) async {
    final u = _uri(path);
    final res = await http.put(u, headers: await _headers(), body: jsonEncode(body));
    return _decode(res);
  }

  Future<Map<String, String>> _headers() => SessionStore.authHeaders();

  Map<String, dynamic> _decode(http.Response res) {
    // handle non-json
    Map<String, dynamic> data;
    try {
      data = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw Exception('Server returned invalid response (${res.statusCode})');
    }

    if (res.statusCode >= 200 && res.statusCode < 300) {
      // many APIs respond: {success:true, data:{...}}
      if (data.containsKey('success') && data['success'] == false) {
        throw Exception(data['message'] ?? 'Request failed');
      }
      return data;
    }

    // error
    final msg = data['message'] ?? 'Request failed (${res.statusCode})';
    throw Exception(msg);
  }
}
