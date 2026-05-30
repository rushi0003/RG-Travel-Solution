import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../services/admin_service.dart';
import '../tracking/live_tracking_screen.dart' as route_tracking;

class LiveTripsScreen extends StatefulWidget {
  const LiveTripsScreen({super.key, required this.adminId});

  final String adminId;

  @override
  State<LiveTripsScreen> createState() => _LiveTripsScreenState();
}

class _LiveTripsScreenState extends State<LiveTripsScreen> {
  int _tabIndex = 0; // 0 live, 1 pre-assign, 2 swap, 3 cancel
  bool _loading = true;
  String? _error;

  String _search = '';
  String _sortBy = 'scheduled';

  Timer? _clockTimer;

  List<Map<String, dynamic>> _liveTrips = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _swapRequests = <Map<String, dynamic>>[];
  List<Map<String, dynamic>> _tripCancelRequests = <Map<String, dynamic>>[];

  @override
  void initState() {
    super.initState();
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {});
    });
    _loadAll();
  }

  @override
  void dispose() {
    _clockTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadAll() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final results = await Future.wait<List<Map<String, dynamic>>>([
        AdminService.getLiveTrips(),
        AdminService.getSwapRequests(),
        AdminService.getTripCancelRequests(),
      ]);

      if (!mounted) return;
      setState(() {
        _liveTrips = results[0];
        _swapRequests = results[1];
        _tripCancelRequests = results[2];
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  bool _asBool(dynamic value) {
    if (value is bool) return value;
    if (value is num) return value != 0;
    final text = (value ?? '').toString().trim().toLowerCase();
    return text == '1' || text == 'true' || text == 'yes';
  }

  int _toInt(dynamic value) {
    if (value is int) return value;
    return int.tryParse((value ?? '').toString()) ?? 0;
  }

  String _toText(dynamic value, {String fallback = ''}) {
    final text = (value ?? '').toString().trim();
    return text.isEmpty ? fallback : text;
  }

  String _employeeMobile(Map<String, dynamic> employee) {
    return _toText(
      employee['mobile'] ??
          employee['employee_mobile'] ??
          employee['phone'] ??
          employee['phone_no'] ??
          employee['contact_no'],
    );
  }

  Map<String, dynamic> _driverSnapshotFromTrip(
    Map<String, dynamic> trip, {
    required bool original,
  }) {
    final key = original ? 'original_driver' : 'current_driver';
    final raw = trip[key];
    if (raw is Map) {
      final driver = raw.cast<dynamic, dynamic>();
      return <String, dynamic>{
        'id': _toText(driver['id']),
        'name': _toText(
          driver['name'],
          fallback: original
              ? _toText(trip['original_driver_name'])
              : _toText(trip['driver_name'] ?? trip['replacement_driver_name']),
        ),
        'mobile': _toText(
          driver['mobile'],
          fallback: original
              ? _toText(trip['original_driver_mobile'])
              : _toText(
                  trip['driver_mobile'] ?? trip['replacement_driver_mobile']),
        ),
        'cab_no': _toText(
          driver['cab_no'],
          fallback: original
              ? _toText(trip['original_cab_no'])
              : _toText(trip['cab_no'] ?? trip['replacement_cab_no']),
        ),
        'role': _toText(driver['role'],
            fallback: original ? 'original' : 'current'),
      };
    }

    return <String, dynamic>{
      'id': '',
      'name': _toText(
        original ? trip['original_driver_name'] : trip['driver_name'],
        fallback: original
            ? _toText(trip['driver_name'])
            : _toText(trip['replacement_driver_name'] ?? trip['driver']),
      ),
      'mobile': _toText(
        original ? trip['original_driver_mobile'] : trip['driver_mobile'],
        fallback: original ? '' : _toText(trip['replacement_driver_mobile']),
      ),
      'cab_no': _toText(
        original ? trip['original_cab_no'] : trip['cab_no'],
        fallback: original ? '' : _toText(trip['replacement_cab_no']),
      ),
      'role': original ? 'original' : 'current',
    };
  }

  String _primaryDriverName(Map<String, dynamic> trip) {
    return _driverSnapshotFromTrip(trip, original: false)['name'] as String;
  }

  Widget _driverInfoCard({
    required String label,
    required Map<String, dynamic> driver,
    required Color accent,
  }) {
    final name = _toText(driver['name'], fallback: '-');
    final mobile = _toText(driver['mobile']);
    final cabNo = _toText(driver['cab_no']);
    final hasPhone = mobile.isNotEmpty;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: accent.withValues(alpha: 0.30)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTypography.labelSmall.copyWith(
              color: accent,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            name,
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (mobile.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              mobile,
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          ],
          if (cabNo.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              'Cab: $cabNo',
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          ],
          if (hasPhone) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: () => _callNumber(
                  mobile,
                  emptyMessage: '$label mobile not available',
                ),
                icon: const Icon(Icons.call_outlined, size: 16),
                label: const Text('Call'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _callNumber(String mobile,
      {required String emptyMessage}) async {
    final phone = mobile.replaceAll(RegExp(r'[^0-9+]'), '').trim();
    if (phone.isEmpty) {
      _toast(emptyMessage);
      return;
    }

    final uri = Uri(scheme: 'tel', path: phone);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _toast('Could not open dialer');
    }
  }

  DateTime _alignedNow({required bool asUtc, required String serverNowRaw}) {
    final serverNow = DateTime.tryParse(serverNowRaw.trim());
    final deviceNow = asUtc ? DateTime.now().toUtc() : DateTime.now();
    if (serverNow == null) return deviceNow;
    final normalizedServer = asUtc ? serverNow.toUtc() : serverNow.toLocal();
    final skew = normalizedServer.difference(deviceNow);
    return deviceNow.add(skew);
  }

  DateTime? _parseTripDateTime(Map<String, dynamic> trip) {
    final raw = _toText(
      trip['start_allowed_after'] ??
          trip['scheduled_at'] ??
          trip['scheduled_datetime'],
    );
    if (raw.isNotEmpty) {
      final parsed = DateTime.tryParse(raw);
      if (parsed != null) return parsed;
    }

    final dayRaw = _toText(trip['trip_day'] ?? trip['date']);
    final timeRaw = _toText(
      trip['schedule_time'] ?? trip['scheduled_time'] ?? trip['trip_time'],
    );
    if (dayRaw.isEmpty || timeRaw.isEmpty) return null;

    try {
      final normDay = dayRaw.contains('-')
          ? dayRaw
          : '${dayRaw.substring(0, 4)}-${dayRaw.substring(4, 6)}-${dayRaw.substring(6, 8)}';
      final safeTime = timeRaw.length == 5 ? '$timeRaw:00' : timeRaw;
      return DateTime.tryParse('${normDay}T$safeTime');
    } catch (_) {
      return null;
    }
  }

  bool _isPreassigned(Map<String, dynamic> trip) {
    if (trip.containsKey('is_preassigned')) {
      return _asBool(trip['is_preassigned']);
    }
    final dt = _parseTripDateTime(trip);
    if (dt == null) return false;
    return dt.isAfter(DateTime.now());
  }

  bool _canStartNow(Map<String, dynamic> trip) {
    final dt = _parseTripDateTime(trip);
    final serverNowRaw = _toText(trip['server_now']);
    if (trip.containsKey('can_start_now')) {
      if (_asBool(trip['can_start_now'])) return true;
      if (dt == null) return false;
      final now = _alignedNow(asUtc: dt.isUtc, serverNowRaw: serverNowRaw);
      return !dt.isAfter(now);
    }
    if (!_isPreassigned(trip)) return true;
    if (dt == null) return false;
    final now = _alignedNow(asUtc: dt.isUtc, serverNowRaw: serverNowRaw);
    return !dt.isAfter(now);
  }

  String _formatDateTime(DateTime? dt) {
    if (dt == null) return '-';
    String two(int n) => n.toString().padLeft(2, '0');
    final local = dt.toLocal();
    return '${two(local.day)}-${two(local.month)}-${local.year} ${two(local.hour)}:${two(local.minute)}';
  }

  String _formatCountdown(Map<String, dynamic> trip) {
    final startAt = _parseTripDateTime(trip);
    if (startAt == null) return '-';
    final serverNowRaw = _toText(trip['server_now']);
    final now = _alignedNow(asUtc: startAt.isUtc, serverNowRaw: serverNowRaw);
    final diff = startAt.difference(now);
    if (diff.inSeconds <= 0) return '00:00:00';
    final h = diff.inHours;
    final m = diff.inMinutes.remainder(60);
    final s = diff.inSeconds.remainder(60);
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(h)}:${two(m)}:${two(s)}';
  }

  List<Map<String, dynamic>> _filteredTrips({required bool preassignOnly}) {
    final query = _search.trim().toLowerCase();
    final trips = _liveTrips.where((trip) {
      final isPre = _isPreassigned(trip);
      if (preassignOnly && !isPre) return false;
      if (!preassignOnly) return _tripMatchesQuery(trip, query);
      return _tripMatchesQuery(trip, query);
    }).toList();

    trips.sort((a, b) {
      if (_sortBy == 'driver') {
        return _primaryDriverName(a)
            .toLowerCase()
            .compareTo(_primaryDriverName(b).toLowerCase());
      }
      if (_sortBy == 'status') {
        return _toText(a['status'])
            .toLowerCase()
            .compareTo(_toText(b['status']).toLowerCase());
      }
      if (_sortBy == 'route') {
        return _toText(a['route_no']).compareTo(_toText(b['route_no']));
      }

      final adt = _parseTripDateTime(a);
      final bdt = _parseTripDateTime(b);
      if (adt == null && bdt == null)
        return _toInt(b['id']).compareTo(_toInt(a['id']));
      if (adt == null) return 1;
      if (bdt == null) return -1;
      return adt.compareTo(bdt);
    });

    return trips;
  }

  bool _tripMatchesQuery(Map<String, dynamic> trip, String q) {
    if (q.isEmpty) return true;
    final bag = [
      _toText(trip['route_no']),
      _toText(trip['driver_name']),
      _toText(trip['driver_mobile']),
      _toText(trip['original_driver_name']),
      _toText(trip['original_driver_mobile']),
      _toText(trip['replacement_driver_name']),
      _toText(trip['replacement_driver_mobile']),
      _toText(trip['cab_no']),
      _toText(trip['original_cab_no']),
      _toText(trip['replacement_cab_no']),
      _toText(trip['status']),
      _toText(trip['operation']),
      _toText(trip['trip_type']),
      _toText(trip['login_time']),
      _toText(trip['pickup_time']),
    ].join(' ').toLowerCase();
    return bag.contains(q);
  }

  Future<void> _markTripLive(Map<String, dynamic> trip) async {
    final tripId = _toInt(trip['id'] ?? trip['trip_id']);
    if (!_canStartNow(trip)) {
      final when = _formatDateTime(_parseTripDateTime(trip));
      _toast(
        when == '-'
            ? 'This trip is pre-assigned and cannot be started yet.'
            : 'This trip is pre-assigned. Start allowed after $when.',
      );
      return;
    }

    try {
      await AdminService.startTrip(tripId, by: 'admin');
      _toast('Trip marked live');
      await _loadAll();
    } catch (e) {
      _toast('Failed to mark trip live: $e');
    }
  }

  Future<void> _cancelTrip(Map<String, dynamic> trip) async {
    final tripId = _toInt(trip['id'] ?? trip['trip_id']);
    final reasonCtl = TextEditingController(text: 'Cancelled by admin');

    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('Cancel Trip'),
          content: TextField(
            controller: reasonCtl,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'Reason',
              hintText: 'Enter cancel reason',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Close'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(reasonCtl.text.trim()),
              child: const Text('Cancel Trip'),
            ),
          ],
        );
      },
    );

    final cleanReason = (reason ?? '').trim();
    if (cleanReason.length < 3) return;

    try {
      await AdminService.cancelTrip(tripId, reason: cleanReason);
      _toast('Trip cancelled');
      await _loadAll();
    } catch (e) {
      _toast('Failed to cancel trip: $e');
    }
  }

  Future<void> _completeTrip(Map<String, dynamic> trip) async {
    final tripId = _toInt(trip['id'] ?? trip['trip_id']);
    try {
      await AdminService.completeTrip(tripId, widget.adminId);
      _toast('Trip completed');
      await _loadAll();
    } catch (e) {
      _toast('Failed to complete trip: $e');
    }
  }

  void _openLiveTracking(Map<String, dynamic> trip) {
    final routeNo = _toText(trip['route_no']);
    final driverName = _primaryDriverName(trip);
    final tripId = _toInt(trip['id'] ?? trip['trip_id']);
    if (routeNo.isEmpty) {
      _toast('Tracking unavailable: route number missing');
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => route_tracking.LiveTrackingScreen(
          routeNo: routeNo,
          driverName: driverName.isEmpty ? null : driverName,
          tripId: tripId > 0 ? tripId : null,
        ),
      ),
    );
  }

  Future<void> _approveSwap(int requestId) async {
    try {
      await AdminService.approveSwapRequest(requestId);
      _toast('Swap request approved');
      await _loadAll();
    } catch (e) {
      _toast('Failed to approve: $e');
    }
  }

  Future<void> _rejectSwap(int requestId) async {
    try {
      await AdminService.rejectSwapRequest(requestId);
      _toast('Swap request rejected');
      await _loadAll();
    } catch (e) {
      _toast('Failed to reject: $e');
    }
  }

  Future<void> _approveTripCancel(int requestId) async {
    try {
      await AdminService.approveTripCancelRequest(
        requestId,
        adminId: widget.adminId,
      );
      _toast('Trip cancel request approved');
      await _loadAll();
    } catch (e) {
      _toast('Failed to approve: $e');
    }
  }

  Future<void> _rejectTripCancel(int requestId) async {
    try {
      await AdminService.rejectTripCancelRequest(
        requestId,
        adminId: widget.adminId,
      );
      _toast('Trip cancel request rejected');
      await _loadAll();
    } catch (e) {
      _toast('Failed to reject: $e');
    }
  }

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  Widget _badge(
    String text, {
    Color? bg,
    Color? fg,
    bool strong = false,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: bg ?? AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Text(
        text,
        style: AppTypography.labelSmall.copyWith(
          color: fg ?? AppThemeColors.textPrimary,
          fontWeight: strong ? FontWeight.w700 : FontWeight.w600,
        ),
      ),
    );
  }

  Widget _tabButton(String label, int index, int count) {
    final selected = _tabIndex == index;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() {
            _tabIndex = index;
          });
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOut,
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          decoration: BoxDecoration(
            color: selected ? AppThemeColors.secondary : Colors.transparent,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          alignment: Alignment.center,
          child: Text(
            '$label ($count)',
            style: AppTypography.labelMedium.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }

  Widget _tripCard(Map<String, dynamic> trip) {
    final tripId = _toInt(trip['id'] ?? trip['trip_id']);
    final routeNo = _toText(trip['route_no'], fallback: '-');
    final status = _toText(trip['status'], fallback: 'live').toLowerCase();
    final operation = _toText(trip['operation'] ?? trip['trip_type']);
    final scheduled = _toText(
      trip['scheduled_time'] ?? trip['schedule_time'] ?? trip['trip_time'],
    );
    final login = _toText(trip['login_time'], fallback: scheduled);
    final pickup = _toText(trip['pickup_time']);
    final pickupBy = pickup.isEmpty ? '' : pickup;

    final currentDriver = _driverSnapshotFromTrip(trip, original: false);
    final originalDriver = _driverSnapshotFromTrip(trip, original: true);
    final hasEmergencySwap = _asBool(trip['has_emergency_swap']) &&
        (_toText(originalDriver['name']) != _toText(currentDriver['name']) ||
            _toText(originalDriver['mobile']) !=
                _toText(currentDriver['mobile']));
    final driverName = _toText(currentDriver['name'], fallback: '-');
    final driverMobile = _toText(currentDriver['mobile']);
    final cabNo = _toText(currentDriver['cab_no'], fallback: '-');
    final totalKm = _toText(trip['total_km'], fallback: '-');
    final vehicleType = _toText(trip['vehicle_type']);

    final membersRaw = trip['employees'] ?? trip['members'];
    final members = membersRaw is List
        ? membersRaw.whereType<Map<String, dynamic>>().toList()
        : <Map<String, dynamic>>[];

    final noShowCount =
        members.where((m) => _asBool(m['no_show'] ?? m['is_no_show'])).length;
    final confirmedCount = members.length - noShowCount;

    final isPreassigned = _isPreassigned(trip);
    final canStartNow = _canStartNow(trip);
    final startAllowedAfter = _formatDateTime(_parseTripDateTime(trip));
    final unlockCountdown = _formatCountdown(trip);

    final statusColor = switch (status) {
      'assigned' => AppThemeColors.info,
      'started' || 'active' || 'in_progress' => AppThemeColors.success,
      'cancelled' => AppThemeColors.error,
      'completed' => AppThemeColors.secondary,
      _ => AppThemeColors.textTertiary,
    };
    final hasAssignedDriver = driverName != '-';

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Route: $routeNo',
                  style: AppTypography.titleSmall.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              _badge('TripId: $tripId'),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              _badge(
                'Status: $status',
                bg: statusColor.withValues(alpha: 0.16),
                fg: statusColor,
                strong: true,
              ),
              if (operation.isNotEmpty) _badge('Type: $operation'),
              _badge('Cab: $cabNo'),
              if (vehicleType.isNotEmpty) _badge('Vehicle: $vehicleType'),
              _badge('KM: $totalKm'),
              if (isPreassigned)
                _badge(
                  canStartNow ? 'Pre-Assign: Ready' : 'Pre-Assign: Locked',
                  bg: canStartNow
                      ? AppThemeColors.success.withValues(alpha: 0.16)
                      : AppThemeColors.error.withValues(alpha: 0.16),
                  fg: canStartNow
                      ? AppThemeColors.success
                      : AppThemeColors.error,
                  strong: true,
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          if (hasEmergencySwap)
            _badge(
              'Emergency Swap Applied',
              bg: AppThemeColors.secondary.withValues(alpha: 0.16),
              fg: AppThemeColors.secondary,
              strong: true,
            ),
          const SizedBox(height: AppSpacing.sm),
          if (hasEmergencySwap) ...[
            _driverInfoCard(
              label: 'Current Driver',
              driver: currentDriver,
              accent: AppThemeColors.success,
            ),
            const SizedBox(height: AppSpacing.sm),
            _driverInfoCard(
              label: 'Original Driver',
              driver: originalDriver,
              accent: AppThemeColors.warning,
            ),
          ] else ...[
            Text(
              'Driver: $driverName${driverMobile.isNotEmpty ? '  |  $driverMobile' : ''}',
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textPrimary),
            ),
            if (driverMobile.isNotEmpty) ...[
              const SizedBox(height: 6),
              OutlinedButton.icon(
                onPressed: () => _callNumber(
                  driverMobile,
                  emptyMessage: 'Driver mobile not available',
                ),
                icon: const Icon(Icons.call_outlined),
                label: const Text('Call Driver'),
              ),
            ],
          ],
          if (scheduled.isNotEmpty)
            Text(
              'Scheduled: $scheduled',
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          if (login.isNotEmpty)
            Text(
              'Login: $login',
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          if (pickupBy.isNotEmpty)
            Text(
              'Pickup by: $pickupBy',
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          if (isPreassigned && !canStartNow) ...[
            const SizedBox(height: 6),
            Text(
              'Start allowed after: $startAllowedAfter',
              style: AppTypography.bodySmall
                  .copyWith(color: AppThemeColors.errorLight),
            ),
            if (unlockCountdown != '-')
              Text(
                'Unlock in: $unlockCountdown',
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.errorLight),
              ),
          ],
          if (members.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Employees (${members.length})  |  Confirmed: $confirmedCount  |  No-show: $noShowCount',
              style: AppTypography.labelMedium.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: members.map((m) {
                final name = _toText(m['name'], fallback: 'Employee');
                final mobile = _employeeMobile(m);
                final isNoShow = _asBool(m['no_show'] ?? m['is_no_show']);
                return Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: isNoShow
                        ? AppThemeColors.error.withValues(alpha: 0.18)
                        : AppThemeColors.cardGlass,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: AppThemeColors.border),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Flexible(
                        child: Text(
                          isNoShow ? '$name (No-show)' : name,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppThemeColors.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (mobile.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        InkWell(
                          borderRadius: BorderRadius.circular(999),
                          onTap: () => _callNumber(
                            mobile,
                            emptyMessage: '$name mobile not available',
                          ),
                          child: const Padding(
                            padding: EdgeInsets.all(2),
                            child: Icon(
                              Icons.call_outlined,
                              size: 16,
                              color: AppThemeColors.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              OutlinedButton(
                onPressed: (status == 'assigned' || status == 'created')
                    ? () => _markTripLive(trip)
                    : null,
                child: Text(canStartNow ? 'Mark Live' : 'Locked'),
              ),
              OutlinedButton(
                onPressed: (status == 'completed' || status == 'cancelled')
                    ? null
                    : () => _cancelTrip(trip),
                child: const Text('Cancel Trip'),
              ),
              FilledButton(
                onPressed: (status == 'completed' || status == 'cancelled')
                    ? null
                    : () => _completeTrip(trip),
                child: const Text('Complete'),
              ),
              OutlinedButton.icon(
                onPressed:
                    hasAssignedDriver ? () => _openLiveTracking(trip) : null,
                icon: const Icon(Icons.location_searching),
                label: const Text('Live Tracking'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _swapRequestCard(Map<String, dynamic> req) {
    final requestId = _toInt(req['id']);
    final status = _toText(req['status'], fallback: 'pending').toLowerCase();
    final routeNo =
        _toText(req['route_no'], fallback: 'Trip #${_toInt(req['trip_id'])}');
    final reason = _toText(req['reason']);
    final requestedBy = _toText(req['driver_name']);
    final newDriver = _toText(req['new_driver_name']);
    final newMobile = _toText(req['new_driver_mobile']);
    final newCab = _toText(req['new_cab_no']);

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Swap Request: $routeNo',
            style: AppTypography.titleSmall.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          _badge('Status: $status'),
          if (requestedBy.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Requested by: $requestedBy',
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ),
          if (reason.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Reason: $reason',
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ),
          if (newDriver.isNotEmpty || newCab.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Swap to: $newDriver${newMobile.isNotEmpty ? ' | $newMobile' : ''}${newCab.isNotEmpty ? ' | $newCab' : ''}',
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              OutlinedButton(
                onPressed:
                    status == 'pending' ? () => _rejectSwap(requestId) : null,
                child: const Text('Reject'),
              ),
              const SizedBox(width: AppSpacing.sm),
              FilledButton(
                onPressed:
                    status == 'pending' ? () => _approveSwap(requestId) : null,
                child: const Text('Approve'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _tripCancelRequestCard(Map<String, dynamic> req) {
    final requestId = _toInt(req['id']);
    final status = _toText(req['status'], fallback: 'pending').toLowerCase();
    final routeNo =
        _toText(req['route_no'], fallback: 'Trip #${_toInt(req['trip_id'])}');
    final reason = _toText(req['reason']);
    final driverName = _toText(req['driver_name']);

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Trip Cancel Request: $routeNo',
            style: AppTypography.titleSmall.copyWith(
              color: AppThemeColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          _badge('Status: $status'),
          if (driverName.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Driver: $driverName',
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ),
          if (reason.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Reason: $reason',
                style: AppTypography.bodySmall
                    .copyWith(color: AppThemeColors.textSecondary),
              ),
            ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              OutlinedButton(
                onPressed: status == 'pending'
                    ? () => _rejectTripCancel(requestId)
                    : null,
                child: const Text('Reject'),
              ),
              const SizedBox(width: AppSpacing.sm),
              FilledButton(
                onPressed: status == 'pending'
                    ? () => _approveTripCancel(requestId)
                    : null,
                child: const Text('Approve'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTripsHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        0,
        AppSpacing.md,
        AppSpacing.md,
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              onChanged: (value) {
                setState(() {
                  _search = value;
                });
              },
              decoration: InputDecoration(
                hintText: 'Search route, driver, cab, status',
                prefixIcon: const Icon(Icons.search),
                filled: true,
                fillColor: AppThemeColors.cardGlass,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  borderSide: BorderSide(color: AppThemeColors.border),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  borderSide: BorderSide(color: AppThemeColors.border),
                ),
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            decoration: BoxDecoration(
              color: AppThemeColors.cardGlass,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppThemeColors.border),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _sortBy,
                dropdownColor: AppThemeColors.surface,
                items: const [
                  DropdownMenuItem(value: 'scheduled', child: Text('By Time')),
                  DropdownMenuItem(value: 'route', child: Text('By Route')),
                  DropdownMenuItem(value: 'driver', child: Text('By Driver')),
                  DropdownMenuItem(value: 'status', child: Text('By Status')),
                ],
                onChanged: (v) {
                  if (v == null) return;
                  setState(() {
                    _sortBy = v;
                  });
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTripsList({required bool preassignOnly}) {
    final trips = _filteredTrips(preassignOnly: preassignOnly);
    if (trips.isEmpty) {
      return Center(
        child: Text(
          preassignOnly
              ? 'No pre-assigned trips found.'
              : 'No live trips found.',
          style: AppTypography.bodyMedium
              .copyWith(color: AppThemeColors.textSecondary),
        ),
      );
    }

    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      itemCount: trips.length,
      itemBuilder: (_, i) => _tripCard(trips[i]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final preAssignedCount = _liveTrips.where(_isPreassigned).length;

    final swapView = _swapRequests.isEmpty
        ? Center(
            child: Text(
              'No swap requests.',
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          )
        : ListView.builder(
            itemCount: _swapRequests.length,
            itemBuilder: (_, i) => _swapRequestCard(_swapRequests[i]),
          );

    final tripCancelView = _tripCancelRequests.isEmpty
        ? Center(
            child: Text(
              'No trip cancel requests.',
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
          )
        : ListView.builder(
            itemCount: _tripCancelRequests.length,
            itemBuilder: (_, i) =>
                _tripCancelRequestCard(_tripCancelRequests[i]),
          );

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppGradients.backgroundGradient,
        ),
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        'View Live Trips',
                        style: AppTypography.titleLarge.copyWith(
                          color: AppThemeColors.textPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: _loadAll,
                      icon: const Icon(Icons.refresh,
                          color: AppThemeColors.textPrimary),
                    ),
                  ],
                ),
              ),
              if (_loading) const LinearProgressIndicator(minHeight: 2),
              if (_error != null)
                Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                  child: Text(
                    _error!,
                    style: AppTypography.bodySmall
                        .copyWith(color: AppThemeColors.error),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.md,
                  AppSpacing.sm,
                  AppSpacing.md,
                  AppSpacing.md,
                ),
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: AppThemeColors.cardGlass,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppThemeColors.border),
                  ),
                  child: Row(
                    children: [
                      _tabButton('Live Trips', 0, _liveTrips.length),
                      _tabButton('Pre-Assign', 1, preAssignedCount),
                      _tabButton('Swap', 2, _swapRequests.length),
                      _tabButton('Cancel Req', 3, _tripCancelRequests.length),
                    ],
                  ),
                ),
              ),
              if (_tabIndex == 0 || _tabIndex == 1) _buildTripsHeader(),
              Expanded(
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                  child: RefreshIndicator(
                    onRefresh: _loadAll,
                    child: IndexedStack(
                      index: _tabIndex,
                      children: [
                        _buildTripsList(preassignOnly: false),
                        _buildTripsList(preassignOnly: true),
                        swapView,
                        tripCancelView,
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
