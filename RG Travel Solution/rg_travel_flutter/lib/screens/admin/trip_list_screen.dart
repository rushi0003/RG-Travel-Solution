import 'dart:async';

import 'package:flutter/material.dart';
import '../../services/admin_service.dart';
import '../../widgets/common/rg_card.dart';
import '../../widgets/common/rg_loader.dart';

class TripListScreen extends StatefulWidget {
  final String adminId;
  const TripListScreen({super.key, required this.adminId});

  @override
  State<TripListScreen> createState() => _TripListScreenState();
}

class _TripListScreenState extends State<TripListScreen> {
  bool _loading = true;
  List<Map<String, dynamic>> _trips = [];
  Timer? _unlockTickTimer;

  bool _asBool(dynamic v) {
    if (v is bool) return v;
    if (v is num) return v != 0;
    final s = (v ?? '').toString().trim().toLowerCase();
    return s == '1' || s == 'true' || s == 'yes';
  }

  DateTime? _parseTripDateTime(Map<String, dynamic> trip) {
    final raw = (trip['start_allowed_after'] ??
            trip['scheduled_at'] ??
            trip['scheduled_datetime'] ??
            '')
        .toString()
        .trim();
    if (raw.isNotEmpty) {
      final parsed = DateTime.tryParse(raw);
      if (parsed != null) return parsed;
    }

    final dayRaw = (trip['trip_day'] ?? trip['date'] ?? '').toString().trim();
    final timeRaw = (trip['schedule_time'] ?? trip['scheduled_time'] ?? '')
        .toString()
        .trim();
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
    if (trip.containsKey('is_preassigned'))
      return _asBool(trip['is_preassigned']);
    final dt = _parseTripDateTime(trip);
    if (dt == null) return false;
    return dt.isAfter(DateTime.now());
  }

  bool _canMarkLive(Map<String, dynamic> trip) {
    final dt = _parseTripDateTime(trip);
    final serverNowRaw = (trip['server_now'] ?? '').toString().trim();
    if (trip.containsKey('can_start_now'))
      return _isStartWindowOpen(
          _asBool(trip['can_start_now']), dt, serverNowRaw);
    if (!_isPreassigned(trip)) return true;
    if (dt == null) return true;
    final now = _alignedNow(asUtc: dt.isUtc, serverNowRaw: serverNowRaw);
    return !dt.isAfter(now);
  }

  String _formatDateTime(DateTime? dt) {
    if (dt == null) return '-';
    String two(int n) => n.toString().padLeft(2, '0');
    final local = dt.toLocal();
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
    DateTime? startAt,
    String serverNowRaw,
  ) {
    if (serverCanStartNow) return true;
    if (startAt == null) return false;
    final now = _alignedNow(asUtc: startAt.isUtc, serverNowRaw: serverNowRaw);
    return !startAt.isAfter(now);
  }

  String _formatCountdown(DateTime? startAt, String serverNowRaw) {
    if (startAt == null) return '-';
    final now = _alignedNow(asUtc: startAt.isUtc, serverNowRaw: serverNowRaw);
    final diff = startAt.difference(now);
    if (diff.inSeconds <= 0) return '00:00:00';
    final h = diff.inHours;
    final m = diff.inMinutes.remainder(60);
    final s = diff.inSeconds.remainder(60);
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(h)}:${two(m)}:${two(s)}';
  }

  @override
  void initState() {
    super.initState();
    _unlockTickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {});
    });
    _loadTrips();
  }

  @override
  void dispose() {
    _unlockTickTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadTrips() async {
    setState(() => _loading = true);
    try {
      final trips = await AdminService.getLiveTrips();
      setState(() => _trips = trips);
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Failed to load trips: $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _markLive(Map<String, dynamic> trip) async {
    if (!_canMarkLive(trip)) {
      final startAt = _parseTripDateTime(trip);
      final when = _formatDateTime(startAt);
      final msg = when == '-'
          ? 'This trip is pre-assigned and cannot be started yet.'
          : 'This trip is pre-assigned. Start allowed after $when.';
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(msg)));
      }
      return;
    }
    try {
      final tripId = trip['trip_id'] ?? trip['id'];
      await AdminService.startTrip(tripId as int, by: 'admin');
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Trip marked live')));
      await _loadTrips();
    } catch (e) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Failed to start trip: $e')));
    }
  }

  Future<void> _completeTrip(Map<String, dynamic> trip) async {
    final tripId = trip['trip_id'] ?? trip['id'];
    final kmText = await showDialog<String?>(
        context: context,
        builder: (ctx) {
          final ctl = TextEditingController();
          return AlertDialog(
            title: const Text('Complete Trip - Final KM'),
            content: TextField(
                controller: ctl,
                keyboardType: TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(hintText: 'Total KM')),
            actions: [
              TextButton(
                  onPressed: () => Navigator.of(ctx).pop(null),
                  child: const Text('Cancel')),
              TextButton(
                  onPressed: () => Navigator.of(ctx).pop(ctl.text),
                  child: const Text('OK')),
            ],
          );
        });

    double? finalKm;
    if (kmText != null && kmText.isNotEmpty) finalKm = double.tryParse(kmText);

    try {
      await AdminService.finishTrip(tripId as int, widget.adminId,
          totalKm: finalKm);
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Trip completed')));
      await _loadTrips();
    } catch (e) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Failed to complete trip: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Trips - Admin')),
      body: _loading
          ? const Center(child: RGLoader())
          : RefreshIndicator(
              onRefresh: _loadTrips,
              child: ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: _trips.length,
                itemBuilder: (ctx, i) {
                  final t = _trips[i];
                  final isPreassigned = _isPreassigned(t);
                  final canMarkLive = _canMarkLive(t);
                  final startAt = _parseTripDateTime(t);
                  final serverNowRaw =
                      (t['server_now'] ?? '').toString().trim();
                  final startAtLabel = _formatDateTime(startAt);
                  final unlockCountdown =
                      _formatCountdown(startAt, serverNowRaw);
                  final subtitle =
                      '${t['trip_type'] ?? ''} | ${t['schedule_time'] ?? t['scheduled_time'] ?? ''} | ${t['status'] ?? ''}'
                      '${isPreassigned ? ' | Pre-assigned${startAtLabel != '-' ? ' ($startAtLabel)' : ''}' : ''}'
                      '${(!canMarkLive && unlockCountdown != '-') ? ' | Unlock in $unlockCountdown' : ''}';
                  return RGCard(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: ListTile(
                      title: Text(t['route_no']?.toString() ??
                          'Route ${t['trip_id'] ?? '—'}'),
                      subtitle: Text(subtitle),
                      trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                        TextButton(
                          onPressed: canMarkLive ? () => _markLive(t) : null,
                          child: Text(canMarkLive ? 'Mark Live' : 'Locked'),
                        ),
                        const SizedBox(width: 8),
                        TextButton(
                            onPressed: () => _completeTrip(t),
                            child: const Text('Complete')),
                      ]),
                      onTap: () {},
                    ),
                  );
                },
              ),
            ),
    );
  }
}
