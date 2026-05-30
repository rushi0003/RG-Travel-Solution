// flutter/lib/screen/employee/employee_dashboard.dart
//
// RG Travel Solution â€” Employee Dashboard
// Features:
// - Left drawer profile + actions (update request, absent, history, help, logout)
// - Assigned trip card (pickup/drop) + driver info + tracking button
// - Employee OTP generation (start/end) according to trip type
// - Office/Home quick map buttons
//
// Backend endpoints used:
//   GET  /api/employee/profile/<employee_id>
//   GET  /api/employee/<employee_id>/my-trip
//   GET  /api/employee/<employee_id>/trip/<trip_id>/otp?type=start|end
//   POST /api/employee/<employee_id>/absent   {date: "YYYY-MM-DD"}
// Optional:
//   POST /api/employee/profile/<employee_id>/change-request
//
// Base URL:
//   Web: http://127.0.0.1:5000
//   Emulator: http://10.0.2.2:5000

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../services/employee_service.dart';
import 'employee_absence_screen.dart';
import 'employee_history_screen.dart';
import 'help_desk_screen.dart';
import 'employee_profile_update.dart';
import '../tracking/live_tracking_screen.dart';
import '../../services/socket_service.dart';
import '../../core/storage/session_store.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/constants.dart';

class EmployeeDashboard extends StatefulWidget {
  final String employeeId;
  final String? baseUrl;

  const EmployeeDashboard({
    super.key,
    required this.employeeId,
    this.baseUrl,
  });

  @override
  State<EmployeeDashboard> createState() => _EmployeeDashboardState();
}

class _EmployeeDashboardState extends State<EmployeeDashboard> {
  bool _loading = false;
  String? _error;

  Map<String, dynamic>? _profile;
  List<Map<String, dynamic>> _myTrips = const [];

  Timer? _pollTimer;
  final Duration _pollEvery = const Duration(seconds: 8);

  final SocketService _socketService = SocketService();

  Map<String, dynamic>? get _primaryTrip =>
      _myTrips.isNotEmpty ? _myTrips.first : null;

