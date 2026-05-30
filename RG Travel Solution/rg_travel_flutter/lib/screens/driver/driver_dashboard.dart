// flutter/lib/screen/driver/driver_dashboard.dart
//
// RG Travel Solution — Driver Dashboard
// - Assigned trip view + no-show + OTP start/end
// - Live GPS ping to backend (safe timers to avoid setState-after-dispose)
// - Profile drawer + change request
// - Trip history link (basic)
//
// IMPORTANT:
//  - Web: baseUrl should be http://127.0.0.1:5000
//  - Android Emulator: baseUrl should be http://10.0.2.2:5000

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geocoding/geocoding.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/storage/session_store.dart';
import '../../core/theme/app_theme.dart';
import '../../screens/help_desk_screen.dart';
import '../../services/driver_service.dart';
import '../../services/location_service.dart';
import '../../services/socket_service.dart';
import '../../widgets/common/map_coordinate_picker_sheet.dart';
import '../../widgets/common/rg_card.dart';
import '../../widgets/tracking/driver_tracking_health_view.dart';
import 'driver_emergency_swap_screen.dart';
import 'driver_history_screen.dart';

// ... (existing imports)

class DriverDashboard extends StatefulWidget {
  const DriverDashboard({
    super.key,
    required this.driverId,
    this.baseUrl,
  });

  final String driverId;
  final String? baseUrl;

  @override
  State<DriverDashboard> createState() => _DriverDashboardState();
}

class _DriverDashboardState extends State<DriverDashboard> {
  // ----------------------------
  // Base URL
  // ----------------------------
  final TextEditingController _baseUrlCtrl = TextEditingController();

  // ----------------------------
  // Timers
  // ----------------------------
  Timer? _pollTripTimer;
  Timer? _unlockTickTimer;

  final Duration _tripPollEvery = const Duration(seconds: 6);

  // ----------------------------
  // UI state
  // ----------------------------
  bool _isOnline = false; // New: Online/Offline status
  bool _socketConnected = false;
  DateTime? _lastLocationUploadAt;
  String? _trackingHealthMessage;
  bool _trackingHealthError = false;
  int? _lastUploadServerCode;

  // ----------------------------
  // Data
  // ----------------------------
  Map<String, dynamic>? _profile;
  Map<String, dynamic>? _assignedTrip;
  List<Map<String, dynamic>> _assignedTrips = const [];
  Map<String, dynamic>? _goHomeRequest;
  List<Map<String, dynamic>> _companies = const [];
  String? _selectedAdminId;
  bool _switchingCompany = false;

  final SocketService _socketService = SocketService();

  Map<String, dynamic>? get _primaryAssignedTrip =>
      _assignedTrips.isNotEmpty ? _assignedTrips.first : _assignedTrip;

  // ----------------------------
  // Profile change request controllers
  // ----------------------------
  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _dlCtrl = TextEditingController();
  final _cabCtrl = TextEditingController();
  final _homeCtrl = TextEditingController();
  final _goHomeRequestCtrl = TextEditingController();
  Timer? _profileAddressDebounce;
  bool _isResolvingProfileAddress = false;
  String? _profileAddressResolveNote;
  double? _profileHomeLat;
  double? _profileHomeLng;
  StreamSubscription<bool>? _locationConnectionSub;
  StreamSubscription<Map<String, dynamic>>? _uploadStatusSub;

  @override
  void initState() {
    super.initState();
    if (widget.baseUrl != null) {
      DriverService.setBaseUrl(widget.baseUrl!);
    }
    _baseUrlCtrl.text = DriverService.baseUrl;
    _startUnlockTicker();
    _boot();
  }

  @override
  void dispose() {
    _pollTripTimer?.cancel();
    _unlockTickTimer?.cancel();
    _socketService.dispose();
    LocationService().stopBroadcasting(); // Stop tracking when leaving screen
    _locationConnectionSub?.cancel();
    _uploadStatusSub?.cancel();

    _baseUrlCtrl.dispose();
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _dlCtrl.dispose();
    _cabCtrl.dispose();
    _homeCtrl.dispose();
    _goHomeRequestCtrl.dispose();
    _profileAddressDebounce?.cancel();
    super.dispose();
  }

  // Need to add imports at top of file, doing that in a separate block or manually via replace.
  // I will assume I can add imports.

  void safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  void toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  // ----------------------------
  // Boot + polling
  // ----------------------------
  Future<void> _boot() async {
    try {
      final token = await SessionStore.getToken();
      if (token != null) {
        LocationService().initialize(token);
        _attachLocationObservers();
        _socketService.initSocket(token);
        _socketService.onTripAssigned((_) {
          if (mounted) _loadAssignedTrip(silent: true);
        });
        _socketService.onTripUpdated((_) {
          if (mounted) _loadAssignedTrip(silent: true);
        });
      }

      await _loadCompanies();
      await _loadProfile();
      await _loadAssignedTrip();
      await _loadGoHomeRequestStatus();
      _startTimers();
    } catch (e) {
      toast('Load failed: $e');
    }
  }

  void _attachLocationObservers() {
    _locationConnectionSub?.cancel();
    _uploadStatusSub?.cancel();

    _locationConnectionSub =
        LocationService().connectionStatusStream.listen((connected) {
      if (!mounted) return;
      safeSetState(() {
        _socketConnected = connected;
        if (!connected && _isOnline) {
          _trackingHealthMessage = 'Realtime socket disconnected. Retrying...';
          _trackingHealthError = true;
        }
      });
    });

    _uploadStatusSub = LocationService().uploadStatusStream.listen((event) {
      if (!mounted) return;
      safeSetState(() {
        final ok = event['ok'] == true;
        final serverCode = event['serverCode'];
        if (serverCode is num) {
          _lastUploadServerCode = serverCode.toInt();
        }
        if (ok) {
          _lastLocationUploadAt = DateTime.now();
          _trackingHealthMessage =
              'Last sync ${_timeAgo(_lastLocationUploadAt!)}';
          _trackingHealthError = false;
        } else {
          _trackingHealthMessage =
              (event['error'] ?? 'Location upload retrying...').toString();
          _trackingHealthError = true;
        }
      });
    });
  }

  void _startTimers() {
    _pollTripTimer?.cancel();

    _pollTripTimer = Timer.periodic(_tripPollEvery, (_) async {
      await _loadAssignedTrip(silent: true);
      await _loadGoHomeRequestStatus(silent: true);
    });
  }

