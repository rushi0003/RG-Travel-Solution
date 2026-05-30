// flutter/lib/screen/employee/my_trip_screen.dart
//
// RG Travel Solution — Employee My Trip Screen
// - Shows assigned trip details (route_no, type pickup/drop, time, status)
// - Driver + cab details
// - Live driver tracking button (navigate with route_no)
// - OTP generation (employee side) based on your rules:
//     * Pickup: Start Trip + Get START OTP
//     * Drop:   End Trip   + Get END OTP
//
// Backend endpoints used:
//   GET /api/employee/<employee_id>/my-trip
//   GET /api/employee/<employee_id>/trip/<trip_id>/otp?type=start|end
//
// Base URL:
//   Web: http://127.0.0.1:5000
//   Emulator: http://10.0.2.2:5000

import 'dart:async';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/services/employee_service.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:geolocator/geolocator.dart';

import '../../core/theme/app_theme.dart';
import '../../widgets/common/rg_card.dart';
import 'driver_tracking_screen.dart';

class MyTripScreen extends StatefulWidget {
  final String employeeId;
  final String? employeeName;

  const MyTripScreen({
    super.key,
    required this.employeeId,
    this.employeeName,
  });

  @override
  State<MyTripScreen> createState() => _MyTripScreenState();
}

class _MyTripScreenState extends State<MyTripScreen> {
  bool _loading = false;
  String? _error;

  Timer? _pollTimer;
  Map<String, dynamic>? _trip;