  @override
  void initState() {
    super.initState();
    if (widget.baseUrl != null) {
      EmployeeService.setBaseUrl(widget.baseUrl!);
    }

    _boot();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _socketService.dispose();
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

  bool _asBool(dynamic v) {
    if (v is bool) return v;
    if (v is num) return v != 0;
    final s = (v ?? '').toString().trim().toLowerCase();
    return s == '1' || s == 'true' || s == 'yes';
  }

  String _text(dynamic v, {String fallback = "—"}) {
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
              : _text(trip['cab_no'] ??
                  trip['replacement_cab_no'] ??
                  trip['vehicle_no']),
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
        original
            ? trip['original_cab_no']
            : (trip['vehicle_no'] ?? trip['cab_no']),
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

  Widget _driverPanel({
    required String label,
    required String name,
    required String mobile,
    required String cabNo,
    required Color accent,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: accent.withValues(alpha: 0.32)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTypography.labelSmall.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            name,
            style: AppTypography.titleSmall.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                  decoration: BoxDecoration(
                    color: AppThemeColors.cardGlass,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppThemeColors.border),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.phone,
                          color: AppThemeColors.textSecondary, size: 14),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          mobile,
                          overflow: TextOverflow.ellipsis,
                          style: AppTypography.labelSmall.copyWith(
                            color: AppThemeColors.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                  decoration: BoxDecoration(
                    color: AppThemeColors.cardGlass,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppThemeColors.border),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.local_taxi,
                          color: AppThemeColors.textSecondary, size: 14),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          cabNo,
                          overflow: TextOverflow.ellipsis,
                          style: AppTypography.labelSmall.copyWith(
                            color: AppThemeColors.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          if (mobile.trim().isNotEmpty && mobile.trim() != "—") ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: () => _callNumber(mobile),
                icon: const Icon(Icons.call_outlined, size: 16),
                label: const Text("Call"),
              ),
            ),
          ],
        ],
      ),
    );
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

  Future<void> _boot() async {
    safeSetState(() {
      _loading = true;
      _error = null;
    });

    try {
      await _loadAll();

      final token = await SessionStore.getToken();
      if (token != null) {
        _socketService.initSocket(token);
        _socketService.onTripAssigned((_) {
          if (mounted) _loadTrips(silent: true);
        });
        _socketService.onTripUpdated((_) {
          if (mounted) _loadTrips(silent: true);
        });
      }

      _startPolling();
    } catch (e) {
      safeSetState(() => _error = "Load failed: $e");
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(_pollEvery, (_) async {
      await _loadTrips(silent: true);
    });
  }

  Future<void> _loadAll() async {
    await Future.wait([
      _loadProfile(),
      _loadTrips(),
    ]);
  }

  Future<void> _loadProfile() async {
    final int eId = int.tryParse(widget.employeeId) ?? 0;
    try {
      final data = await EmployeeService.getEmployeeProfile(eId);
      safeSetState(() => _profile = data);
    } catch (e) {
      // Handle error gracefully or rethrow if critical
      debugPrint("Profile load error: $e");
    }
  }

  Future<void> _loadTrips({bool silent = false}) async {
    final int eId = int.tryParse(widget.employeeId) ?? 0;
    try {
      final trips = await EmployeeService.getMyTrips(eId);
      if (trips.isNotEmpty) {
        safeSetState(() => _myTrips = trips);
        return;
      }

      final singleTrip = await EmployeeService.getMyTrip(eId);
      safeSetState(
          () => _myTrips = singleTrip == null ? const [] : [singleTrip]);
    } catch (e) {
      if (!silent) safeSetState(() => _error = "Trip load failed: $e");
    }
  }

  Future<void> _markAbsent() async {
    await Navigator.push(
      context,
      MaterialPageRoute<void>(
        builder: (_) => EmployeeAbsenceScreen(employeeId: widget.employeeId),
      ),
    );
    await _loadTrips(silent: true);
  }

  Future<void> _openMapsByQuery(String query) async {
    final url = Uri.parse(
      "https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(query)}",
    );
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      toast("Could not open Google Maps");
    }
  }

  Future<void> _callNumber(String mobile) async {
    final phone = mobile.replaceAll(RegExp(r"[^0-9+]"), "").trim();
    if (phone.isEmpty || phone == "â€”") {
      toast("Driver mobile not available");
      return;
    }
    final uri = Uri(scheme: "tel", path: phone);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      toast("Could not open dialer");
    }
  }

  Future<void> _getOtp(int tripId, String routeNo, String type) async {
    // type: start or end
    try {
      if (routeNo.isEmpty) {
        toast("Invalid route number");
        return;
      }

      final res = await EmployeeService.getTripOtp(routeNo, type: type);
      final otp = res["otp"]?.toString() ?? "â€”";
      final msg =
          "OTP generated successfully"; // Backend might not send message in data

      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: AppThemeColors.surface,
          title: Text("Your ${type.toUpperCase()} OTP",
              style: AppTypography.titleMedium
                  .copyWith(color: AppThemeColors.textPrimary)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(msg,
                  style: AppTypography.bodySmall
                      .copyWith(color: AppThemeColors.textSecondary)),
              const SizedBox(height: 12),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppThemeColors.cardGlass,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppThemeColors.border),
                ),
                child: Text(
                  otp,
                  style: AppTypography.displayLarge.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontSize: 26,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                "Share this OTP with Driver for verification.",
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textTertiary),
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

  Future<void> _showSOSDialog() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        title: const Text("EMERGENCY SOS",
            style: TextStyle(
                color: AppThemeColors.error, fontWeight: FontWeight.bold)),
        content: const Text(
          "Are you sure you want to send an SOS alert?\n\nThis will notify the Admin immediately with your current location.",
          style: TextStyle(color: AppThemeColors.textPrimary),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text("Cancel")),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
                backgroundColor: AppThemeColors.error,
                foregroundColor: AppThemeColors.textPrimary),
            onPressed: () => Navigator.pop(context, true),
            child: const Text("SEND ALERT"),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final int eId = int.tryParse(widget.employeeId) ?? 0;
      final primaryTrip = _primaryTrip;
      final int? tripId = primaryTrip != null ? _int(primaryTrip["id"]) : null;

      // In real app, use Geolocator.getCurrentPosition() here.
      // For now we send null or dummy text, checking backend handles it.
      // TODO: Integrate 'geolocator' package for real coordinates.
      await EmployeeService.sendSOS(
        employeeId: eId,
        tripId: tripId,
        lat: 19.0760, // Example: Mumbai
        lng: 72.8777,
      );

      if (mounted) {
        showDialog<void>(
            context: context,
            builder: (_) => const AlertDialog(
                  backgroundColor: AppThemeColors.surface,
                  title: Text("SOS SENT",
                      style: TextStyle(color: AppThemeColors.error)),
                  content: Text("Admin has been notified. Help is on the way.",
                      style: TextStyle(color: AppThemeColors.textPrimary)),
                ));
      }
    } catch (e) {
      toast("Failed to send SOS: $e");
    }
  }

  // ---------------------- UI ----------------------

  @override
  Widget build(BuildContext context) {
    final p = _profile ?? {};
    final employeeName = (p["name"] ?? "Employee").toString().trim();
    final employeeCode = (p["employee_code"] ?? p["code"] ?? "N/A").toString();
    final width = MediaQuery.of(context).size.width;
    final horizontalPad = width > 900 ? 22.0 : 14.0;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text("Employee Dashboard"),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: _topCircleAction(
              icon: Icons.apartment,
              tooltip: "Office Location",
              onTap: () {
                final officeFromProfile =
                    (p["office_location"] ?? p["office_address"] ?? "")
                        .toString()
                        .trim();
                final officeFromTrip = (_primaryTrip?["office_location"] ??
                        _primaryTrip?["office_address"] ??
                        "")
                    .toString()
                    .trim();
                final officeLat = _primaryTrip?["office_lat"];
                final officeLng = _primaryTrip?["office_lng"];
                final office = officeFromProfile.isNotEmpty
                    ? officeFromProfile
                    : (officeFromTrip.isNotEmpty
                        ? officeFromTrip
                        : ((officeLat != null && officeLng != null)
                            ? "$officeLat,$officeLng"
                            : ""));
                if (office.trim().isEmpty) {
                  toast("Office location not available");
                  return;
                }
                _openMapsByQuery(office);
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: _topCircleAction(
              icon: Icons.home,
              tooltip: "Home Location",
              onTap: () {
                final home =
                    (p["address"] ?? p["home_address"] ?? "").toString();
                if (home.trim().isEmpty) {
                  toast("Home location not available");
                  return;
                }
                _openMapsByQuery(home);
              },
            ),
          ),
          IconButton(
            onPressed: () async {
              await _loadAll();
              toast("Refreshed");
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      drawer: _drawer(p),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showSOSDialog(),
        label: const Text("SOS", style: TextStyle(fontWeight: FontWeight.bold)),
        icon: const Icon(Icons.emergency),
        backgroundColor: AppThemeColors.error,
        foregroundColor: AppThemeColors.textPrimary,
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: ListView(
            padding: EdgeInsets.fromLTRB(horizontalPad, 12, horizontalPad, 20),
            children: [
              _dashboardHero(
                employeeName: employeeName,
                employeeCode: employeeCode,
              ),
              if (_loading) ...[
                const SizedBox(height: 10),
                const LinearProgressIndicator(minHeight: 3),
              ],
              if (_error != null) ...[
                const SizedBox(height: 10),
                _msg(_error!, error: true),
              ],
              const SizedBox(height: 12),
              _card(
                title:
                    _myTrips.length <= 1 ? "Assigned Trip" : "Assigned Trips",
                child: _myTrips.isEmpty
                    ? _hint("No trip assigned yet.")
                    : Column(
                        children: _myTrips
                            .asMap()
                            .entries
                            .map((entry) => Padding(
                                  padding: EdgeInsets.only(
                                    bottom: entry.key == _myTrips.length - 1
                                        ? 0
                                        : 14,
                                  ),
                                  child: _tripCard(entry.value),
                                ))
                            .toList(),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _dashboardHero({
    required String employeeName,
    required String employeeCode,
  }) {
    final trip = _primaryTrip;
    final tripType = (trip?["trip_type"] ?? "N/A").toString().toUpperCase();
    final status = (trip?["status"] ?? "IDLE").toString().toUpperCase();
    final tripCount = _myTrips.length;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: AppGradients.cardGradient,
        border: Border.all(color: AppThemeColors.border),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "Welcome, $employeeName",
            style: AppTypography.titleLarge.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "Track your ride, get OTP securely, and stay connected.",
            style: AppTypography.bodySmall
                .copyWith(color: AppThemeColors.textSecondary),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _badge("Code: $employeeCode"),
              _badge("Trip: $tripType"),
              _badge("Status: $status"),
              _badge("Assigned: $tripCount"),
            ],
          ),
        ],
      ),
    );
  }

  Widget _tripCard(Map<String, dynamic> trip) {
    final tripId = _int(trip["id"]);
    final routeNo = (trip["route_no"] ?? "—").toString();
    final tripType =
        (trip["trip_type"] ?? "—").toString().toLowerCase(); // pickup/drop
    final time = (trip["scheduled_time"] ?? "—").toString();
    final status = (trip["status"] ?? "—").toString().toLowerCase();
    final isNoShow = (trip["is_no_show"] == 1 ||
        trip["is_no_show"] == true ||
        (trip["member_status"] ?? "").toString().toLowerCase() == "no_show" ||
        status == "no_show");

    final currentDriver = _driverSnapshot(trip, original: false);
    final originalDriver = _driverSnapshot(trip, original: true);
    final hasEmergencySwap = _hasEmergencySwap(trip);
    final driverName = _text(currentDriver["name"]);
    final driverMobile = _text(currentDriver["mobile"]);
    final cabNo = _text(currentDriver["cab_no"]);

    final canGetStartOtp = tripType == "pickup" && !isNoShow;
    final canGetEndOtp = tripType == "drop" && !isNoShow;
    final pickupTime = (trip["pickup_time"] ?? "").toString().trim();
    final timeLabel = tripType == "pickup" && pickupTime.isNotEmpty
        ? "Pickup: $pickupTime"
        : "Time: $time";
    final isPreassigned = _asBool(trip["is_preassigned"]);
    final canStartNowRaw = trip["can_start_now"];
    final canStartNow = canStartNowRaw == null ? true : _asBool(canStartNowRaw);
    final startAllowedAfter =
        (trip["start_allowed_after"] ?? "").toString().trim();
    final startAllowedAfterLabel = _formatGateDateTime(startAllowedAfter);
    final serverNowRaw = (trip["server_now"] ?? "").toString().trim();
    final canStartNowEffective =
        _isStartWindowOpen(canStartNow, startAllowedAfter, serverNowRaw);
    final unlockCountdown =
        _formatUnlockCountdown(startAllowedAfter, serverNowRaw);
    final tripInteractionLocked = isPreassigned && !canStartNowEffective;
    final otpType = canGetStartOtp ? "start" : (canGetEndOtp ? "end" : "");

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            _badge("Route: $routeNo"),
            _badge("Type: $tripType"),
            _badge(timeLabel),
            _badge("Status: $status"),
            if (tripInteractionLocked && startAllowedAfterLabel != '-')
              _badge("Unlock: $startAllowedAfterLabel"),
          ],
        ),
        const SizedBox(height: 14),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isNoShow
                  ? [
                      AppThemeColors.error.withValues(alpha: 0.18),
                      AppThemeColors.surface,
                    ]
                  : [
                      AppThemeColors.surfaceLight,
                      AppThemeColors.surface,
                    ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isNoShow
                  ? AppThemeColors.error.withValues(alpha: 0.28)
                  : AppThemeColors.border,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: isNoShow
                          ? AppThemeColors.error.withValues(alpha: 0.20)
                          : AppThemeColors.info.withValues(alpha: 0.20),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: isNoShow
                            ? AppThemeColors.error.withValues(alpha: 0.45)
                            : AppThemeColors.info.withValues(alpha: 0.45),
                      ),
                    ),
                    child: const Icon(
                      Icons.person,
                      color: AppThemeColors.textPrimary,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Assigned Driver",
                          style: TextStyle(
                            color: isNoShow
                                ? AppThemeColors.error.withValues(alpha: 0.90)
                                : AppThemeColors.textSecondary,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          isNoShow ? "$driverName (NO SHOW)" : driverName,
                          style: TextStyle(
                            color: isNoShow
                                ? AppThemeColors.error
                                : AppThemeColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
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
                    color: AppThemeColors.secondary.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: AppThemeColors.secondary.withValues(alpha: 0.40),
                    ),
                  ),
                  child: const Text(
                    "Emergency Swap Active",
                    style: TextStyle(
                      color: AppThemeColors.textPrimary,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              _driverPanel(
                label: hasEmergencySwap
                    ? "Current Driver"
                    : "Assigned Driver Details",
                name: isNoShow ? "$driverName (NO SHOW)" : driverName,
                mobile: driverMobile,
                cabNo: cabNo,
                accent: hasEmergencySwap
                    ? AppThemeColors.success
                    : AppThemeColors.info,
              ),
              if (hasEmergencySwap) ...[
                const SizedBox(height: 10),
                _driverPanel(
                  label: "Original Driver",
                  name: _text(originalDriver["name"]),
                  mobile: _text(originalDriver["mobile"]),
                  cabNo: _text(originalDriver["cab_no"]),
                  accent: AppThemeColors.warning,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 14),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            SizedBox(
              width: 190,
              child: ElevatedButton.icon(
                onPressed: isNoShow || tripInteractionLocked
                    ? null
                    : () {
                        Navigator.push(
                          context,
                          MaterialPageRoute<void>(
                            builder: (_) => LiveTrackingScreen(
                              routeNo: routeNo,
                              driverName: driverName,
                            ),
                          ),
                        );
                      },
                icon: const Icon(Icons.location_on),
                label: const Text("Track Live"),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppThemeColors.primary,
                  foregroundColor: AppThemeColors.background,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            SizedBox(
              width: 170,
              child: OutlinedButton.icon(
                onPressed: isNoShow || tripInteractionLocked
                    ? null
                    : () => _callNumber(driverMobile),
                icon: const Icon(Icons.call),
                label: const Text("Call Driver"),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppThemeColors.textPrimary,
                  side: const BorderSide(color: AppThemeColors.borderLight),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            SizedBox(
              width: 150,
              child: ElevatedButton.icon(
                onPressed: otpType.isEmpty || tripInteractionLocked
                    ? null
                    : () => _getOtp(tripId, routeNo, otpType),
                icon: const Icon(Icons.password),
                label: const Text("Get OTP"),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppThemeColors.secondaryDark,
                  foregroundColor: AppThemeColors.textPrimary,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        if (isNoShow) _hint("Driver marked you as no-show for this trip."),
        if (tripInteractionLocked)
          _hint(startAllowedAfterLabel == '-'
              ? "Pre-assigned trip is locked until driver can start."
              : "Pre-assigned trip locked until $startAllowedAfterLabel${unlockCountdown != '-' ? ' (in $unlockCountdown)' : ''}."),
        if (canGetStartOtp && !tripInteractionLocked)
          _hint("Share Start OTP with Driver at pickup time."),
        if (canGetEndOtp && !tripInteractionLocked)
          _hint("Share End OTP with Driver to complete trip."),
      ],
    );
  }

  Drawer _drawer(Map<String, dynamic> p) {
    final name = (p["name"] ?? "Employee").toString();
    final mobile = (p["mobile"] ?? "â€”").toString();
    final code = (p["employee_code"] ?? p["code"] ?? "â€”").toString();
    final loginTime = (p["login_time"] ?? "â€”").toString();
    final logoutTime = (p["logout_time"] ?? "â€”").toString();
    final address = (p["address"] ?? "â€”").toString();

    return Drawer(
      backgroundColor: AppThemeColors.background,
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: AppThemeColors.cardGlass,
                  child: const Icon(Icons.person,
                      color: AppThemeColors.textPrimary, size: 30),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    name,
                    style: AppTypography.titleSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            _drawerInfo("Mobile", mobile),
            _drawerInfo("Employee Code", code),
            _drawerInfo("Login Time", loginTime),
            _drawerInfo("Logout Time", logoutTime),
            _drawerInfo("Address", address),
            const SizedBox(height: 14),
            const Divider(color: AppThemeColors.border),
            ListTile(
              leading:
                  const Icon(Icons.edit, color: AppThemeColors.textPrimary),
              title: const Text("Update Profile (Request)",
                  style: TextStyle(color: AppThemeColors.textPrimary)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute<void>(
                      builder: (_) => EmployeeProfileUpdateScreen(
                          employeeId: widget.employeeId)),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.event_busy,
                  color: AppThemeColors.textPrimary),
              title: const Text("Absent (Request)",
                  style: TextStyle(color: AppThemeColors.textPrimary)),
              onTap: () async {
                Navigator.pop(context);
                await _markAbsent();
              },
            ),
            ListTile(
              leading:
                  const Icon(Icons.history, color: AppThemeColors.textPrimary),
              title: const Text("Trip History",
                  style: TextStyle(color: AppThemeColors.textPrimary)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute<void>(
                      builder: (_) => EmployeeHistoryScreen(
                          employeeId: int.parse(widget.employeeId))),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.support_agent,
                  color: AppThemeColors.textPrimary),
              title: const Text("Help Desk",
                  style: TextStyle(color: AppThemeColors.textPrimary)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute<void>(
                      builder: (_) =>
                          HelpDeskScreen(employeeId: widget.employeeId)),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.logout, color: AppThemeColors.error),
              title: const Text("Logout",
                  style: TextStyle(color: AppThemeColors.error)),
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

  Widget _drawerInfo(String k, String v) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Row(
        children: [
          Expanded(
              child: Text(k,
                  style: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.textSecondary))),
          Expanded(
            child: Text(
              v,
              style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textPrimary,
                  fontWeight: FontWeight.w800),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }

  // ---------------- UI atoms ----------------

  Future<void> _logout() async {
    await SessionStore.clear();
    if (mounted) {
      Navigator.pushNamedAndRemoveUntil(
          context, AppRoutes.login, (route) => false);
    }
  }

  Widget _topCircleAction({
    required IconData icon,
    required String tooltip,
    required VoidCallback onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: AppThemeColors.cardGlass,
        shape: const CircleBorder(),
        child: InkWell(
          onTap: onTap,
          customBorder: const CircleBorder(),
          child: Padding(
            padding: const EdgeInsets.all(9),
            child: Icon(icon, size: 18, color: AppThemeColors.textPrimary),
          ),
        ),
      ),
    );
  }

  Widget _card({required String title, required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: AppGradients.cardGradient,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppThemeColors.border),
        boxShadow: AppShadows.card,
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
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _msg(String t, {required bool error}) {
    final accent = error ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
      ),
      child: Text(
        t,
        style: AppTypography.labelSmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _hint(String t) => Container(
        margin: const EdgeInsets.only(top: 2),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: AppThemeColors.cardGlass,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppThemeColors.border),
        ),
        child: Text(
          t,
          style: AppTypography.labelSmall.copyWith(
            color: AppThemeColors.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
      );

  Widget _badge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(999),
        border:
            Border.all(color: AppThemeColors.primary.withValues(alpha: 0.30)),
      ),
      child: Text(
        text,
        style: AppTypography.labelSmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  int _int(dynamic v, [int def = 0]) {
    if (v == null) return def;
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? def;
  }
}
