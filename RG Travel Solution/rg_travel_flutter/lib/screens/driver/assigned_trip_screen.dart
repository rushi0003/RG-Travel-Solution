// flutter/lib/screen/driver/assigned_trip_screen.dart
//
// RG Travel Solution — Assigned Trip Screen (Driver)
// Features:
//  - Shows assigned trip (route_no, type pickup/drop, status, time)
//  - Employee list with NO-SHOW action
//  - OTP verify for start/end
//      * Pickup: Start requires OTP
//      * Drop: Start does NOT require OTP (as per your rule)
//      * End requires OTP (exclude no-show employees)
//  - Sends GPS updates every X seconds (demo movement, production replace with real location)
//  - Emergency swap request (vehicle failure / driver swap)
//  - Fixes: setState() after dispose (mounted checks + timers cancelled)
//
// Backend endpoints used:
//  GET  /api/driver/<driver_id>/assigned-trip
//  POST /api/driver/<driver_id>/trip/<trip_id>/no-show
//  POST /api/driver/<driver_id>/trip/<trip_id>/otp/verify
//  POST /api/driver/<driver_id>/gps
//  POST /api/driver/<driver_id>/trip/<trip_id>/swap-request
//
// Base URL:
//  Web: http://127.0.0.1:5000
//  Emulator: http://10.0.2.2:5000

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../services/driver_service.dart';
import '../../widgets/common/rg_card.dart';

class AssignedTripScreen extends StatefulWidget {
  const AssignedTripScreen({
    super.key,
    required this.driverId,
  });
  final String driverId;

  @override
  State<AssignedTripScreen> createState() => _AssignedTripScreenState();
}

class _AssignedTripScreenState extends State<AssignedTripScreen> {
  // ----------------------------
  // Timers (safe)
  // ----------------------------
  Timer? _pollTimer;
  Timer? _gpsTimer;
  Timer? _unlockTickTimer;

  final Duration _pollEvery = const Duration(seconds: 6);
  final Duration _gpsEvery = const Duration(seconds: 8);

  // ----------------------------
  // State
  // ----------------------------
  bool _loading = false;
  String? _error;
  DateTime? _lastRefresh;

  Map<String, dynamic>? _trip;