  @override
  void initState() {
    super.initState();
    _loadTrip();
    _startTimer();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startTimer() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      _loadTrip(silent: true);
    });
  }

  void safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  void toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  bool _asBool(dynamic v) {
    if (v is bool) return v;
    if (v is num) return v != 0;
    final s = (v ?? '').toString().trim().toLowerCase();
    return s == '1' || s == 'true' || s == 'yes';
  }

  String _text(dynamic v, {String fallback = '-'}) {
    final text = (v ?? '').toString().trim();
    return text.isEmpty ? fallback : text;
  }

  Map<String, dynamic> _driverSnapshot(
    Map<String, dynamic> trip, {
    required bool original,
  }) {
    final key = original ? 'original_driver' : 'current_driver';
    final raw = trip[key];
    if (raw is Map) {
      final driver = raw.cast<dynamic, dynamic>();
      return {
        'name': _text(
          driver['name'],
          fallback: original
              ? _text(trip['original_driver_name'])
              : _text(trip['driver_name'] ?? trip['replacement_driver_name']),
        ),
        'mobile': _text(
          driver['mobile'],
          fallback: original
              ? _text(trip['original_driver_mobile'])
              : _text(
                  trip['driver_mobile'] ?? trip['replacement_driver_mobile']),
        ),
        'cab_no': _text(
          driver['cab_no'],
          fallback: original
              ? _text(trip['original_cab_no'])
              : _text(trip['cab_no'] ?? trip['replacement_cab_no']),
        ),
      };
    }

    return {
      'name': _text(
        original ? trip['original_driver_name'] : trip['driver_name'],
        fallback: original
            ? _text(trip['driver_name'])
            : _text(trip['replacement_driver_name']),
      ),
      'mobile': _text(
        original ? trip['original_driver_mobile'] : trip['driver_mobile'],
      ),
      'cab_no': _text(
        original ? trip['original_cab_no'] : trip['cab_no'],
      ),
    };
  }

  bool _hasEmergencySwap(Map<String, dynamic> trip) {
    final current = _driverSnapshot(trip, original: false);
    final original = _driverSnapshot(trip, original: true);
    return _asBool(trip['has_emergency_swap']) &&
        (current['name'] != original['name'] ||
            current['mobile'] != original['mobile'] ||
            current['cab_no'] != original['cab_no']);
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

  int _i(dynamic v, [int def = 0]) {
    if (v == null) return def;
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? def;
  }

  int get _employeeId => int.tryParse(widget.employeeId) ?? 0;

  Future<void> _loadTrip({bool silent = false}) async {
    if (!silent) {
      safeSetState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      final data = await EmployeeService.getMyTrip(_employeeId);
      safeSetState(() => _trip = data);
    } catch (e) {
      if (!silent) safeSetState(() => _error = "Trip load failed: $e");
    } finally {
      if (!silent && mounted) safeSetState(() => _loading = false);
    }
  }

  Future<void> _openMapsQuery(String q) async {
    final url = Uri.parse(
        "https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(q)}");
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      toast("Could not open maps");
    }
  }

  Future<void> _getOtp(String routeNo, String type) async {
    // type: start/end
    try {
      final res = await EmployeeService.getTripOtp(
        routeNo,
        type: type,
      );

      final otp =
          res["data"]?["otp"]?.toString() ?? res["otp"]?.toString() ?? '-';
      final msg = res["message"]?.toString() ?? "OTP generated";

      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: Text('${type.toUpperCase()} OTP'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                msg,
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                  vertical: AppSpacing.sm,
                ),
                decoration: BoxDecoration(
                  color: AppThemeColors.cardGlassActive,
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  border: Border.all(
                    color: AppThemeColors.borderLight.withValues(alpha: 0.45),
                  ),
                ),
                child: Text(
                  otp,
                  style: AppTypography.displayLarge.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Share this OTP with Driver for verification.',
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text("Close")),
          ],
        ),
      );
    } catch (e) {
      toast("OTP failed: $e");
    }
  }

  void _openTracking(String routeNo) {
    Navigator.push(
      context,
      MaterialPageRoute<void>(
        builder: (_) => DriverTrackingScreen(
          routeNo: routeNo,
          employeeId: widget.employeeId,
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // SOS & RATING LOGIC
  // ---------------------------------------------------------------------------

  Future<void> _sendSos(int tripId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(
          'Emergency SOS',
          style: AppTypography.titleLarge.copyWith(
            color: AppThemeColors.error,
            fontWeight: FontWeight.w800,
          ),
        ),
        content: const Text(
          'Are you in danger?\nThis will alert the admin immediately with your location.',
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Send SOS'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    safeSetState(() => _loading = true);
    try {
      double lat = 0.0;
      double lng = 0.0;

      // Try fetching real location
      try {
        if (!kIsWeb) {
          LocationPermission permission = await Geolocator.checkPermission();
          if (permission == LocationPermission.denied) {
            permission = await Geolocator.requestPermission();
          }

          if (permission == LocationPermission.whileInUse ||
              permission == LocationPermission.always) {
            const locationSettings = LocationSettings(
              accuracy: LocationAccuracy.high,
            );
            final pos = await Geolocator.getCurrentPosition(
              locationSettings: locationSettings,
            );
            lat = pos.latitude;
            lng = pos.longitude;
          }
        }
      } catch (locErr) {
        debugPrint("SOS Location Error: $locErr");
        // Proceed with 0,0 if location fails - safety first (send alert anyway)
      }

      await EmployeeService.sendSOS(
        employeeId: _employeeId,
        tripId: tripId,
        lat: lat,
        lng: lng,
      );

      if (mounted) {
        showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('SOS Sent'),
            content: const Text('Admin has been notified of your emergency.'),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('OK'))
            ],
          ),
        );
      }
    } catch (e) {
      toast("SOS Failed: $e");
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  Future<void> _rateTrip(int tripId) async {
    int rating = 5;
    final ctrl = TextEditingController();

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (context, setDialogState) {
        return AlertDialog(
          title: const Text('Rate Driver'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  final r = index + 1;
                  return IconButton(
                    onPressed: () => setDialogState(() => rating = r),
                    icon: Icon(
                      r <= rating ? Icons.star : Icons.star_border,
                      color: AppThemeColors.warning,
                      size: 32,
                    ),
                  );
                }),
              ),
              const SizedBox(height: AppSpacing.sm),
              TextField(
                controller: ctrl,
                decoration: const InputDecoration(
                  hintText: 'Review (optional)',
                ),
                maxLines: 2,
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(context);
                try {
                  await EmployeeService.rateTrip(
                    tripId,
                    employeeId: _employeeId,
                    rating: rating,
                    feedback: ctrl.text,
                  );
                  toast('Rating submitted!');
                } catch (e) {
                  toast('Rating failed: $e');
                }
              },
              child: const Text('Submit'),
            ),
          ],
        );
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.employeeName ?? "Employee";

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: Text('My Trip - $name'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loadTrip,
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
              if (_loading) const LinearProgressIndicator(minHeight: 3),
              if (_error != null) ...[
                const SizedBox(height: AppSpacing.sm),
                _msg(_error!, error: true),
              ],
              const SizedBox(height: AppSpacing.md),
              if (_trip == null)
                _card(
                  title: 'Trip',
                  child: _hint('No trip assigned yet.'),
                )
              else
                _tripView(_trip!),
            ],
          ),
        ),
      ),
    );
  }

  Widget _tripView(Map<String, dynamic> t) {
    final tripId = _i(t["id"]);
    final routeNo = (t["route_no"] ?? "-").toString();
    final tripType =
        (t["trip_type"] ?? "-").toString().toLowerCase(); // pickup/drop
    final status = (t["status"] ?? "-").toString().toLowerCase();
    final time = (t["scheduled_time"] ?? "-").toString();

    final currentDriver = _driverSnapshot(t, original: false);
    final originalDriver = _driverSnapshot(t, original: true);
    final hasEmergencySwap = _hasEmergencySwap(t);
    final driverName = _text(currentDriver["name"]);
    final driverMobile = _text(currentDriver["mobile"]);
    final cabNo = _text(currentDriver["cab_no"]);

    final isPreassigned = _asBool(t["is_preassigned"]);
    final canStartNowRaw = t["can_start_now"];
    final canStartNow = canStartNowRaw == null ? true : _asBool(canStartNowRaw);
    final startAllowedAfter =
        (t["start_allowed_after"] ?? "").toString().trim();
    final startAllowedAfterLabel = _formatGateDateTime(startAllowedAfter);
    final serverNowRaw = (t["server_now"] ?? "").toString().trim();
    final canStartNowEffective =
        _isStartWindowOpen(canStartNow, startAllowedAfter, serverNowRaw);
    final tripInteractionLocked = isPreassigned && !canStartNowEffective;
    final office =
        (t["office_location"] ?? t["office_address"] ?? "").toString();
    final myHome =
        (t["employee_home"] ?? t["employee_address"] ?? "").toString();

    final employees = (t["employees"] is List)
        ? (t["employees"] as List<dynamic>)
        : <dynamic>[];

    // OTP rules (employee side)
    final showStartOtp = tripType == "pickup";
    final showEndOtp = tripType == "drop";

    // Status checks
    final isCompleted = status == "completed";
    final isActive =
        status == "started" || status == "in_progress" || status == "live";
    final statusColor =
        isCompleted ? AppThemeColors.success : AppThemeColors.warning;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ALERT HEADER
        if (isActive)
          Container(
            margin: const EdgeInsets.only(bottom: 16),
            width: double.infinity,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppThemeColors.error,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () => _sendSos(tripId),
              icon: const Icon(Icons.warning_amber_rounded,
                  color: AppThemeColors.textPrimary, size: 28),
              label: const Text("SOS EMERGENCY",
                  style: TextStyle(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold,
                      fontSize: 16)),
            ),
          ),

        _card(
            title: "Trip Details",
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _badge("Route: $routeNo"),
                  _badge("Type: $tripType"),
                  _badge("Time: $time"),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(
                        color: statusColor.withValues(alpha: 0.55),
                      ),
                    ),
                    child: Text(
                      status.toUpperCase(),
                      style: TextStyle(
                          color: statusColor,
                          fontWeight: FontWeight.bold,
                          fontSize: 12),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (hasEmergencySwap)
                Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppThemeColors.warning.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: AppThemeColors.warning.withValues(alpha: 0.45),
                    ),
                  ),
                  child: Text(
                    "Emergency Swap Active",
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.warning,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              _kv(hasEmergencySwap ? "Current Driver" : "Driver", driverName),
              _kv(
                hasEmergencySwap ? "Current Driver Mobile" : "Driver Mobile",
                driverMobile,
              ),
              _kv(hasEmergencySwap ? "Current Cab No" : "Cab No", cabNo),
              if (hasEmergencySwap) ...[
                const SizedBox(height: 8),
                _kv("Original Driver", _text(originalDriver["name"])),
                _kv(
                  "Original Driver Mobile",
                  _text(originalDriver["mobile"]),
                ),
                _kv("Original Cab No", _text(originalDriver["cab_no"])),
              ],
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: routeNo.trim().isEmpty || tripInteractionLocked
                          ? null
                          : () => _openTracking(routeNo),
                      icon: const Icon(Icons.location_on),
                      label: const Text("Driver Tracking"),
                    ),
                  ),
                ],
              ),
              if (isCompleted) ...[
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppThemeColors.warning,
                      foregroundColor: AppThemeColors.background,
                    ),
                    onPressed: () => _rateTrip(tripId),
                    icon: const Icon(Icons.star),
                    label: const Text("Rate Your Trip",
                        style: TextStyle(
                            color: AppThemeColors.background,
                            fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ])),

        const SizedBox(height: 12),

        // Locations
        _card(
          title: "Locations",
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: office.trim().isEmpty
                      ? null
                      : () => _openMapsQuery(office),
                  icon: const Icon(Icons.apartment),
                  label: const Text("Office"),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: myHome.trim().isEmpty
                      ? null
                      : () => _openMapsQuery(myHome),
                  icon: const Icon(Icons.home),
                  label: const Text("Home"),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        if (employees.isNotEmpty) ...[
          _card(
              title: "Co-Passengers",
              child: Column(
                children: employees.map((e) {
                  final m = (e as Map).cast<String, dynamic>();
                  final en = (m["name"] ?? "-").toString();
                  final ea = (m["address"] ?? "-").toString();
                  return Container(
                    margin: const EdgeInsets.only(bottom: AppSpacing.sm),
                    padding: const EdgeInsets.all(AppSpacing.sm),
                    decoration: BoxDecoration(
                      color: AppThemeColors.cardGlass,
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                      border: Border.all(
                        color:
                            AppThemeColors.borderLight.withValues(alpha: 0.35),
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            en,
                            style: AppTypography.bodyMedium.copyWith(
                              color: AppThemeColors.textPrimary,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: ea.trim().isEmpty
                              ? null
                              : () => _openMapsQuery(ea),
                          child: const Text("Map"),
                        )
                      ],
                    ),
                  );
                }).toList(),
              )),
          const SizedBox(height: 12),
        ],

        // OTP Actions
        if (!isCompleted)
          _card(
            title: "OTP Actions",
            child: Column(
              children: [
                if (showStartOtp) ...[
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => toast(
                              "Share the below OTP with your driver to start the trip."),
                          icon: const Icon(Icons.help_outline),
                          label: const Text("How to Start?"),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: tripInteractionLocked
                              ? null
                              : () => _getOtp(routeNo, "start"),
                          icon: const Icon(Icons.password),
                          label: const Text("Get OTP"),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _hint(tripInteractionLocked
                      ? (startAllowedAfterLabel == '-'
                          ? "Pre-assigned trip is locked until driver can start."
                          : "Pre-assigned trip locked until $startAllowedAfterLabel.")
                      : "Pickup start OTP share with driver."),
                ],
                if (showEndOtp) ...[
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => toast(
                              "Share the below OTP with your driver to end the trip."),
                          icon: const Icon(Icons.help_outline),
                          label: const Text("How to End?"),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: tripInteractionLocked
                              ? null
                              : () => _getOtp(routeNo, "end"),
                          icon: const Icon(Icons.password),
                          label: const Text("Get OTP"),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _hint(tripInteractionLocked
                      ? (startAllowedAfterLabel == '-'
                          ? "Pre-assigned trip is locked until driver can start."
                          : "Pre-assigned trip locked until $startAllowedAfterLabel.")
                      : "Drop end OTP share with driver."),
                ],
                if (!showStartOtp && !showEndOtp) ...[
                  _hint("OTP action not available for this trip type."),
                ],
              ],
            ),
          ),
      ],
    );
  }

  // ---------------- UI atoms ----------------

  Widget _card({required String title, required Widget child}) {
    return RGCard(
      title: title,
      child: child,
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
}
