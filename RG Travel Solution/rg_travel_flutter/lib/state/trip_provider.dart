// flutter/lib/state/trip_provider.dart
//
// RG Travel Solution — TripProvider (ChangeNotifier)
//
// Handles trip flow for Admin/Driver/Employee:
// - Fetch assigned trip (driver/employee)
// - Fetch trips (admin live/history)
// - OTP: employee get OTP, driver verify OTP
// - No show marking by driver
// - Emergency vehicle/driver swap request by driver
// - Live tracking polling (driver location to admin/employee)
// - Safe timers (avoid setState after dispose)
// - Route No based everywhere (NOT tripId)
//
// Dependencies (pubspec.yaml):
//   http: ^1.2.2
//   provider: ^6.1.2

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../core/storage/session_store.dart';
import '../models/trip_model.dart';

enum TripRole { admin, driver, employee }
enum OtpKind { start, end }

class TripProvider extends ChangeNotifier {
  TripProvider({required this.baseUrl});

  final String baseUrl;

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
  // ADMIN: live/history lists
  // =========================
  List<TripModel> _liveTrips = [];
  List<TripModel> get liveTrips => _liveTrips;

  List<TripModel> _historyTrips = [];
  List<TripModel> get historyTrips => _historyTrips;

  Future<void> fetchAdminLiveTrips() async {
    try {
      final res = await _get('/api/admin/trips/live');
      final list = _mapListFrom(res['data'] ?? res);
      _liveTrips = list.map((e) => TripModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<void> fetchAdminTripHistory({
    String? q,
    String? fromDate,
    String? toDate,
    int? driverId,
  }) async {
    try {
      final res = await _get('/api/v2/trips/history', queryParams: {
        if (q != null && q.trim().isNotEmpty) 'q': q.trim(),
        if (fromDate != null) 'from': fromDate,
        if (toDate != null) 'to': toDate,
        if (driverId != null) 'driver_id': driverId.toString(),
      },);
      final payload = _mapFrom(res['data'] ?? res);
      final list = _mapListFrom(payload['trips'] ?? payload);
      _historyTrips = list.map((e) => TripModel.fromJson(e)).toList();
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<bool> adminCancelTrip({required String routeNo, required String reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/trips/$routeNo/cancel', {'reason': reason});
      await fetchAdminLiveTrips();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> adminCompleteTrip({required String routeNo}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/trips/$routeNo/complete', {});
      await fetchAdminLiveTrips();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVER/EMPLOYEE: my trip
  // =========================
  TripModel? _driverAssignedTrip;
  TripModel? get driverAssignedTrip => _driverAssignedTrip;

  TripModel? _employeeMyTrip;
  TripModel? get employeeMyTrip => _employeeMyTrip;

  Future<void> fetchDriverAssignedTrip({required int driverId}) async {
    try {
      final res = await _get('/api/driver/$driverId/assigned-trip');
      final data = (res['data'] ?? res) as Map<String, dynamic>?;
      _driverAssignedTrip = data == null ? null : TripModel.fromJson(data);
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<void> fetchEmployeeMyTrip({required int employeeId}) async {
    try {
      final res = await _get('/api/employee/$employeeId/my-trip');
      final data = (res['data'] ?? res) as Map<String, dynamic>?;
      _employeeMyTrip = data == null ? null : TripModel.fromJson(data);
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  // =========================
  // EMPLOYEE: OTP GET (start/end)
  // =========================

  /// Returns: { otp: '123456', expires_at: 'ISO', route_no: '....' }
  Future<Map<String, dynamic>> employeeGetOtp({
    required int employeeId,
    required String routeNo,
    required OtpKind kind,
  }) async {
    _setBusy(true);
    _error = null;
    try {
      final res = await _get(
        '/api/employee/$employeeId/otp',
        queryParams: {
          'route_no': routeNo,
          'type': kind == OtpKind.start ? 'start' : 'end',
        },
      );
      return _mapFrom(res['data'] ?? res);
    } catch (e) {
      _setError(e);
      rethrow;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVER: OTP VERIFY (start/end)
  // =========================

  Future<bool> driverVerifyOtp({
    required int driverId,
    required String routeNo,
    required OtpKind kind,
    required String otp,
  }) async {
    _setBusy(true);
    _error = null;
    try {
      final res = await _post(
        '/api/driver/$driverId/trips/$routeNo/verify-otp',
        {
          'type': kind == OtpKind.start ? 'start' : 'end',
          'otp': otp,
        },
      );

      // Refresh assigned trip after verification
      await fetchDriverAssignedTrip(driverId: driverId);
      return (res['success'] == true) ||
          ((((res['data'] ?? <String, dynamic>{}) as Map<String, dynamic>)['verified'] == true));
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVER: START TRIP (Drop mode can start without OTP)
  // =========================
  Future<bool> driverStartTrip({
    required int driverId,
    required String routeNo,
  }) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/driver/$driverId/trips/$routeNo/start', {});
      await fetchDriverAssignedTrip(driverId: driverId);
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVER: COMPLETE TRIP (end OTP already verified OR backend validates)
  // =========================
  Future<bool> driverCompleteTrip({
    required int driverId,
    required String routeNo,
  }) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/driver/$driverId/trips/$routeNo/complete', {});
      await fetchDriverAssignedTrip(driverId: driverId);
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVER: NO-SHOW (mark employee absent for this trip)
  // =========================
  Future<bool> driverMarkNoShow({
    required int driverId,
    required String routeNo,
    required int employeeId,
    String? note,
  }) async {
    _setBusy(true);
    _error = null;
    try {
      await _post(
        '/api/driver/$driverId/trips/$routeNo/no-show',
        {
          'employee_id': employeeId,
          if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
        },
      );
      await fetchDriverAssignedTrip(driverId: driverId);
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // DRIVER: EMERGENCY VEHICLE/DRIVER SWAP REQUEST
  // =========================
  //
  // Driver can request swap; admin approves later.
  // Payload must include new driver/cab details + photo URLs (upload handled in UI separately)
  //
  Future<bool> driverEmergencySwapRequest({
    required int driverId,
    required String routeNo,
    required String newDriverName,
    required String newDriverMobile,
    required String newCabNo,
    String? photoUrl, // uploaded file URL (optional)
    String? reason,
  }) async {
    _setBusy(true);
    _error = null;
    try {
      await _post(
        '/api/driver/$driverId/trips/$routeNo/emergency-swap',
        {
          'new_driver_name': newDriverName,
          'new_driver_mobile': newDriverMobile,
          'new_cab_no': newCabNo,
          if (photoUrl != null) 'photo_url': photoUrl,
          if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
        },
      );
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // ADMIN: Emergency requests list + approve/reject
  // =========================
  List<Map<String, dynamic>> _emergencyRequests = [];
  List<Map<String, dynamic>> get emergencyRequests => _emergencyRequests;

  Future<void> fetchAdminEmergencyRequests() async {
    try {
      final res = await _get('/api/admin/emergency-requests');
      _emergencyRequests = _mapListFrom(res['data'] ?? res);
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  Future<bool> adminApproveEmergencyRequest({required String requestId}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/emergency-requests/$requestId/approve', {});
      await fetchAdminEmergencyRequests();
      await fetchAdminLiveTrips();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  Future<bool> adminRejectEmergencyRequest({required String requestId, String? reason}) async {
    _setBusy(true);
    _error = null;
    try {
      await _post('/api/admin/emergency-requests/$requestId/reject', {
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      });
      await fetchAdminEmergencyRequests();
      return true;
    } catch (e) {
      _setError(e);
      return false;
    } finally {
      _setBusy(false);
    }
  }

  // =========================
  // LIVE TRACKING (Driver sends GPS)
  // =========================

  /// Driver -> backend: send current GPS
  Future<bool> driverSendLocation({
    required int driverId,
    required String routeNo,
    required double lat,
    required double lng,
    double? speed,
    double? heading,
  }) async {
    try {
      await _post(
        '/api/driver/$driverId/trips/$routeNo/location',
        {
          'lat': lat,
          'lng': lng,
          if (speed != null) 'speed': speed,
          if (heading != null) 'heading': heading,
        },
      );
      return true;
    } catch (e) {
      // don't spam UI for tracking failures
      return false;
    }
  }

  // =========================
  // LIVE TRACKING (Admin/Employee view)
  // =========================

  /// route tracking details:
  /// {route_no, driver:{...}, polyline:'', stops:[...], latest_location:{lat,lng}, updated_at:''}
  Map<String, dynamic>? _routeTracking;
  Map<String, dynamic>? get routeTracking => _routeTracking;

  Timer? _trackingTimer;

  bool _trackingRunning = false;
  bool get trackingRunning => _trackingRunning;

  Future<void> startRouteTrackingPolling({
    required String routeNo,
    required TripRole viewerRole,
    int? employeeId,
    Duration interval = const Duration(seconds: 5),
  }) async {
    stopRouteTrackingPolling();

    _trackingRunning = true;
    notifyListeners();

    await fetchRouteTracking(routeNo: routeNo, viewerRole: viewerRole, employeeId: employeeId);

    _trackingTimer = Timer.periodic(interval, (_) async {
      try {
        await fetchRouteTracking(routeNo: routeNo, viewerRole: viewerRole, employeeId: employeeId);
      } catch (_) {}
    });
  }

  void stopRouteTrackingPolling() {
    _trackingTimer?.cancel();
    _trackingTimer = null;
    _routeTracking = null;
    _trackingRunning = false;
    notifyListeners();
  }

  Future<void> fetchRouteTracking({
    required String routeNo,
    required TripRole viewerRole,
    int? employeeId,
  }) async {
    try {
      // Role-wise endpoint (you can keep only one endpoint too)
      String path;
      if (viewerRole == TripRole.admin) {
        path = '/api/admin/trips/$routeNo/tracking';
      } else if (viewerRole == TripRole.employee) {
        path = '/api/employee/$employeeId/trips/$routeNo/tracking';
      } else {
        path = '/api/driver/trips/$routeNo/tracking';
      }

      final res = await _get(path);
      _routeTracking = _mapFrom(res['data'] ?? res);
      notifyListeners();
    } catch (e) {
      _setError(e);
    }
  }

  @override
  void dispose() {
    _trackingTimer?.cancel();
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

  Future<Map<String, String>> _headers() => SessionStore.authHeaders();

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

  Map<String, dynamic> _decode(http.Response res) {
    Map<String, dynamic> data;
    try {
      data = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {
      throw Exception('Server returned invalid response (${res.statusCode})');
    }

    if (res.statusCode >= 200 && res.statusCode < 300) {
      if (data.containsKey('success') && data['success'] == false) {
        throw Exception(data['message'] ?? 'Request failed');
      }
      return data;
    }

    final msg = data['message'] ?? 'Request failed (${res.statusCode})';
    throw Exception(msg);
  }
}
