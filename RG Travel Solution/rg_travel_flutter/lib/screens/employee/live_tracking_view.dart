import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../widgets/common/rg_card.dart';
import '../../widgets/tracking/osm_live_map.dart';

class LiveTrackingView extends StatefulWidget {
  const LiveTrackingView({
    super.key,
    required this.routeNo,
    this.employeeId,
    this.adminId,
    this.baseUrl,
    this.pollSeconds = 6,
  });

  final String routeNo;
  final int? employeeId;
  final int? adminId;
  final String? baseUrl;
  final int pollSeconds;

  @override
  State<LiveTrackingView> createState() => _LiveTrackingViewState();
}

class _LiveTrackingViewState extends State<LiveTrackingView> {
  late String _baseUrl;
  late final TextEditingController _baseUrlCtrl;

  final MapController _mapCtrl = MapController();
  Timer? _timer;
  bool _loading = false;
  String? _error;

  Map<String, dynamic>? _track;
  final List<LatLng> _history = [];
  final List<Marker> _markers = [];

  bool _followDriver = true;
  LatLng _lastPos = const LatLng(18.5204, 73.8567);

  @override
  void initState() {
    super.initState();
    _baseUrl = widget.baseUrl ??
        (kIsWeb ? 'http://127.0.0.1:5000' : 'http://10.0.2.2:5000');
    _baseUrlCtrl = TextEditingController(text: _baseUrl);
    _boot();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _baseUrlCtrl.dispose();
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

  Uri _u(String path) {
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('${_baseUrl.trim()}$p');
  }

  Future<Map<String, dynamic>> _getJson(String path) async {
    final r = await http.get(_u(path));
    final body = jsonDecode(r.body);
    if (r.statusCode >= 400) {
      final msg = (body is Map && body['message'] != null)
          ? body['message'].toString()
          : 'HTTP ${r.statusCode}';
      throw Exception(msg);
    }
    if (body is Map<String, dynamic>) return body;
    throw Exception('Invalid response format');
  }

  Future<void> _boot() async {
    safeSetState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _fetchLatest();
      _startPolling();
    } catch (e) {
      safeSetState(() => _error = 'Tracking load failed: $e');
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  void _startPolling() {
    _timer?.cancel();
    _timer = Timer.periodic(Duration(seconds: widget.pollSeconds), (_) async {
      await _fetchLatest(silent: true);
    });
  }

  Future<void> _fetchLatest({bool silent = false}) async {
    try {
      final res =
          await _getJson('/api/tracking/route/${widget.routeNo}/latest');
      final location = (res['location'] is Map)
          ? (res['location'] as Map).cast<String, dynamic>()
          : null;
      final data = (res['data'] is Map)
          ? (res['data'] as Map).cast<String, dynamic>()
          : null;
      final payload = data ?? location;
      if (payload == null) {
        throw Exception(res['message']?.toString() ?? 'No tracking data');
      }

      final lat = _toDouble(payload['lat'] ?? payload['latitude']);
      final lng = _toDouble(payload['lng'] ?? payload['longitude']);
      if (lat == null || lng == null) {
        throw Exception('Invalid lat/lng from backend');
      }

      final pos = LatLng(lat, lng);
      _lastPos = pos;

      _history.add(pos);
      if (_history.length > 300) {
        _history.removeAt(0);
      }

      _markers
        ..clear()
        ..add(
          Marker(
            point: pos,
            width: 48,
            height: 48,
            alignment: Alignment.center,
            child: const Icon(
              Icons.navigation,
              color: AppThemeColors.primary,
              size: 32,
            ),
          ),
        );

      safeSetState(() {
        _track = payload;
        _error = null;
      });

      if (_followDriver) {
        _mapCtrl.move(pos, 16);
      }
    } catch (e) {
      safeSetState(() {
        if (!silent) {
          _error = 'Fetch failed: $e';
        } else if (_track == null) {
          _error = 'Live feed unavailable. Retrying...';
        }
      });
    }
  }

  bool _isLikelyStale(Map<String, dynamic> track) {
    final raw = track['updated_at'] ?? track['timestamp'];
    if (raw == null) return true;
    final ts = DateTime.tryParse(raw.toString())?.toUtc();
    if (ts == null) return true;
    return DateTime.now().toUtc().difference(ts).inSeconds > 60;
  }

  double? _toDouble(dynamic v) {
    if (v == null) return null;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    return double.tryParse(v.toString());
  }

  Future<void> _openDriverInMaps() async {
    final t = _track;
    if (t == null) return;
    final lat = _toDouble(t['lat'] ?? t['latitude']);
    final lng = _toDouble(t['lng'] ?? t['longitude']);
    if (lat == null || lng == null) return;

    final url = Uri.parse('https://www.google.com/maps?q=$lat,$lng');
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      toast('Could not open maps');
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _track ?? {};
    final driverName = (t['driver_name'] ?? t['driverId'] ?? '-').toString();
    final driverMobile = (t['driver_mobile'] ?? '-').toString();
    final cabNo = (t['cab_no'] ?? '-').toString();
    final status =
        (t['status'] ?? (t['stale'] == true ? 'stale' : 'live')).toString();
    final updatedAt = (t['updated_at'] ?? t['timestamp'] ?? '-').toString();
    final stale = t.isEmpty
        ? true
        : (_isLikelyStale(t) || status.toLowerCase() == 'stale');

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: Text('Live Tracking - ${widget.routeNo}'),
        actions: [
          IconButton(
            tooltip: 'Refresh now',
            onPressed: _fetchLatest,
            icon: const Icon(Icons.refresh_rounded),
          ),
          IconButton(
            tooltip: _followDriver ? 'Following driver' : 'Follow driver',
            onPressed: () => safeSetState(() => _followDriver = !_followDriver),
            icon: Icon(
              _followDriver
                  ? Icons.my_location_rounded
                  : Icons.location_searching_rounded,
            ),
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: Column(
            children: [
              _backendCard(),
              if (_loading) const LinearProgressIndicator(minHeight: 3),
              Expanded(
                child: Stack(
                  children: [
                    OsmLiveMap(
                      mapController: _mapCtrl,
                      initialCenter: _lastPos,
                      routeHistory: _history,
                      markers: _markers,
                      polylineColor:
                          AppThemeColors.primary.withValues(alpha: 0.8),
                    ),
                    if (_error != null || stale)
                      Positioned(
                        left: AppSpacing.md,
                        right: AppSpacing.md,
                        top: AppSpacing.md,
                        child: _msg(
                          _error ??
                              'Live feed is stale. Showing last known location.',
                          error: _error != null,
                        ),
                      ),
                    Positioned(
                      left: AppSpacing.md,
                      right: AppSpacing.md,
                      bottom: AppSpacing.md,
                      child: _infoCard(
                        driverName: driverName,
                        driverMobile: driverMobile,
                        cabNo: cabNo,
                        status: status,
                        updatedAt: updatedAt,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _backendCard() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        AppSpacing.md,
        AppSpacing.md,
        AppSpacing.sm,
      ),
      child: RGCard(
        title: 'Connection',
        subtitle: kIsWeb
            ? 'Web: http://127.0.0.1:5000'
            : 'Emulator: http://10.0.2.2:5000',
        padding: const EdgeInsets.all(AppSpacing.md),
        child: TextField(
          controller: _baseUrlCtrl,
          style: AppTypography.bodySmall,
          decoration: _deco('Base URL', 'http://127.0.0.1:5000', Icons.link),
          onSubmitted: (v) async {
            final nv = v.trim();
            if (nv.isEmpty) return;
            safeSetState(() => _baseUrl = nv);
            toast('Base URL set: $_baseUrl');
            await _boot();
          },
        ),
      ),
    );
  }

  Widget _infoCard({
    required String driverName,
    required String driverMobile,
    required String cabNo,
    required String status,
    required String updatedAt,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.96),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.45),
        ),
        boxShadow: AppShadows.elevated,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              _badge('Driver: $driverName'),
              _badge('Cab: $cabNo'),
              _badge('Status: $status'),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Mobile: $driverMobile',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Last updated: $updatedAt',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textTertiary,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _openDriverInMaps,
                  icon: const Icon(Icons.map_outlined, size: 18),
                  label: const Text('Open in Maps'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _mapCtrl.move(_lastPos, 16),
                  icon: const Icon(Icons.center_focus_strong_rounded, size: 18),
                  label: const Text('Center'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _msg(String t, {required bool error}) {
    final accent = error ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
        boxShadow: AppShadows.card,
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

  InputDecoration _deco(String label, String hint, IconData icon) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: Icon(icon, size: 20),
    );
  }
}