  void _startUnlockTicker() {
    _unlockTickTimer?.cancel();
    _unlockTickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      safeSetState(() {});
    });
  }

  // ----------------------------
  // API Calls (via DriverService)
  // ----------------------------
  Future<void> _loadProfile() async {
    try {
      final data = await DriverService.getDriverProfile(
        widget.driverId,
        adminId: _selectedAdminId,
      );
      if (data.isEmpty) {
        return;
      }

      safeSetState(() {
        _profile = data;
        final companies = (data['companies'] is List)
            ? (data['companies'] as List)
                .whereType<Map<dynamic, dynamic>>()
                .map((e) => e.cast<String, dynamic>())
                .toList()
            : _companies;
        _companies = companies;
        final selectedAdminId =
            (data['selected_admin_id'] ?? _selectedAdminId)?.toString().trim();
        if (selectedAdminId != null && selectedAdminId.isNotEmpty) {
          _selectedAdminId = selectedAdminId;
        }
        final savedHomeAddress = _currentDriverHomeAddress(profile: data);

        // preload request fields
        _nameCtrl.text = (data['name'] ?? '').toString();
        _mobileCtrl.text = (data['mobile'] ?? '').toString();
        _dlCtrl.text = (data['dl_no'] ?? '').toString();
        _cabCtrl.text = (data['cab_no'] ?? '').toString();
        _homeCtrl.text = savedHomeAddress;
        _goHomeRequestCtrl.text = savedHomeAddress;
        _profileHomeLat = _asDouble(data['home_lat'] ?? data['hometown_lat']);
        _profileHomeLng = _asDouble(data['home_lng'] ?? data['hometown_lng']);
      });
      await SessionStore.setSelectedAdminId(_selectedAdminId);
    } catch (e) {
      // Keep dashboard usable even if profile endpoint has schema mismatch.
      debugPrint('Profile load error (non-fatal): $e');
    }
  }

  Future<void> _loadAssignedTrip({bool silent = false}) async {
    try {
      final tripList = await DriverService.getMyTrips(
        widget.driverId,
        adminId: _selectedAdminId,
      );
      final assignedTrip = await DriverService.getAssignedTrip(
        widget.driverId,
        adminId: _selectedAdminId,
      );
      final mergedTrips = tripList.isNotEmpty
          ? tripList.map((trip) => <String, dynamic>{...trip}).toList()
          : <Map<String, dynamic>>[];

      if (assignedTrip != null) {
        final assignedId =
            (assignedTrip['id'] ?? assignedTrip['trip_id'])?.toString().trim();
        final assignedRouteNo =
            (assignedTrip['route_no'] ?? '').toString().trim();
        final matchIndex = mergedTrips.indexWhere((trip) {
          final tripId =
              (trip['id'] ?? trip['trip_id'])?.toString().trim() ?? '';
          final routeNo = (trip['route_no'] ?? '').toString().trim();
          final idMatches = assignedId != null &&
              assignedId.isNotEmpty &&
              tripId == assignedId;
          final routeMatches =
              assignedRouteNo.isNotEmpty && routeNo == assignedRouteNo;
          return idMatches || routeMatches;
        });

        if (matchIndex >= 0) {
          mergedTrips[matchIndex] = {
            ...mergedTrips[matchIndex],
            ...assignedTrip,
          };
        } else {
          mergedTrips.insert(0, assignedTrip);
        }
      }

      final data =
          assignedTrip ?? (mergedTrips.isNotEmpty ? mergedTrips.first : null);

      safeSetState(() {
        _assignedTrip = data;
        _assignedTrips = mergedTrips.isNotEmpty
            ? mergedTrips
            : (data == null ? const [] : [data]);
        // Fallback hydration for drawer profile when profile API is unavailable.
        if (data != null) {
          final existing = _profile ?? <String, dynamic>{};
          final fallbackProfile = <String, dynamic>{
            ...existing,
            'name': (existing['name']?.toString().trim().isNotEmpty ?? false)
                ? existing['name']
                : (data['driver_name'] ?? existing['name'] ?? 'Driver'),
            'mobile':
                (existing['mobile']?.toString().trim().isNotEmpty ?? false)
                    ? existing['mobile']
                    : (data['driver_mobile'] ??
                        data['mobile'] ??
                        existing['mobile'] ??
                        '—'),
            'cab_no': (data['cab_no']?.toString().trim().isNotEmpty ?? false)
                ? data['cab_no']
                : ((data['vehicle_no']?.toString().trim().isNotEmpty ?? false)
                    ? data['vehicle_no']
                    : (existing['cab_no'] ?? '—')),
            'vehicle_no':
                (data['vehicle_no']?.toString().trim().isNotEmpty ?? false)
                    ? data['vehicle_no']
                    : (data['cab_no'] ?? existing['vehicle_no'] ?? '—'),
            'hometown': existing['hometown'] ??
                existing['home_town'] ??
                data['hometown'] ??
                data['home_town'] ??
                '—',
          };
          _profile = fallbackProfile;

          final tripGoHome = data['go_home_request'];
          if (tripGoHome is Map) {
            _goHomeRequest = tripGoHome.cast<String, dynamic>();
          } else {
            final tripStatus =
                (data['go_home_request_status'] ?? '').toString().trim();
            final tripTown = (data['go_home_requested_home_town'] ??
                    data['requested_home_town'] ??
                    data['home_town'] ??
                    '')
                .toString()
                .trim();
            if (tripStatus.isNotEmpty || tripTown.isNotEmpty) {
              _goHomeRequest = {
                ...?_goHomeRequest,
                if (tripStatus.isNotEmpty) 'status': tripStatus,
                if (tripTown.isNotEmpty) 'requested_home_town': tripTown,
                'updated_at':
                    (data['go_home_request_updated_at'] ?? '').toString(),
              };
            }
          }
        }
      });

      // Auto-resume tracking if trip is active
      if (data != null) {
        final status = (data['status'] ?? '').toString().toLowerCase();
        final routeNo = (data['route_no'] ?? '').toString();
        // If status is 'in_progress', 'live', 'started' etc.
        if ((status == 'in_progress' ||
                status == 'live' ||
                status == 'started') &&
            routeNo.isNotEmpty) {
          // Ensure tracking is on. startBroadcasting checks _isBroadcasting internally so safe to call.
          // However, startBroadcasting is async. checking isConnected or similar might be good.
          // For now, simply calling it is robust enough as it's idempotent-ish (checks flag).
          unawaited(LocationService().startBroadcasting(routeNo: routeNo));
          if (!_isOnline) {
            safeSetState(() => _isOnline = true);
          }
        } else {
          // If completed or assigned (not started), ensure OFF?
          // Maybe safe to leave OFF. But user might have toggled ON manually?
          // Let's rely on manual toggle + auto-start hooks.
          // If we force OFF here, we might kill manual debug sessions.
          // But for production:
          if (status == 'completed' || status == 'cancelled') {
            LocationService().stopBroadcasting();
            if (_isOnline) safeSetState(() => _isOnline = false);
          }
        }
      }
    } catch (e) {
      if (!silent) toast('Assigned trip load failed: $e');
    }
  }

  Future<void> _loadGoHomeRequestStatus({bool silent = false}) async {
    try {
      final token = await SessionStore.getToken();
      final data = await DriverService.getHometownRequestStatus(
        widget.driverId,
        token: token,
      );
      if (!mounted) return;
      safeSetState(() {
        _goHomeRequest = data;
        final profileHomeAddress = _currentDriverHomeAddress();
        if (profileHomeAddress.isNotEmpty) {
          _goHomeRequestCtrl.text = profileHomeAddress;
        }
      });
    } catch (e) {
      if (!silent) {
        debugPrint('Go-home status load error: $e');
      }
    }
  }

  Future<void> _markNoShow(int tripId, int employeeId) async {
    try {
      await DriverService.markNoShow(
        widget.driverId,
        tripId: tripId,
        employeeId: employeeId,
      );
      toast('Marked no-show');
      await _loadAssignedTrip(silent: true);
    } catch (e) {
      toast('No-show failed: $e');
    }
  }

  Future<void> _verifyOtp(
    int tripId,
    String otpType,
    String otp, {
    int? employeeId,
    String? employeeName,
  }) async {
    try {
      await DriverService.verifyTripOtp(
        tripId,
        type: otpType,
        otp: otp,
        driverId: widget.driverId,
        employeeId: employeeId,
      );
      if (employeeId != null) {
        final who = (employeeName ?? 'Employee').trim();
        toast('$who OTP verified (${otpType.toUpperCase()})');
      } else {
        toast("OTP verified: Trip ${otpType == 'start' ? 'Started' : 'Ended'}");
      }

      // Auto-tracking only for trip-level OTP verification.
      if (employeeId == null) {
        if (otpType == 'start') {
          final routeNo = _primaryAssignedTrip?['route_no']?.toString() ?? '';
          if (routeNo.isNotEmpty) {
            await LocationService().startBroadcasting(routeNo: routeNo);
          }
        } else if (otpType == 'end') {
          LocationService().stopBroadcasting();
        }
      }

      await _loadAssignedTrip(silent: true);
    } catch (e) {
      toast('OTP verify failed: $e');
    }
  }

  bool _canVerifyEmployeeStartOtp(String tripType, String status, bool noShow) {
    if (noShow) return false;
    if (status != 'assigned' && status != 'created' && status != 'active') {
      return false;
    }
    // Fallback: if trip_type missing from payload, allow start-otp in pre-start phase.
    return tripType == 'pickup' || tripType.isEmpty;
  }

  bool _canVerifyEmployeeEndOtp(String tripType, String status, bool noShow) {
    if (noShow) return false;
    if (status != 'started' && status != 'in_progress' && status != 'live') {
      return false;
    }
    // Fallback: if trip_type missing from payload, allow end-otp in live phase.
    return tripType == 'drop' || tripType.isEmpty;
  }

  bool _asBool(dynamic v) {
    if (v is bool) return v;
    if (v is num) return v != 0;
    final s = (v ?? '').toString().trim().toLowerCase();
    return s == '1' || s == 'true' || s == 'yes';
  }

  String _normalizePhone(String raw) {
    final input = raw.trim();
    if (input.isEmpty) return '';
    final cleaned = input.replaceAll(RegExp(r'[^0-9+]'), '');
    return cleaned;
  }

  Future<void> _callEmployee(String mobile, {String? name}) async {
    final phone = _normalizePhone(mobile);
    if (phone.isEmpty) {
      toast('Invalid mobile number');
      return;
    }

    final uri = Uri(scheme: 'tel', path: phone);
    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok) {
        toast('Could not open dialer');
      }
    } catch (_) {
      toast("Call failed for ${name ?? 'employee'}");
    }
  }

  Future<void> _openEmployeeNavigation(String address, {String? name}) async {
    final dest = address.trim();
    if (dest.isEmpty || dest == 'â€”' || dest == '—') {
      toast('Employee location not available');
      return;
    }

    final url = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=${Uri.encodeComponent(dest)}&travelmode=driving',
    );
    try {
      final ok = await launchUrl(url, mode: LaunchMode.externalApplication);
      if (!ok) {
        toast('Could not open navigation');
      }
    } catch (_) {
      toast("Navigation failed for ${name ?? 'employee'}");
    }
  }

  Future<void> _openOtpDialogAndVerify({
    required int tripId,
    required int employeeId,
    required String employeeName,
    required String otpType,
  }) async {
    final ctrl = TextEditingController();
    final otp = await showDialog<String>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: AppThemeColors.surface,
          title: Text(
            otpType == 'start'
                ? 'Start OTP - $employeeName'
                : 'End OTP - $employeeName',
            style: const TextStyle(color: AppThemeColors.textPrimary),
          ),
          content: TextField(
            controller: ctrl,
            autofocus: true,
            keyboardType: TextInputType.number,
            style: const TextStyle(color: AppThemeColors.textPrimary),
            maxLength: 6,
            decoration: InputDecoration(
              hintText: 'Enter 6-digit OTP',
              hintStyle: TextStyle(
                  color: AppThemeColors.textPrimary.withValues(alpha: 0.45)),
              counterStyle: TextStyle(
                  color: AppThemeColors.textPrimary.withValues(alpha: 0.6)),
              filled: true,
              fillColor: AppThemeColors.textPrimary.withValues(alpha: 0.07),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
              child: const Text('Verify'),
            ),
          ],
        );
      },
    );
    ctrl.dispose();

    final entered = (otp ?? '').trim();
    if (entered.isEmpty) return;
    await _verifyOtp(
      tripId,
      otpType,
      entered,
      employeeId: employeeId,
      employeeName: employeeName,
    );
  }

  Future<void> _sendProfileChangeRequest() async {
    try {
      await DriverService.requestProfileChange(
        widget.driverId,
        name: _nameCtrl.text.trim(),
        mobile: _mobileCtrl.text.trim(),
        dlNo: _dlCtrl.text.trim(),
        cabNo: _cabCtrl.text.trim(),
        homeTown: _homeCtrl.text.trim(),
        homeLat: _profileHomeLat,
        homeLng: _profileHomeLng,
      );
      toast('Request sent');
    } catch (e) {
      toast('Request failed: $e');
    }
  }

  double? _asDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  String _profileCoordLabel() {
    if (_profileHomeLat == null || _profileHomeLng == null) {
      return 'No map point selected';
    }
    return '${_profileHomeLat!.toStringAsFixed(6)}, ${_profileHomeLng!.toStringAsFixed(6)}';
  }

  Future<void> _openDriverProfileMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Update Hometown Location',
        addressHint: _homeCtrl.text.trim(),
        initialLat: _profileHomeLat,
        initialLng: _profileHomeLng,
      ),
    );
    if (selected == null || !mounted) return;
    safeSetState(() {
      _profileHomeLat = selected.latitude;
      _profileHomeLng = selected.longitude;
      _profileAddressResolveNote = 'Map location selected';
    });
  }

  void _onDriverProfileAddressChanged(String value) {
    _profileAddressDebounce?.cancel();
    final address = value.trim();
    if (address.length < 5) {
      safeSetState(() {
        _profileAddressResolveNote = null;
      });
      return;
    }
    _profileAddressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveDriverProfileAddress(address);
    });
  }

  Future<void> _autoResolveDriverProfileAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    safeSetState(() {
      _isResolvingProfileAddress = true;
      _profileAddressResolveNote = 'Resolving address on map...';
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final loc = locations.first;
        safeSetState(() {
          _profileHomeLat = loc.latitude;
          _profileHomeLng = loc.longitude;
          _profileAddressResolveNote = 'Auto-centered from typed address';
        });
      } else {
        safeSetState(() {
          _profileAddressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      safeSetState(() {
        _profileAddressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (mounted) {
        safeSetState(() {
          _isResolvingProfileAddress = false;
        });
      }
    }
  }

  Future<void> _loadCompanies() async {
    try {
      final token = await SessionStore.getToken();
      final data = await DriverService.getDriverCompanies(
        widget.driverId,
        token: token,
      );
      if (!mounted) return;
      final companies = (data['companies'] is List)
          ? (data['companies'] as List)
              .whereType<Map<dynamic, dynamic>>()
              .map((e) => e.cast<String, dynamic>())
              .toList()
          : <Map<String, dynamic>>[];
      final selectedAdminId =
          (data['selected_admin_id'] ?? await SessionStore.getSelectedAdminId())
              ?.toString()
              .trim();
      safeSetState(() {
        _companies = companies;
        _selectedAdminId = (selectedAdminId?.isNotEmpty ?? false)
            ? selectedAdminId
            : _selectedAdminId;
      });
      await SessionStore.setSelectedAdminId(_selectedAdminId);
    } catch (e) {
      debugPrint('Company load error (non-fatal): $e');
    }
  }

  Future<void> _switchCompany(String? adminId) async {
    final target = (adminId ?? '').trim();
    if (target.isEmpty || target == _selectedAdminId || _switchingCompany) {
      return;
    }
    safeSetState(() => _switchingCompany = true);
    try {
      final token = await SessionStore.getToken();
      final data = await DriverService.switchDriverCompany(
        widget.driverId,
        adminId: target,
        token: token,
      );
      final companies = (data['companies'] is List)
          ? (data['companies'] as List)
              .whereType<Map<dynamic, dynamic>>()
              .map((e) => e.cast<String, dynamic>())
              .toList()
          : _companies;
      final selectedAdminId =
          (data['selected_admin_id'] ?? target).toString().trim();
      await SessionStore.setSelectedAdminId(selectedAdminId);
      safeSetState(() {
        _companies = companies;
        _selectedAdminId = selectedAdminId;
        _assignedTrip = null;
        _assignedTrips = const [];
      });
      await _loadProfile();
      await _loadAssignedTrip();
      toast('Company switched');
    } catch (e) {
      toast('Company switch failed: $e');
    } finally {
      if (mounted) {
        safeSetState(() => _switchingCompany = false);
      }
    }
  }

  Future<void> _sendSwapRequest(int tripId) async {
    // Navigate to the full screen swap form
    await Navigator.push(
      context,
      MaterialPageRoute<void>(
        builder: (_) => DriverEmergencySwapScreen(
          driverId: widget.driverId,
          tripId: tripId,
        ),
      ),
    );
  }

  Future<void> _sendTripCancelRequest(
    int tripId, {
    String currentStatus = '',
  }) async {
    final status = currentStatus.trim().toLowerCase();
    if (status == 'pending') {
      toast('Trip cancel request already pending with admin');
      return;
    }

    final reasonCtrl = TextEditingController();
    final okPressed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppThemeColors.background,
        title: const Text(
          'Request Trip Cancel',
          style: TextStyle(color: AppThemeColors.textPrimary),
        ),
        content: _tf(
          reasonCtrl,
          'Reason for cancel request',
          maxLines: 3,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Close'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Send Request'),
          ),
        ],
      ),
    );

    if (okPressed == true) {
      final reason = reasonCtrl.text.trim();
      if (reason.length < 3) {
        toast('Reason required (min 3 chars)');
      } else {
        try {
          await DriverService.createTripCancelRequest(
            widget.driverId,
            tripId: tripId,
            reason: reason,
          );
          toast('Trip cancel request sent to admin');
          await _loadAssignedTrip(silent: true);
        } catch (e) {
          toast('Trip cancel request failed: $e');
        }
      }
    }
    reasonCtrl.dispose();
  }

  Future<void> _sendGoHomeRequest() async {
    if (_isGoHomeRequestLocked()) {
      toast(
        'Existing go home request is active. Wait for completion or rejection.',
      );
      return;
    }
    final hometown = _currentDriverHomeAddress();
    if (hometown.isEmpty) {
      toast('Driver home address not found in profile');
      return;
    }
    try {
      final token = await SessionStore.getToken();
      await DriverService.requestHometownChange(
        widget.driverId,
        newHometown: hometown,
        token: token,
      );
      toast('Go home request sent to admin');
      if (mounted) {
        safeSetState(() {
          _homeCtrl.text = hometown;
          _profile = {
            ...?_profile,
            'hometown': hometown,
            'home_address': hometown,
          };
          _goHomeRequest = {
            ...?_goHomeRequest,
            'requested_home_town': hometown,
            'home_address': hometown,
            'status': 'pending',
          };
        });
      }
      await _loadGoHomeRequestStatus(silent: true);
    } catch (e) {
      toast('Go home request failed: $e');
    }
  }

  Drawer _driverDrawer(Map<String, dynamic>? profile) {
    final name =
        (profile?['name'] ?? _primaryAssignedTrip?['driver_name'] ?? 'Driver')
            .toString();
    final mobile =
        (profile?['mobile'] ?? _primaryAssignedTrip?['driver_mobile'] ?? '-')
            .toString();
    final cab = (_primaryAssignedTrip?['cab_no'] ??
            _primaryAssignedTrip?['vehicle_no'] ??
            profile?['cab_no'] ??
            profile?['vehicle_no'] ??
            '-')
        .toString();
    final home = (profile?['hometown'] ??
            profile?['home_town'] ??
            _primaryAssignedTrip?['hometown'] ??
            _primaryAssignedTrip?['home_town'] ??
            '-')
        .toString();

    return Drawer(
      backgroundColor: AppThemeColors.background,
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            Row(
              children: [
                Container(
                  height: 56,
                  width: 56,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    gradient: const LinearGradient(
                      colors: [AppThemeColors.primary, AppThemeColors.infoDark],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppThemeColors.primary.withValues(alpha: 0.18),
                        blurRadius: 16,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.person,
                      color: AppThemeColors.textPrimary),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          color: AppThemeColors.textPrimary,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        mobile,
                        style: TextStyle(
                          color: AppThemeColors.textPrimary
                              .withValues(alpha: 0.65),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _drawerInfo('Cab', cab),
            _drawerInfo('Hometown', home),
            if (_companies.isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppThemeColors.textPrimary.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                      color:
                          AppThemeColors.textPrimary.withValues(alpha: 0.08)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Company',
                      style: TextStyle(
                        color:
                            AppThemeColors.textPrimary.withValues(alpha: 0.72),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      initialValue: _companies.any((company) =>
                              company['admin_id']?.toString() ==
                              _selectedAdminId)
                          ? _selectedAdminId
                          : null,
                      dropdownColor: AppThemeColors.surfaceLight,
                      decoration: InputDecoration(
                        isDense: true,
                        filled: true,
                        fillColor:
                            AppThemeColors.textPrimary.withValues(alpha: 0.06),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: BorderSide.none,
                        ),
                      ),
                      iconEnabledColor: AppThemeColors.textPrimary,
                      style: const TextStyle(color: AppThemeColors.textPrimary),
                      items: _companies.map((company) {
                        final adminId = company['admin_id']?.toString() ?? '';
                        final label = (company['company_name'] ??
                                company['office_name'] ??
                                company['admin_name'] ??
                                adminId)
                            .toString();
                        return DropdownMenuItem<String>(
                          value: adminId,
                          child: Text(
                            label,
                            overflow: TextOverflow.ellipsis,
                          ),
                        );
                      }).toList(),
                      onChanged: _switchingCompany ? null : _switchCompany,
                    ),
                  ],
                ),
              ),
            ],
            _drawerInfo(
              'Go Home Status',
              _goHomeStatusLabel(),
              valueColor: _goHomeStatusColor(),
            ),
            Divider(
                height: 26,
                color: AppThemeColors.textPrimary.withValues(alpha: 0.15)),
            ListTile(
              leading:
                  const Icon(Icons.edit, color: AppThemeColors.textPrimary),
              title: const Text(
                'Update Profile (Request)',
                style: TextStyle(color: AppThemeColors.textPrimary),
              ),
              onTap: () {
                Navigator.pop(context);
                _openProfileRequestSheet();
              },
            ),
            ListTile(
              leading: const Icon(Icons.home_work_outlined,
                  color: AppThemeColors.textPrimary),
              title: const Text(
                'Go Home Request',
                style: TextStyle(color: AppThemeColors.textPrimary),
              ),
              subtitle: const Text(
                'Request hometown priority for next trip',
                style:
                    TextStyle(color: AppThemeColors.textDisabled, fontSize: 12),
              ),
              onTap: () {
                Navigator.pop(context);
                _openGoHomeRequestSheet();
              },
            ),
            ListTile(
              leading:
                  const Icon(Icons.history, color: AppThemeColors.textPrimary),
              title: const Text(
                'Trip History',
                style: TextStyle(color: AppThemeColors.textPrimary),
              ),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        DriverHistoryScreen(driverId: widget.driverId),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.support_agent,
                  color: AppThemeColors.textPrimary),
              title: const Text(
                'Help Desk',
                style: TextStyle(color: AppThemeColors.textPrimary),
              ),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute<void>(
                    builder: (_) => HelpDeskScreen(
                      userId: widget.driverId,
                      userType: 'driver',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.logout, color: AppThemeColors.error),
              title: const Text(
                'Logout',
                style: TextStyle(color: AppThemeColors.error),
              ),
              onTap: () {
                Navigator.pop(context);
                _logout();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _drawerInfo(String k, String v, {Color? valueColor}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppThemeColors.textPrimary.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: AppThemeColors.textPrimary.withValues(alpha: 0.06)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              k,
              style: TextStyle(
                color: AppThemeColors.textPrimary.withValues(alpha: 0.70),
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              v,
              style: TextStyle(
                color: valueColor ?? AppThemeColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }

  void _openProfileRequestSheet() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppThemeColors.background,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (_) {
        return Padding(
          padding: EdgeInsets.only(
            left: 14,
            right: 14,
            top: 14,
            bottom: MediaQuery.of(context).viewInsets.bottom + 14,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Profile Change Request',
                style: TextStyle(
                  color: AppThemeColors.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 12),
              _tf(_nameCtrl, 'Name'),
              const SizedBox(height: 8),
              _tf(
                _mobileCtrl,
                'Mobile (10 digits)',
                keyboard: TextInputType.phone,
              ),
              const SizedBox(height: 8),
              _tf(_dlCtrl, 'DL No (2 letters + 13 digits)'),
              const SizedBox(height: 8),
              _tf(_cabCtrl, 'Cab No (MH12AB1234)'),
              const SizedBox(height: 8),
              _tf(
                _homeCtrl,
                'Hometown Location',
                onChanged: _onDriverProfileAddressChanged,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Coordinates: ${_profileCoordLabel()}',
                      style: TextStyle(
                        color:
                            AppThemeColors.textPrimary.withValues(alpha: 0.65),
                        fontSize: 12,
                      ),
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: _openDriverProfileMapPicker,
                    icon: const Icon(Icons.map_outlined, size: 16),
                    label: const Text('Pick on Map'),
                  ),
                ],
              ),
              if (_isResolvingProfileAddress ||
                  _profileAddressResolveNote != null) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    if (_isResolvingProfileAddress) ...[
                      const SizedBox(
                        width: 12,
                        height: 12,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      const SizedBox(width: 8),
                    ],
                    Expanded(
                      child: Text(
                        _isResolvingProfileAddress
                            ? 'Resolving address...'
                            : (_profileAddressResolveNote ?? ''),
                        style: TextStyle(
                          color: AppThemeColors.textPrimary
                              .withValues(alpha: 0.55),
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () async {
                    Navigator.pop(context);
                    await _sendProfileChangeRequest();
                  },
                  icon: const Icon(Icons.send),
                  label: const Text('Send Request to Admin'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  String _currentDriverHomeAddress({Map<String, dynamic>? profile}) {
    final source = profile ?? _profile;
    return (source?['home_address'] ??
            source?['hometown'] ??
            source?['home_town'] ??
            _homeCtrl.text)
        .toString()
        .trim();
  }

  void _openGoHomeRequestSheet() {
    final fallbackHome = _currentDriverHomeAddress();
    if (fallbackHome.isNotEmpty && fallbackHome != '-') {
      _goHomeRequestCtrl.text = fallbackHome;
    }

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppThemeColors.background,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (_) {
        return Padding(
          padding: EdgeInsets.only(
            left: 14,
            right: 14,
            top: 14,
            bottom: MediaQuery.of(context).viewInsets.bottom + 14,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Send Go Home Request',
                style: TextStyle(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 8),
              Text(
                'After admin approval, request is valid for only one trip.',
                style: TextStyle(
                  color: AppThemeColors.textPrimary.withValues(alpha: 0.7),
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppThemeColors.textPrimary.withValues(alpha: 0.04),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _goHomeStatusColor().withValues(alpha: 0.35),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.flag_circle_outlined,
                      color: _goHomeStatusColor(),
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Current status: ${_goHomeStatusLabel()}${_goHomeStatusMeta().isNotEmpty ? ' • ${_goHomeStatusMeta()}' : ''}',
                        style: TextStyle(
                          color: AppThemeColors.textPrimary
                              .withValues(alpha: 0.86),
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              _tf(
                _goHomeRequestCtrl,
                'Driver home address',
                readOnly: true,
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isGoHomeRequestLocked()
                      ? null
                      : () async {
                          Navigator.pop(context);
                          await _sendGoHomeRequest();
                        },
                  icon: const Icon(Icons.send),
                  label: Text(_goHomeActionLabel()),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _assignedTripView(Map<String, dynamic> trip) {
    final tripId = _int(trip['id']) ?? 0;
    final routeNo = (trip['route_no'] ?? '—').toString();
    final tripTypeRaw = (trip['trip_type'] ?? trip['operation'] ?? '')
        .toString()
        .trim()
        .toLowerCase();
    final tripType =
        (tripTypeRaw == 'pickup' || tripTypeRaw == 'drop') ? tripTypeRaw : '';
    final otpRequiredType =
        (trip['otp_required_type'] ?? '').toString().trim().toLowerCase();
    final pendingOtpEmployeeIds =
        ((trip['otp_pending_employee_ids'] as List?) ?? const [])
            .map((e) => e.toString())
            .toSet();
    final hasOtpMetadata = trip.containsKey('otp_pending_count') ||
        trip.containsKey('otp_required_type');
    final status = (trip['status'] ?? '—').toString().toLowerCase();
    final cabNo =
        (trip['cab_no'] ?? trip['vehicle_no'] ?? trip['cab'] ?? '—').toString();
    final scheduledTime =
        (trip['scheduled_time'] ?? trip['schedule_time'] ?? '—').toString();
    final loginTime = (trip['login_time'] ?? scheduledTime).toString();
    final timeLabel = tripType == 'drop' ? 'Logout time' : 'Login time';
    final pickupTime = (trip['pickup_time'] ?? '').toString().trim();
    final pickupByLabel = pickupTime.isNotEmpty ? pickupTime : '';

    final isPreassigned = _asBool(trip['is_preassigned']);
    final canStartNowRaw = trip['can_start_now'];
    final canStartNow = canStartNowRaw == null ? true : _asBool(canStartNowRaw);
    final startAllowedAfter =
        (trip['start_allowed_after'] ?? '').toString().trim();
    final startAllowedAfterLabel = _formatGateDateTime(startAllowedAfter);
    final serverNowRaw = (trip['server_now'] ?? '').toString().trim();
    final canStartNowEffective =
        _isStartWindowOpen(canStartNow, startAllowedAfter, serverNowRaw);
    final unlockCountdown =
        _formatUnlockCountdown(startAllowedAfter, serverNowRaw);
    final cancelRequest = (trip['cancel_request'] is Map)
        ? (trip['cancel_request'] as Map).cast<String, dynamic>()
        : null;
    final cancelRequestStatus =
        (trip['cancel_request_status'] ?? cancelRequest?['status'] ?? '')
            .toString()
            .trim()
            .toLowerCase();
    final cancelRequestPending = cancelRequestStatus == 'pending';

    final emps = (trip['employees'] is List)
        ? (trip['employees'] as List).cast<Map<String, dynamic>>()
        : <Map<String, dynamic>>[];
    final requiredActiveEmployees =
        emps.where((e) => !_isNoShow(e['is_no_show'] ?? e['no_show'])).length;
    final pendingOtpCount = _int(trip['otp_pending_count']) ??
        (pendingOtpEmployeeIds.isNotEmpty
            ? pendingOtpEmployeeIds.length
            : ((tripType == 'pickup' &&
                    (status == 'assigned' ||
                        status == 'created' ||
                        status == 'active'))
                ? requiredActiveEmployees
                : 0));

    final canStartTrip =
        status == 'assigned' || status == 'created' || status == 'active';
    final canEndTrip =
        status == 'started' || status == 'in_progress' || status == 'live';
    final canShowStartTripButton = canStartTrip &&
        (tripType == 'pickup' || tripType == 'drop' || tripType.isEmpty);
    final canPressStartTrip = !(tripType == 'pickup' && pendingOtpCount > 0) &&
        canStartTrip &&
        canStartNowEffective;
    final canPressStartTripSafe =
        tripType == 'pickup' && !hasOtpMetadata ? false : canPressStartTrip;
    final canPressEndTrip =
        !(tripType == 'drop' && pendingOtpCount > 0) && canEndTrip;
    final tripInteractionLocked = isPreassigned && !canStartNowEffective;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _cardInner(
          title: 'Trip Snapshot',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _badge('Route: $routeNo'),
                  _badge("Type: ${tripType.isEmpty ? 'N/A' : tripType}"),
                  _badge('Status: $status'),
                  _badge('Cab: $cabNo'),
                  if (isPreassigned) _badge('Pre-assigned'),
                  if (cancelRequestPending) _badge('Cancel request pending'),
                  if (!canStartNowEffective && startAllowedAfterLabel != '-')
                    _badge('Start after: $startAllowedAfterLabel'),
                  if (!canStartNowEffective && unlockCountdown != '-')
                    _badge('Unlock in: $unlockCountdown'),
                ],
              ),
              const SizedBox(height: 10),
              _kv('Scheduled time', scheduledTime),
              _kv(timeLabel, loginTime),
              if (pickupByLabel.isNotEmpty) _kv('Pickup by', pickupByLabel),
              if (!canStartNowEffective) ...[
                const SizedBox(height: 6),
                _hint(
                  startAllowedAfterLabel == '-'
                      ? 'Pre-assigned trip is locked until scheduled time.'
                      : 'Pre-assigned trip. Start allowed after $startAllowedAfterLabel (in $unlockCountdown).',
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: _isOnline
                  ? [AppThemeColors.successDark, AppThemeColors.surface]
                  : [AppThemeColors.surfaceLight, AppThemeColors.surface],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: _isOnline
                  ? AppThemeColors.success.withValues(alpha: 0.35)
                  : AppThemeColors.textPrimary.withValues(alpha: 0.12),
            ),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(9),
                decoration: BoxDecoration(
                  color: _isOnline
                      ? AppThemeColors.success.withValues(alpha: 0.18)
                      : AppThemeColors.textPrimary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  Icons.location_on,
                  color: _isOnline
                      ? AppThemeColors.success
                      : AppThemeColors.textDisabled,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _isOnline ? 'YOU ARE ONLINE' : 'YOU ARE OFFLINE',
                      style: TextStyle(
                        color: _isOnline
                            ? AppThemeColors.success
                            : AppThemeColors.textDisabled,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    if (_isOnline)
                      const Text(
                        'Broadcasting location...',
                        style: TextStyle(
                            color: AppThemeColors.textSecondary, fontSize: 10),
                      )
                    else
                      const Text(
                        'Go online to start tracking',
                        style: TextStyle(
                            color: AppThemeColors.textDisabled, fontSize: 10),
                      ),
                    DriverTrackingHealthView(
                      isOnline: _isOnline,
                      socketConnected: _socketConnected,
                      trackingHealthError: _trackingHealthError,
                      trackingHealthMessage: _trackingHealthMessage,
                      lastLocationUploadAt: _lastLocationUploadAt,
                      lastUploadServerCode: _lastUploadServerCode,
                      onRetryNow: () async {
                        safeSetState(() {
                          _trackingHealthMessage = 'Retry requested...';
                          _trackingHealthError = false;
                        });
                        await LocationService()
                            .forceUploadNow(routeNo: routeNo);
                      },
                    ),
                  ],
                ),
              ),
              Switch(
                value: _isOnline,
                activeThumbColor: AppThemeColors.success,
                onChanged: (val) async {
                  if (val) {
                    final success = await LocationService()
                        .startBroadcasting(routeNo: routeNo);
                    if (success) {
                      toast('You are now ONLINE');
                      safeSetState(() {
                        _isOnline = true;
                        _trackingHealthError = false;
                        _trackingHealthMessage = _socketConnected
                            ? 'Waiting for first location sync...'
                            : 'Socket connecting...';
                        _lastUploadServerCode = null;
                      });
                    } else {
                      toast('Failed: Enable GPS & Permissions');
                      safeSetState(() {
                        _isOnline = false;
                        _trackingHealthError = true;
                        _trackingHealthMessage =
                            'Could not start tracking. Check GPS permission.';
                        _lastUploadServerCode = null;
                      });
                    }
                  } else {
                    LocationService().stopBroadcasting();
                    toast('You are now OFFLINE');
                    safeSetState(() {
                      _isOnline = false;
                      _trackingHealthError = false;
                      _trackingHealthMessage = null;
                      _lastUploadServerCode = null;
                    });
                  }
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            const Text(
              'Employees',
              style: TextStyle(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w900,
                fontSize: 16,
              ),
            ),
            _badge('Total: ${emps.length}'),
            _badge('Pending OTP: $pendingOtpCount'),
          ],
        ),
        const SizedBox(height: 8),

        if (emps.isEmpty)
          _hint('No employee list found for this trip.')
        else
          ...emps.map<Widget>((e) {
            final m = (e as Map).cast<String, dynamic>();
            final empId = _int(m['id'] ?? m['employee_id']) ?? 0;
            final name = (m['name'] ?? '—').toString();
            final mob = (m['mobile'] ?? '—').toString();
            final addr = (m['address'] ?? '—').toString();
            final noShow = _isNoShow(m['is_no_show'] ?? m['no_show']);
            final empIdStr = empId.toString();
            final isPendingForOtp = pendingOtpEmployeeIds.isEmpty ||
                pendingOtpEmployeeIds.contains(empIdStr);
            final serverOtpRequired = _asBool(m['otp_required']);
            final serverOtpVerified = _asBool(m['otp_verified']);
            final serverOtpType =
                (m['otp_type_required'] ?? '').toString().trim().toLowerCase();

            final effectiveOtpType =
                serverOtpType.isNotEmpty ? serverOtpType : otpRequiredType;
            final otpRequiredForEmp = serverOtpType.isNotEmpty
                ? serverOtpRequired
                : (!noShow && isPendingForOtp);
            final canStartOtp = otpRequiredForEmp &&
                !serverOtpVerified &&
                (effectiveOtpType == 'start' ||
                    _canVerifyEmployeeStartOtp(tripType, status, noShow));
            final canEndOtp = otpRequiredForEmp &&
                !serverOtpVerified &&
                (effectiveOtpType == 'end' ||
                    _canVerifyEmployeeEndOtp(tripType, status, noShow));
            final otpTypeForButton =
                canStartOtp ? 'start' : (canEndOtp ? 'end' : '');
            final otpButtonLabel = serverOtpVerified
                ? 'OTP Verified'
                : (canStartOtp
                    ? 'Fill Start OTP'
                    : (canEndOtp ? 'Fill End OTP' : 'OTP N/A'));
            final otpButtonIcon = serverOtpVerified
                ? Icons.verified
                : (canStartOtp ? Icons.lock_open : Icons.pin);

            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: noShow
                      ? [AppThemeColors.errorDark, AppThemeColors.surface]
                      : [AppThemeColors.surfaceLight, AppThemeColors.surface],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: noShow
                      ? AppThemeColors.error.withValues(alpha: 0.28)
                      : AppThemeColors.textPrimary.withValues(alpha: 0.08),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 16,
                        backgroundColor:
                            AppThemeColors.textPrimary.withValues(alpha: 0.12),
                        child: Text(
                          name.isNotEmpty ? name[0].toUpperCase() : '?',
                          style: const TextStyle(
                            color: AppThemeColors.textPrimary,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          noShow ? '$name (NO SHOW)' : name,
                          style: TextStyle(
                            color: noShow
                                ? AppThemeColors.error
                                : AppThemeColors.textPrimary,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      if (serverOtpVerified)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color:
                                AppThemeColors.success.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                              color:
                                  AppThemeColors.success.withValues(alpha: 0.4),
                            ),
                          ),
                          child: const Text(
                            'OTP VERIFIED',
                            style: TextStyle(
                              color: AppThemeColors.success,
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(Icons.phone,
                          size: 13, color: AppThemeColors.textSecondary),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          mob,
                          style: TextStyle(
                            color: AppThemeColors.textPrimary
                                .withValues(alpha: 0.75),
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.place,
                          size: 13, color: AppThemeColors.textSecondary),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          addr,
                          style: TextStyle(
                            color: AppThemeColors.textPrimary
                                .withValues(alpha: 0.7),
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: noShow
                              ? null
                              : tripInteractionLocked
                                  ? null
                                  : () =>
                                      _openEmployeeNavigation(addr, name: name),
                          icon: const Icon(Icons.navigation),
                          label: const Text('Navigate'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: noShow
                              ? null
                              : tripInteractionLocked
                                  ? null
                                  : () => _callEmployee(mob, name: name),
                          icon: const Icon(Icons.call),
                          label: const Text('Call'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: noShow || tripInteractionLocked
                              ? null
                              : () => _markNoShow(tripId, empId),
                          icon: const Icon(Icons.person_off),
                          label: const Text('No Show'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: (!serverOtpVerified &&
                                  otpTypeForButton.isNotEmpty &&
                                  !tripInteractionLocked)
                              ? () => _openOtpDialogAndVerify(
                                    tripId: tripId,
                                    employeeId: empId,
                                    employeeName: name,
                                    otpType: otpTypeForButton,
                                  )
                              : null,
                          icon: Icon(otpButtonIcon),
                          label: Text(otpButtonLabel),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }),

        const SizedBox(height: 8),

        // Trip actions
        _cardInner(
          title: 'Trip Actions',
          child: Column(
            children: [
              if (tripType == 'pickup' && canStartTrip) ...[
                SizedBox(
                  width: double.infinity,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: canPressStartTripSafe
                            ? [
                                AppThemeColors.secondaryDark,
                                AppThemeColors.secondary
                              ]
                            : [
                                AppThemeColors.surfaceLighter,
                                AppThemeColors.surface,
                              ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ElevatedButton.icon(
                      onPressed: canPressStartTripSafe
                          ? () => _startTripNoOtp(tripId)
                          : null,
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start Trip'),
                      style: ElevatedButton.styleFrom(
                        elevation: 0,
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        foregroundColor: AppThemeColors.textPrimary,
                        disabledForegroundColor: AppThemeColors.textDisabled,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ),
              ] else if (tripType == 'drop' && canStartTrip) ...[
                SizedBox(
                  width: double.infinity,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: canPressStartTrip
                            ? [
                                AppThemeColors.secondaryDark,
                                AppThemeColors.secondary
                              ]
                            : [
                                AppThemeColors.surfaceLighter,
                                AppThemeColors.surface,
                              ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ElevatedButton.icon(
                      onPressed: canPressStartTrip
                          ? () => _startTripNoOtp(tripId)
                          : null,
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start Trip'),
                      style: ElevatedButton.styleFrom(
                        elevation: 0,
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        foregroundColor: AppThemeColors.textPrimary,
                        disabledForegroundColor: AppThemeColors.textDisabled,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ),
              ] else if (canShowStartTripButton) ...[
                SizedBox(
                  width: double.infinity,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: canPressStartTrip
                            ? [
                                AppThemeColors.secondaryDark,
                                AppThemeColors.secondary
                              ]
                            : [
                                AppThemeColors.surfaceLighter,
                                AppThemeColors.surface,
                              ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ElevatedButton.icon(
                      onPressed: canPressStartTrip
                          ? () => _startTripNoOtp(tripId)
                          : null,
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start Trip'),
                      style: ElevatedButton.styleFrom(
                        elevation: 0,
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        foregroundColor: AppThemeColors.textPrimary,
                        disabledForegroundColor: AppThemeColors.textDisabled,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 10),
              if (canEndTrip) ...[
                SizedBox(
                  width: double.infinity,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: canPressEndTrip
                            ? [
                                AppThemeColors.infoDark,
                                AppThemeColors.infoLight
                              ]
                            : [
                                AppThemeColors.surfaceLighter,
                                AppThemeColors.surface,
                              ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ElevatedButton.icon(
                      onPressed: (canPressEndTrip && !tripInteractionLocked)
                          ? () => _completeTrip(tripId)
                          : null,
                      icon: const Icon(Icons.check_circle),
                      label: const Text('End Trip'),
                      style: ElevatedButton.styleFrom(
                        elevation: 0,
                        backgroundColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        foregroundColor: AppThemeColors.textPrimary,
                        disabledForegroundColor: AppThemeColors.textDisabled,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                    ),
                  ),
                ),
              ],
              if (pendingOtpCount > 0) ...[
                const SizedBox(height: 8),
                _hint(
                  'OTP pending for $pendingOtpCount employee(s). Fill employee OTP first.',
                ),
              ],
              if (tripInteractionLocked) ...[
                const SizedBox(height: 8),
                _hint(
                  'Trip is locked. Actions are disabled except Start Nav and Request Trip Cancel.',
                ),
              ],
              if (tripType == 'pickup' && canStartTrip && !hasOtpMetadata) ...[
                const SizedBox(height: 8),
                _hint(
                  'OTP status sync pending. Please refresh/restart backend once.',
                ),
              ],
              if (pendingOtpCount == 0 &&
                  otpRequiredType.isEmpty &&
                  canEndTrip) ...[
                const SizedBox(height: 8),
                _hint('No OTP required in this phase.'),
              ],
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => _openRouteMap(trip),
                  icon: const Icon(Icons.navigation),
                  label: const Text('Start Nav'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppThemeColors.infoDark,
                    foregroundColor: AppThemeColors.textPrimary,
                    padding: const EdgeInsets.symmetric(vertical: 13),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: cancelRequestPending
                      ? null
                      : () => _sendTripCancelRequest(
                            tripId,
                            currentStatus: cancelRequestStatus,
                          ),
                  icon: const Icon(Icons.cancel_schedule_send),
                  label: Text(
                    cancelRequestPending
                        ? 'Trip Cancel Request Pending'
                        : 'Request Trip Cancel',
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppThemeColors.error,
                    side: BorderSide(
                      color: AppThemeColors.error.withValues(alpha: 0.5),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 13),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: tripInteractionLocked
                      ? null
                      : () => _sendSwapRequest(tripId),
                  icon: const Icon(Icons.warning_amber),
                  label: const Text('Request Emergency Swap'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppThemeColors.warning,
                    side: BorderSide(
                      color: AppThemeColors.warning.withValues(alpha: 0.5),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 13),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _startTripNoOtp(int tripId) async {
    try {
      await DriverService.startTrip(tripId, driverId: widget.driverId);
      toast('Trip Started!');

      // Auto-tracking
      final routeNo = _primaryAssignedTrip?['route_no']?.toString() ?? '';
      if (routeNo.isNotEmpty) {
        await LocationService().startBroadcasting(routeNo: routeNo);
      }

      await _loadAssignedTrip();
    } on ApiException catch (e) {
      if (e.code == 'TRIP_NOT_STARTED_YET') {
        final payload = e.data;
        final dataMap = (payload?['data'] is Map)
            ? (payload?['data'] as Map).cast<String, dynamic>()
            : null;
        final when = _formatGateDateTime(
          (payload?['start_allowed_after'] ??
                  dataMap?['start_allowed_after'] ??
                  '')
              .toString(),
        );
        if (when != '-') {
          toast('Trip pre-assigned. You can start after $when.');
        } else {
          toast(e.message);
        }
        await _loadAssignedTrip(silent: true);
        return;
      }
      toast('Start failed: ${e.message}');
    } catch (e) {
      toast('Start failed: $e');
    }
  }

  Future<void> _completeTrip(int tripId) async {
    try {
      await DriverService.completeTrip(tripId, driverId: widget.driverId);
      LocationService().stopBroadcasting();
      toast('Trip Completed!');
      await _loadAssignedTrip();
    } catch (e) {
      toast('End failed: $e');
    }
  }

  // ----------------------------
  // UI helpers
  // ----------------------------
  Widget _cardInner({required String title, required Widget child}) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppThemeColors.textPrimary.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
            color: AppThemeColors.textPrimary.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _msg(String t, {required bool error, Key? key}) {
    return Container(
      key: key,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: (error ? AppThemeColors.error : AppThemeColors.success)
            .withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: (error ? AppThemeColors.error : AppThemeColors.success)
              .withValues(alpha: 0.30),
        ),
      ),
      child: Text(
        t,
        style: const TextStyle(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w800,
          fontSize: 12,
        ),
      ),
    );
  }

  Widget _hint(String t) => Text(
        t,
        style: TextStyle(
          color: AppThemeColors.textPrimary.withValues(alpha: 0.65),
          fontSize: 12,
        ),
      );

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Expanded(
            child: Text(
              k,
              style: TextStyle(
                color: AppThemeColors.textPrimary.withValues(alpha: 0.65),
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              v,
              style: const TextStyle(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }

  Widget _badge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppThemeColors.textPrimary.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
            color: AppThemeColors.textPrimary.withValues(alpha: 0.12)),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: AppThemeColors.textPrimary,
          fontSize: 12,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _tf(
    TextEditingController c,
    String hint, {
    TextInputType keyboard = TextInputType.text,
    int maxLines = 1,
    ValueChanged<String>? onChanged,
    bool readOnly = false,
  }) {
    return TextField(
      controller: c,
      readOnly: readOnly,
      maxLines: maxLines,
      keyboardType: keyboard,
      onChanged: onChanged,
      style: const TextStyle(color: AppThemeColors.textPrimary),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(
            color: AppThemeColors.textPrimary.withValues(alpha: 0.35)),
        filled: true,
        fillColor: AppThemeColors.textPrimary.withValues(alpha: 0.06),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }

  Future<void> _openRouteMap(Map<String, dynamic> trip) async {
    final tripType = (trip['trip_type'] ?? '').toString().toLowerCase();

    // Get employees
    final employees = (trip['employees'] is List)
        ? (trip['employees'] as List).cast<Map<String, dynamic>>()
        : <Map<String, dynamic>>[];

    // Sort employees by sequence if strictly needed, but usually backend sends in order.
    // If backend doesn't sort, we should rely on what we have or sort by sequence_no if available.

    final waypoints = <String>[];
    for (final e in employees) {
      final addr = (e['address'] ?? '').toString();
      if (addr.isNotEmpty) {
        waypoints.add(addr);
      }
    }

    if (waypoints.isEmpty) {
      toast('No employee addresses found for route.');
      return;
    }

    final officeLat = trip['office_lat'];
    final officeLng = trip['office_lng'];
    final officeAddress =
        (trip['office_address'] ?? trip['office_location'] ?? '').toString();
    String destination = '';

    // Logic:
    // Pickup: Destination = Office. Waypoints = Employees.
    // Drop: Destination = Last Employee. Waypoints = Office (if not start) + Other Employees.
    // Simplifying:
    // Pickup: Dest=Office, Waypoints=Emps
    // Drop: Dest=LastEmp, Waypoints=Emps[0..n-1]

    if (tripType == 'pickup') {
      if (officeLat != null && officeLng != null) {
        destination = '$officeLat,$officeLng';
      } else if (officeAddress.trim().isNotEmpty) {
        destination = officeAddress.trim();
      } else {
        destination = 'Office';
      }
    } else {
      // Drop
      if (waypoints.isNotEmpty) {
        destination = waypoints.last;
        waypoints.removeLast();
      }
    }

    final sb = StringBuffer('https://www.google.com/maps/dir/?api=1');
    if (destination.isNotEmpty) {
      sb.write('&destination=${Uri.encodeComponent(destination)}');
    }

    if (waypoints.isNotEmpty) {
      sb.write(
        "&waypoints=${waypoints.map(Uri.encodeComponent).join('|')}",
      );
    }

    sb.write('&travelmode=driving');

    final url = Uri.parse(sb.toString());
    try {
      if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
        toast('Could not open Maps');
      }
    } catch (e) {
      toast('Error opening maps: $e');
    }
  }

  // Missing helper methods
  int? _int(dynamic v) =>
      v == null ? null : (v is int ? v : int.tryParse(v.toString()));

  bool _isNoShow(dynamic v) =>
      v != null &&
      (v == 1 || v == true || v.toString().toLowerCase() == 'true');

  String _timeAgo(DateTime dt) {
    final seconds = DateTime.now().difference(dt).inSeconds;
    if (seconds < 60) return '${seconds}s ago';
    return '${seconds ~/ 60}m ago';
  }

  String _formatGateDateTime(String raw) {
    final v = raw.trim();
    if (v.isEmpty) return '-';
    final dt = DateTime.tryParse(v);
    if (dt == null) return v;
    final local = dt.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(local.day)}-${two(local.month)}-${local.year} ${two(local.hour)}:${two(local.minute)}';
  }

  DateTime _alignedNow({
    required bool asUtc,
    required String serverNowRaw,
  }) {
    final serverNow = DateTime.tryParse(serverNowRaw.trim());
    final deviceNow = asUtc ? DateTime.now().toUtc() : DateTime.now();
    if (serverNow == null) return deviceNow;
    final normalizedServer = asUtc ? serverNow.toUtc() : serverNow.toLocal();
    final skew = normalizedServer.difference(deviceNow);
    return deviceNow.add(skew);
  }

  bool _isStartWindowOpen(
    bool serverCanStartNow,
    String startAllowedAfterRaw,
    String serverNowRaw,
  ) {
    if (serverCanStartNow) return true;
    final dt = DateTime.tryParse(startAllowedAfterRaw.trim());
    if (dt == null) return false;
    final now = _alignedNow(asUtc: dt.isUtc, serverNowRaw: serverNowRaw);
    return !dt.isAfter(now);
  }

  String _formatUnlockCountdown(
    String startAllowedAfterRaw,
    String serverNowRaw,
  ) {
    final dt = DateTime.tryParse(startAllowedAfterRaw.trim());
    if (dt == null) return '-';
    final now = _alignedNow(asUtc: dt.isUtc, serverNowRaw: serverNowRaw);
    final diff = dt.difference(now);
    if (diff.inSeconds <= 0) return '00:00:00';
    final h = diff.inHours;
    final m = diff.inMinutes.remainder(60);
    final s = diff.inSeconds.remainder(60);
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(h)}:${two(m)}:${two(s)}';
  }

  Future<void> _logout() async {
    await SessionStore.clear();
    if (mounted) {
      unawaited(Navigator.of(context).pushReplacementNamed('/login'));
    }
  }

  void _openMaps(double lat, double lon, [String label = 'Location']) async {
    toast('Opening maps for $label');
    // In real app, use url_launcher package
  }

  void _openMapsByQuery(String query, [String label = 'Location']) async {
    final q = query.trim();
    if (q.isEmpty) {
      toast('Location unavailable');
      return;
    }
    final encoded = Uri.encodeComponent(q);
    final geo = Uri.parse('geo:0,0?q=$encoded');
    final google = Uri.parse(
      'https://www.google.com/maps/search/?api=1&query=$encoded',
    );
    try {
      if (await canLaunchUrl(geo)) {
        await launchUrl(geo, mode: LaunchMode.externalApplication);
      } else if (await canLaunchUrl(google)) {
        await launchUrl(google, mode: LaunchMode.externalApplication);
      } else {
        toast('Could not open maps');
      }
    } catch (e) {
      toast('Error opening maps: $e');
    }
  }

  void _openOfficeLocationFromAssignedTrip() {
    final trip = _primaryAssignedTrip;
    if (trip == null) {
      toast('No assigned trip');
      return;
    }

    final officeLat = trip['office_lat'];
    final officeLng = trip['office_lng'];
    final officeAddress =
        (trip['office_address'] ?? trip['office_location'] ?? '')
            .toString()
            .trim();

    if (officeLat is num && officeLng is num) {
      _openMaps(officeLat.toDouble(), officeLng.toDouble(), 'Office');
      return;
    }
    if (officeAddress.isNotEmpty) {
      _openMapsByQuery(officeAddress, 'Office');
      return;
    }
    toast('Office location not available');
  }

  Future<void> _loadDashboard() async {
    await _loadAssignedTrip();
    await _loadProfile();
    await _loadGoHomeRequestStatus();
  }

  String _goHomeStatusLabel() {
    final status = _normalizedGoHomeStatus();
    if (status.isEmpty) return 'No Request';
    if (status == 'approved') return 'Approved';
    if (status == 'rejected') return 'Rejected';
    if (status == 'pending') return 'Pending';
    return status;
  }

  String _normalizedGoHomeStatus() {
    final raw =
        (_goHomeRequest?['status'] ?? '').toString().trim().toLowerCase();
    if (raw == 'approve' || raw == 'accepted' || raw == 'accept') {
      return 'approved';
    }
    if (raw == 'reject') return 'rejected';
    return raw;
  }

  bool _isGoHomeRequestLocked() {
    final status = _normalizedGoHomeStatus();
    return status == 'pending' || status == 'approved';
  }

  String _goHomeActionLabel() {
    final status = _normalizedGoHomeStatus();
    if (status == 'pending') return 'Request Pending';
    if (status == 'approved') return 'Approved (1 Trip)';
    return 'Send Go Home Request';
  }

  Color _goHomeStatusColor() {
    final status = _normalizedGoHomeStatus();
    if (status == 'approved') return AppThemeColors.success;
    if (status == 'rejected') return AppThemeColors.error;
    if (status == 'pending') return AppThemeColors.warning;
    return AppThemeColors.textSecondary;
  }

  String _goHomeStatusMeta() {
    final raw = (_goHomeRequest?['updated_at'] ??
            _goHomeRequest?['created_at'] ??
            _goHomeRequest?['date'] ??
            '')
        .toString()
        .trim();
    if (raw.isEmpty) return '';
    return raw;
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'started':
      case 'in_progress':
      case 'live':
        return AppThemeColors.success;
      case 'assigned':
      case 'created':
      case 'active':
        return AppThemeColors.warning;
      case 'completed':
        return AppThemeColors.info;
      case 'cancelled':
        return AppThemeColors.error;
      default:
        return AppThemeColors.textSecondary;
    }
  }

  Widget _summaryStat({
    required IconData icon,
    required String label,
    required String value,
    required Color accent,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
        decoration: BoxDecoration(
          color: AppThemeColors.textPrimary.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: accent.withValues(alpha: 0.35)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 16, color: accent),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                color: AppThemeColors.textPrimary.withValues(alpha: 0.7),
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: AppThemeColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _dashboardHero() {
    final trip = _primaryAssignedTrip;
    final routeNo = (trip?['route_no'] ?? 'No Route').toString();
    final status = (trip?['status'] ?? 'idle').toString();
    final tripType = (trip?['trip_type'] ?? trip?['operation'] ?? 'n/a')
        .toString()
        .toUpperCase();
    final statusColor = _statusColor(status);
    final isCompact = MediaQuery.of(context).size.width < 430;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppThemeColors.surfaceLight,
            AppThemeColors.surface,
            AppThemeColors.background
          ],
        ),
        border: Border.all(
            color: AppThemeColors.textPrimary.withValues(alpha: 0.12)),
        boxShadow: [
          BoxShadow(
            color: AppThemeColors.primary.withValues(alpha: 0.08),
            blurRadius: 26,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: _isOnline
                      ? AppThemeColors.success.withValues(alpha: 0.18)
                      : AppThemeColors.textPrimary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: _isOnline
                        ? AppThemeColors.success.withValues(alpha: 0.55)
                        : AppThemeColors.textDisabled,
                  ),
                ),
                child: Text(
                  _isOnline ? 'ONLINE TRACKING' : 'OFFLINE MODE',
                  style: TextStyle(
                    color: _isOnline
                        ? AppThemeColors.success
                        : AppThemeColors.textSecondary,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                'Driver Operations',
                style: TextStyle(
                  color: AppThemeColors.textPrimary.withValues(alpha: 0.75),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Command Dashboard',
            style: TextStyle(
              color: AppThemeColors.textPrimary,
              fontSize: 24,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Live route monitoring, OTP flow and action control.',
            style: TextStyle(
              color: AppThemeColors.textPrimary.withValues(alpha: 0.7),
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 14),
          if (!isCompact)
            Row(
              children: [
                _summaryStat(
                  icon: Icons.route,
                  label: 'Route',
                  value: routeNo,
                  accent: AppThemeColors.primary,
                ),
                const SizedBox(width: 8),
                _summaryStat(
                  icon: Icons.compare_arrows,
                  label: 'Trip Type',
                  value: tripType,
                  accent: AppThemeColors.info,
                ),
                const SizedBox(width: 8),
                _summaryStat(
                  icon: Icons.radar,
                  label: 'Status',
                  value: status.toUpperCase(),
                  accent: statusColor,
                ),
              ],
            )
          else
            Column(
              children: [
                Row(
                  children: [
                    _summaryStat(
                      icon: Icons.route,
                      label: 'Route',
                      value: routeNo,
                      accent: AppThemeColors.primary,
                    ),
                    const SizedBox(width: 8),
                    _summaryStat(
                      icon: Icons.compare_arrows,
                      label: 'Trip Type',
                      value: tripType,
                      accent: AppThemeColors.info,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _summaryStat(
                      icon: Icons.radar,
                      label: 'Status',
                      value: status.toUpperCase(),
                      accent: statusColor,
                    ),
                  ],
                ),
              ],
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final horizontalPadding = screenWidth < 390 ? 12.0 : 16.0;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Driver Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.apartment),
            tooltip: 'Office Location',
            onPressed: _openOfficeLocationFromAssignedTrip,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadAssignedTrip,
          ),
        ],
      ),
      drawer: _driverDrawer(_profile),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: _loadDashboard,
            child: SingleChildScrollView(
              padding: EdgeInsets.all(horizontalPadding),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 980),
                  child: Column(
                    children: [
                      _dashboardHero(),
                      const SizedBox(height: 14),
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 300),
                        switchInCurve: Curves.easeOutCubic,
                        switchOutCurve: Curves.easeInCubic,
                        child: _assignedTrips.isNotEmpty
                            ? RGCard(
                                key: const ValueKey('assigned_trip'),
                                title: _assignedTrips.length <= 1
                                    ? 'Assigned Trip'
                                    : 'Assigned Trips',
                                subtitle: _assignedTrips.length <= 1
                                    ? 'Live workflow controls'
                                    : 'Live workflow controls for all trips',
                                child: Column(
                                  children: _assignedTrips
                                      .asMap()
                                      .entries
                                      .map(
                                        (entry) => Padding(
                                          padding: EdgeInsets.only(
                                            bottom: entry.key ==
                                                    _assignedTrips.length - 1
                                                ? 0
                                                : 16,
                                          ),
                                          child: _assignedTripView(entry.value),
                                        ),
                                      )
                                      .toList(),
                                ),
                              )
                            : _msg(
                                'No assigned trip',
                                error: false,
                                key: const ValueKey('no_trip'),
                              ),
                      ),
                      const SizedBox(height: 20),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