  // Demo GPS (replace with real geolocator)
  double _lat = 18.5204;
  double _lng = 73.8567;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _gpsTimer?.cancel();
    _unlockTickTimer?.cancel();
    super.dispose();
  }

  void safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  void toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  // ----------------------------
  // Boot + timers
  // ----------------------------
  Future<void> _boot() async {
    safeSetState(() {
      _loading = true;
      _error = null;
    });

    try {
      await _loadTrip();
      _startTimers();
    } catch (e) {
      safeSetState(() => _error = 'Load failed: $e');
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  void _startTimers() {
    _pollTimer?.cancel();
    _gpsTimer?.cancel();
    _unlockTickTimer?.cancel();

    _pollTimer = Timer.periodic(_pollEvery, (_) async {
      await _loadTrip(silent: true);
    });

    _gpsTimer = Timer.periodic(_gpsEvery, (_) async {
      await _sendGps(silent: true);
      _simulateMovement();
    });

    _unlockTickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      safeSetState(() {});
    });
  }

  void _simulateMovement() {
    _lat += 0.00012;
    _lng += 0.00010;
  }

  // ----------------------------
  // API actions
  // ----------------------------
  // ----------------------------
  // API actions
  // ----------------------------
  String get _driverId => widget.driverId;

  Future<void> _loadTrip({bool silent = false}) async {
    if (!silent) {
      safeSetState(() {
        _error = null;
      });
    }

    try {
      final data = await DriverService.getAssignedTrip(_driverId);

      safeSetState(() {
        _trip = data;
        _lastRefresh = DateTime.now();
      });
    } catch (e) {
      if (!silent) safeSetState(() => _error = 'Assigned trip load failed: $e');
    }
  }

  Future<void> _sendGps({bool silent = false}) async {
    final routeNo = (_trip?['route_no'] ?? '').toString().trim();

    try {
      await DriverService.sendGpsUpdate(
        _driverId,
        routeNo: routeNo,
        lat: _lat,
        lng: _lng,
      );
    } catch (e) {
      if (!silent) toast('GPS update failed: $e');
    }
  }

  Future<void> _markNoShow(int tripId, int empId) async {
    try {
      await DriverService.markNoShow(
        _driverId,
        tripId: tripId,
        employeeId: empId,
      );
      toast('No-show marked');
      await _loadTrip(silent: true);
    } catch (e) {
      toast('No-show failed: $e');
    }
  }

  Future<void> _verifyOtp(int tripId, String otpType, String otp) async {
    try {
      await DriverService.verifyTripOtp(
        tripId,
        type: otpType,
        otp: otp,
        driverId: _driverId,
      );
      toast('OTP verified');
      await _loadTrip(silent: true);
    } catch (e) {
      toast('OTP verify failed: $e');
    }
  }

  Future<void> _startTripNoOtp(int tripId) async {
    try {
      await DriverService.startTrip(tripId, driverId: _driverId);
      toast('Trip started');
      await _loadTrip(silent: true);
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
        await _loadTrip(silent: true);
        return;
      }
      toast('Start trip failed: ${e.message}');
    } catch (e) {
      toast('Start trip failed: $e');
    }
  }

  Future<void> _completeTripNoOtp(int tripId) async {
    try {
      await DriverService.completeTrip(tripId, driverId: _driverId);
      toast('Trip completed');
      await _loadTrip(silent: true);
    } catch (e) {
      toast('Complete trip failed: $e');
    }
  }

  Future<void> _sendSwapRequest(int tripId) async {
    final nameCtrl = TextEditingController();
    final mobCtrl = TextEditingController();
    final cabCtrl = TextEditingController();
    final reasonCtrl = TextEditingController();

    final okPressed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Emergency Swap Request'),
        content: SingleChildScrollView(
          child: Column(
            children: [
              _tf(nameCtrl, 'New Driver Name'),
              const SizedBox(height: 8),
              _tf(mobCtrl, 'New Driver Mobile (10 digits)',
                  keyboard: TextInputType.phone),
              const SizedBox(height: 8),
              _tf(cabCtrl, 'New Cab No (MH12AB1234)'),
              const SizedBox(height: 8),
              _tf(reasonCtrl, 'Reason (vehicle failure etc.)', maxLines: 3),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          ElevatedButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Send')),
        ],
      ),
    );

    if (okPressed == true) {
      try {
        await DriverService.createSwapRequest(
          _driverId,
          tripId: tripId,
          reason: reasonCtrl.text.trim(),
          newDriverName: nameCtrl.text.trim(),
          newDriverMobile: mobCtrl.text.trim(),
          newCabNo: cabCtrl.text.trim().toUpperCase(),
        );
        toast('Swap request submitted');
      } catch (e) {
        toast('Swap request failed: $e');
      }
    }

    nameCtrl.dispose();
    mobCtrl.dispose();
    cabCtrl.dispose();
    reasonCtrl.dispose();
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
        title: const Text('Request Trip Cancel'),
        content: _tf(reasonCtrl, 'Reason for cancel request', maxLines: 3),
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
            _driverId,
            tripId: tripId,
            reason: reason,
          );
          toast('Trip cancel request sent to admin');
          await _loadTrip(silent: true);
        } catch (e) {
          toast('Trip cancel request failed: $e');
        }
      }
    }
    reasonCtrl.dispose();
  }

  // ----------------------------
  // Helpers
  // ----------------------------
  int _i(dynamic v, [int def = 0]) {
    if (v == null) return def;
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? def;
  }

  bool _asBool(dynamic v) {
    if (v is bool) return v;
    if (v is num) return v != 0;
    final s = (v ?? '').toString().trim().toLowerCase();
    return s == '1' || s == 'true' || s == 'yes';
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

  bool _isNoShow(dynamic v) => v == 1 || v == true || v.toString() == '1';

  Future<void> _openMapsQuery(String q) async {
    final url = Uri.parse(
        'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(q)}');
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      toast('Could not open maps');
    }
  }

  Future<void> _openOtpDialog(int tripId, {required String otpType}) async {
    final ctrl = TextEditingController();

    final okPressed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(
          otpType == 'start'
              ? 'Start OTP Verification'
              : 'End OTP Verification',
        ),
        content: _tf(ctrl, 'Enter 6-digit OTP', keyboard: TextInputType.number),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          ElevatedButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Verify')),
        ],
      ),
    );

    if (okPressed == true) {
      final otp = ctrl.text.trim();
      await _verifyOtp(tripId, otpType, otp);
    }
    ctrl.dispose();
  }

  // ----------------------------
  // UI
  // ----------------------------
  @override
  Widget build(BuildContext context) {
    final trip = _trip;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Assigned Trip'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: () async {
              await _loadTrip();
              toast('Refreshed');
            },
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(AppSpacing.md),
            children: [
              const SizedBox(height: AppSpacing.sm),
              if (_loading) const LinearProgressIndicator(minHeight: 3),
              if (_error != null) ...[
                const SizedBox(height: AppSpacing.sm),
                _msg(_error!, error: true),
              ],
              const SizedBox(height: AppSpacing.md),
              _card(
                title: 'Live Status',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _kv('GPS', '($_lat, $_lng)'),
                    _kv(
                      'Last refresh',
                      _lastRefresh == null ? '-' : _lastRefresh.toString(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              _card(
                title: 'Trip Details',
                child: (trip == null)
                    ? _hint('No assigned trip.')
                    : _tripView(trip),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _tripView(Map<String, dynamic> trip) {
    final tripId = _i(trip['id']);
    final routeNo = (trip['route_no'] ?? '-').toString();
    final tripType =
        (trip['trip_type'] ?? '-').toString().toLowerCase(); // pickup/drop
    final status = (trip['status'] ?? '-').toString().toLowerCase();
    final time =
        (trip['scheduled_time'] ?? trip['schedule_time'] ?? '-').toString();
    final loginTime = (trip['login_time'] ?? time).toString();
    final timeLabel = tripType == 'drop' ? 'Logout time' : 'Login time';
    final pickupTime = (trip['pickup_time'] ?? '').toString().trim();
    final pickupByLabel = pickupTime.isNotEmpty ? pickupTime : '';

    final cabNo = (trip['cab_no'] ?? '-').toString();
    final totalKm = (trip['total_km'] ?? '-').toString();

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

    final List<dynamic> employees = (trip['employees'] is List<dynamic>)
        ? (trip['employees'] as List<dynamic>)
        : const <dynamic>[];

    // Your rules:
    final startNeedsOtp = (tripType == 'pickup');
    final endNeedsOtp = (tripType == 'drop'); // Pickup ends at office (no OTP)
    final canStartByStatus =
        status == 'assigned' || status == 'created' || status == 'active';
    final canStart = canStartByStatus && canStartNowEffective;
    final tripInteractionLocked = isPreassigned && !canStartNowEffective;

    // Sort employees by order
    final List<Map<String, dynamic>> sortedEmployees =
        employees.map((e) => (e as Map).cast<String, dynamic>()).toList();
    if (tripType == 'pickup') {
      sortedEmployees.sort(
          (a, b) => _i(a['pickup_order']).compareTo(_i(b['pickup_order'])));
    } else {
      sortedEmployees
          .sort((a, b) => _i(a['drop_order']).compareTo(_i(b['drop_order'])));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _badge('Route: $routeNo'),
            _badge('Type: $tripType'),
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
        const SizedBox(height: 8),
        _kv('Scheduled time', time),
        _kv(timeLabel, loginTime),
        if (pickupByLabel.isNotEmpty) _kv('Pickup by', pickupByLabel),
        _kv('Total km', totalKm),
        if (!canStartNowEffective) ...[
          const SizedBox(height: 6),
          _hint(startAllowedAfterLabel == '-'
              ? 'Pre-assigned trip is locked until scheduled time.'
              : 'Pre-assigned trip. Start allowed after $startAllowedAfterLabel (in $unlockCountdown).'),
        ],
        const SizedBox(height: AppSpacing.md),
        Text(
          'Employees (Stop Order)',
          style: AppTypography.titleSmall.copyWith(
            color: AppThemeColors.textPrimary,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        if (sortedEmployees.isEmpty)
          _hint('No employee list found.')
        else
          ...sortedEmployees.asMap().entries.map((entry) {
            final index = entry.key + 1;
            final m = entry.value;
            final empId = _i(m['id']);
            final name = (m['name'] ?? '-').toString();
            final mob = (m['mobile'] ?? '-').toString();
            final addr = (m['address'] ?? '-').toString();
            final noShow = _isNoShow(m['no_show']);

            return Container(
              margin: const EdgeInsets.only(bottom: AppSpacing.sm),
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppThemeColors.cardGlass,
                borderRadius: BorderRadius.circular(AppRadius.sm),
                border: Border.all(
                  color: AppThemeColors.borderLight.withValues(alpha: 0.35),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        alignment: Alignment.center,
                        decoration: const BoxDecoration(
                          color: AppThemeColors.primary,
                          shape: BoxShape.circle,
                        ),
                        child: Text(
                          '$index',
                          style: AppTypography.bodySmall.copyWith(
                            color: AppThemeColors.background,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Text(
                          noShow ? '$name (NO SHOW)' : name,
                          style: AppTypography.titleSmall.copyWith(
                            color: noShow
                                ? AppThemeColors.error
                                : AppThemeColors.textPrimary,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Padding(
                    padding: const EdgeInsets.only(left: 34),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          mob,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppThemeColors.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          addr,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppThemeColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: noShow || tripInteractionLocked
                              ? null
                              : () => _markNoShow(tripId, empId),
                          icon: const Icon(Icons.person_off, size: 16),
                          label: const Text('No Show'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: tripInteractionLocked
                              ? null
                              : () => _openMapsQuery(addr),
                          icon: const Icon(Icons.map, size: 16),
                          label: const Text('Map'),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          }),
        const SizedBox(height: 10),
        _cardInner(
          title: 'Trip Actions',
          child: Column(
            children: [
              if (canStartByStatus && startNeedsOtp) ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: (canStart && !tripInteractionLocked)
                        ? () => _openOtpDialog(tripId, otpType: 'start')
                        : null,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Trip (OTP required)'),
                  ),
                ),
              ] else if (canStartByStatus && !startNeedsOtp) ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: (canStart && !tripInteractionLocked)
                        ? () => _startTripNoOtp(tripId)
                        : null,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Start Trip (No OTP)'),
                  ),
                ),
              ],
              if (canStartByStatus && !canStartNowEffective) ...[
                const SizedBox(height: 8),
                _hint(startAllowedAfterLabel == '-'
                    ? 'Start locked for pre-assigned trip.'
                    : 'Start locked. Allowed after $startAllowedAfterLabel (in $unlockCountdown).'),
              ],
              if (tripInteractionLocked) ...[
                const SizedBox(height: 8),
                _hint(
                    'Trip is locked. Actions are disabled except Request Trip Cancel.'),
              ],
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
                  label: Text(cancelRequestPending
                      ? 'Trip Cancel Request Pending'
                      : 'Request Trip Cancel'),
                ),
              ),
              const SizedBox(height: 10),
              if (status == 'started') ...[
                if (endNeedsOtp)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: tripInteractionLocked
                          ? null
                          : () => _openOtpDialog(tripId, otpType: 'end'),
                      icon: const Icon(Icons.check_circle),
                      label: const Text('End Trip (OTP required)'),
                    ),
                  )
                else
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: tripInteractionLocked
                          ? null
                          : () => _completeTripNoOtp(tripId),
                      icon: const Icon(Icons.check_circle),
                      label: const Text('End Trip (No OTP)'),
                    ),
                  ),
              ],
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: tripInteractionLocked
                          ? null
                          : () => _sendSwapRequest(tripId),
                      icon: const Icon(Icons.warning_amber),
                      label: const Text('Emergency Swap'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: tripInteractionLocked
                          ? null
                          : () async {
                              await _sendGps();
                              toast('GPS sent');
                            },
                      icon: const Icon(Icons.my_location),
                      label: const Text('Send GPS Now'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ----------------------------
  // UI atoms
  // ----------------------------

  Widget _card({required String title, required Widget child}) {
    return RGCard(
      title: title,
      child: child,
    );
  }

  Widget _cardInner({required String title, required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.35),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppTypography.titleSmall.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          child,
        ],
      ),
    );
  }

  Widget _msg(String t, {required bool error}) {
    final accent = error ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: accent.withValues(alpha: 0.30)),
      ),
      child: Text(
        t,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _hint(String t) => Text(
        t,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textSecondary,
        ),
      );

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          Expanded(
            child: Text(
              k,
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              v,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.bodySmall.copyWith(
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
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlassActive,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.45),
        ),
      ),
      child: Text(
        text,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
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
  }) {
    return TextField(
      controller: c,
      maxLines: maxLines,
      keyboardType: keyboard,
      decoration: InputDecoration(
        hintText: hint,
      ),
    );
  }
}
