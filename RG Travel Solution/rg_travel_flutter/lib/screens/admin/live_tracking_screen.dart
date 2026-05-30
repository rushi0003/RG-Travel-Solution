import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:rg_travel_flutter/core/storage/session_store.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../widgets/common/rg_card.dart';

class LiveTrackingScreen extends StatefulWidget {
  final String adminId;
  final String? baseUrl;
  final String? initialQuery;

  const LiveTrackingScreen({
    super.key,
    required this.adminId,
    this.baseUrl,
    this.initialQuery,
  });

  @override
  State<LiveTrackingScreen> createState() => _LiveTrackingScreenState();
}

class _LiveTrackingScreenState extends State<LiveTrackingScreen> {
  late String _baseUrl;

  bool _loading = false;
  String? _error;
  DateTime? _lastRefresh;

  Timer? _timer;
  final Duration _pollEvery = const Duration(seconds: 5);

  List<Map<String, dynamic>> _drivers = [];
  late final TextEditingController _searchCtrl;

  @override
  void initState() {
    super.initState();
    _baseUrl = widget.baseUrl ??
        (kIsWeb ? 'http://127.0.0.1:5000' : 'http://10.0.2.2:5000');
    _searchCtrl =
        TextEditingController(text: (widget.initialQuery ?? '').trim());
    _startPolling();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _searchCtrl.dispose();
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
    final headers = await SessionStore.authHeaders();
    final r = await http.get(_u(path), headers: headers);
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

  int? _int(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    return int.tryParse(v.toString());
  }

  double? _dbl(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  void _startPolling() {
    _timer?.cancel();
    _fetchDrivers(showLoader: true);
    _timer = Timer.periodic(_pollEvery, (_) {
      _fetchDrivers(showLoader: false);
    });
  }

  Future<void> _fetchDrivers({required bool showLoader}) async {
    if (showLoader) {
      safeSetState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      final res = await _getJson('/api/admin/drivers/online');
      final drivers = _normalizeDrivers(res);

      safeSetState(() {
        _drivers = drivers;
        _lastRefresh = DateTime.now();
        _error = null;
      });
    } catch (e) {
      safeSetState(() {
        _error = 'Live tracking failed: $e';
      });
    } finally {
      if (showLoader) safeSetState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> _normalizeDrivers(Map<String, dynamic> res) {
    final data = res['data'];
    final rawList = switch (data) {
      List<dynamic> list => list,
      Map<String, dynamic> map when map['online_drivers'] is List<dynamic> =>
        map['online_drivers'] as List<dynamic>,
      Map<dynamic, dynamic> map when map['online_drivers'] is List<dynamic> =>
        map['online_drivers'] as List<dynamic>,
      _ => <dynamic>[],
    };

    return rawList.whereType<Map<dynamic, dynamic>>().map((entry) {
      final driver = entry.cast<String, dynamic>();
      final nestedLocation = driver['location'] is Map<dynamic, dynamic>
          ? (driver['location'] as Map<dynamic, dynamic>)
              .cast<String, dynamic>()
          : const <String, dynamic>{};

      final routeNo = (driver['route_no'] ??
              nestedLocation['route_no'] ??
              nestedLocation['routeNo'] ??
              '')
          .toString();
      final lat = _dbl(driver['lat']) ?? _dbl(nestedLocation['lat']);
      final lng = _dbl(driver['lng']) ?? _dbl(nestedLocation['lng']);
      final updatedAt = (driver['updated_at'] ??
              nestedLocation['updated_at'] ??
              nestedLocation['device_time'] ??
              driver['last_seen'] ??
              '')
          .toString();

      return <String, dynamic>{
        ...driver,
        'route_no': routeNo,
        'lat': lat,
        'lng': lng,
        'updated_at': updatedAt,
        'is_assigned':
            driver['is_assigned'] ?? (routeNo.trim().isNotEmpty ? 1 : 0),
      };
    }).toList(growable: false);
  }

  List<Map<String, dynamic>> _filteredDrivers() {
    final q = _searchCtrl.text.trim().toLowerCase();
    if (q.isEmpty) return _drivers;

    return _drivers.where((d) {
      final hay = [
        (d['name'] ?? '').toString(),
        (d['mobile'] ?? '').toString(),
        (d['cab_no'] ?? '').toString(),
        (d['route_no'] ?? '').toString(),
        (d['updated_at'] ?? '').toString(),
        (d['status'] ?? '').toString(),
      ].join(' ').toLowerCase();
      return hay.contains(q);
    }).toList();
  }

  Future<void> _openInMaps(double lat, double lng) async {
    final url = Uri.parse('https://www.google.com/maps?q=$lat,$lng');
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      toast('Could not open Google Maps');
    }
  }

  String _timeAgo(String? iso) {
    if (iso == null || iso.trim().isEmpty) return '-';
    DateTime? dt;
    try {
      dt = DateTime.parse(iso).toLocal();
    } catch (_) {
      return iso;
    }
    final diff = DateTime.now().difference(dt);
    if (diff.inSeconds < 10) return 'just now';
    if (diff.inMinutes < 1) return '${diff.inSeconds}s ago';
    if (diff.inHours < 1) return '${diff.inMinutes}m ago';
    if (diff.inDays < 1) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  @override
  Widget build(BuildContext context) {
    final drivers = _filteredDrivers();
    final assignedCount =
        _drivers.where((d) => (_int(d['is_assigned'] ?? 0) ?? 0) == 1).length;
    final withLocationCount = _drivers
        .where((d) => _dbl(d['lat']) != null && _dbl(d['lng']) != null)
        .length;
    final isWide = MediaQuery.of(context).size.width >= 980;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Live Driver Tracking'),
        actions: [
          IconButton(
            onPressed: () => _fetchDrivers(showLoader: true),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: () => _fetchDrivers(showLoader: true),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.md,
                AppSpacing.sm,
                AppSpacing.md,
                AppSpacing.lg,
              ),
              children: [
                _heroPanel(),
                const SizedBox(height: 12),
                _card(
                  title: 'Live Metrics',
                  child: isWide
                      ? Row(
                          children: [
                            _metricCard(
                              icon: Icons.radar_rounded,
                              label: 'Online',
                              value: '${_drivers.length}',
                              accent: AppThemeColors.success,
                            ),
                            const SizedBox(width: 10),
                            _metricCard(
                              icon: Icons.route_rounded,
                              label: 'Assigned',
                              value: '$assignedCount',
                              accent: AppThemeColors.warning,
                            ),
                            const SizedBox(width: 10),
                            _metricCard(
                              icon: Icons.place_rounded,
                              label: 'Location Active',
                              value: '$withLocationCount',
                              accent: AppThemeColors.infoLight,
                            ),
                            const SizedBox(width: 10),
                            _metricCard(
                              icon: Icons.schedule_rounded,
                              label: 'Last Sync',
                              value: _lastRefresh == null
                                  ? '-'
                                  : '${_lastRefresh!.hour.toString().padLeft(2, '0')}:${_lastRefresh!.minute.toString().padLeft(2, '0')}',
                              accent: AppThemeColors.secondary,
                            ),
                          ],
                        )
                      : Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            _metricCard(
                              icon: Icons.radar_rounded,
                              label: 'Online',
                              value: '${_drivers.length}',
                              accent: AppThemeColors.success,
                              compact: true,
                            ),
                            _metricCard(
                              icon: Icons.route_rounded,
                              label: 'Assigned',
                              value: '$assignedCount',
                              accent: AppThemeColors.warning,
                              compact: true,
                            ),
                            _metricCard(
                              icon: Icons.place_rounded,
                              label: 'Location Active',
                              value: '$withLocationCount',
                              accent: AppThemeColors.infoLight,
                              compact: true,
                            ),
                            _metricCard(
                              icon: Icons.schedule_rounded,
                              label: 'Last Sync',
                              value: _lastRefresh == null
                                  ? '-'
                                  : '${_lastRefresh!.hour.toString().padLeft(2, '0')}:${_lastRefresh!.minute.toString().padLeft(2, '0')}',
                              accent: AppThemeColors.secondary,
                              compact: true,
                            ),
                          ],
                        ),
                ),
                const SizedBox(height: 12),
                _card(
                  title: 'Search Drivers',
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: _deco(
                      'Search by name, cab, route, mobile',
                      'ex: Rahul, MH12, assigned',
                      Icons.search_rounded,
                    ),
                    onChanged: (_) => safeSetState(() {}),
                  ),
                ),
                if (_loading) ...[
                  const SizedBox(height: 12),
                  const LinearProgressIndicator(
                    minHeight: 3,
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  _msg(_error!, error: true),
                ],
                const SizedBox(height: 12),
                _card(
                  title: 'Driver Grid',
                  child: drivers.isEmpty
                      ? _hint('No online drivers found.')
                      : AnimatedSwitcher(
                          duration: const Duration(milliseconds: 280),
                          child: isWide
                              ? GridView.builder(
                                  key: ValueKey<String>(
                                      'grid_${drivers.length}'),
                                  shrinkWrap: true,
                                  physics: const NeverScrollableScrollPhysics(),
                                  itemCount: drivers.length,
                                  gridDelegate:
                                      const SliverGridDelegateWithFixedCrossAxisCount(
                                    crossAxisCount: 2,
                                    crossAxisSpacing: 10,
                                    mainAxisSpacing: 10,
                                    mainAxisExtent: 230,
                                  ),
                                  itemBuilder: (_, i) =>
                                      _driverTile(drivers[i]),
                                )
                              : Column(
                                  key: ValueKey<String>(
                                      'list_${drivers.length}'),
                                  children: drivers.map(_driverTile).toList(),
                                ),
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _heroPanel() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        gradient: AppGradients.cardGradient,
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.55),
        ),
        boxShadow: AppShadows.card,
      ),
      child: Row(
        children: [
          Container(
            height: 48,
            width: 48,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadius.sm),
              color: AppThemeColors.primary.withValues(alpha: 0.14),
              border: Border.all(
                color: AppThemeColors.primary.withValues(alpha: 0.45),
              ),
            ),
            child: const Icon(
              Icons.gps_fixed_rounded,
              color: AppThemeColors.primary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Fleet Pulse',
                  style: AppTypography.titleMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Real-time driver visibility, route state and location freshness.',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _metricCard({
    required IconData icon,
    required String label,
    required String value,
    required Color accent,
    bool compact = false,
  }) {
    return Expanded(
      flex: compact ? 0 : 1,
      child: Container(
        constraints: compact ? const BoxConstraints(minWidth: 150) : null,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        decoration: BoxDecoration(
          color: AppThemeColors.cardGlass,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          border: Border.all(color: accent.withValues(alpha: 0.45)),
        ),
        child: Row(
          children: [
            Icon(icon, size: 18, color: accent),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textSecondary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _driverTile(Map<String, dynamic> d) {
    final name = (d['name'] ?? 'Driver').toString();
    final mobile = (d['mobile'] ?? '-').toString();
    final cab = (d['cab_no'] ?? '-').toString();
    final route = (d['route_no'] ?? '-').toString();
    final updatedAt = (d['updated_at'] ?? d['last_seen'] ?? '').toString();

    final lat = _dbl(d['lat']);
    final lng = _dbl(d['lng']);

    final assigned = (_int(d['is_assigned'] ?? 0) ?? 0) == 1;
    final badgeColor =
        assigned ? AppThemeColors.warning : AppThemeColors.success;
    final badgeText = assigned ? 'ASSIGNED' : 'ONLINE';

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.surface.withValues(alpha: 0.86),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.45),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 16,
                backgroundColor: AppThemeColors.primary.withValues(alpha: 0.18),
                child: Text(
                  name.isNotEmpty ? name[0].toUpperCase() : 'D',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '$name - $mobile',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w900,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              _statusBadge(badgeText, badgeColor),
            ],
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _badge('Cab: $cab'),
              if (route != '-' && route.trim().isNotEmpty)
                _badge('Route: $route'),
              _badge('Last seen: ${_timeAgo(updatedAt)}'),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            (lat == null || lng == null)
                ? 'Location: not available'
                : 'Location: $lat, $lng',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: (lat == null || lng == null)
                      ? null
                      : () => _openInMaps(lat, lng),
                  icon: const Icon(Icons.map),
                  label: const Text('Track Map'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () =>
                      toast('Driver: $name | Cab: $cab | Route: $route'),
                  icon: const Icon(Icons.info_outline),
                  label: const Text('Quick Info'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

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
        color: accent.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
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

  Widget _hint(String t) => Text(t,
      style: AppTypography.bodySmall.copyWith(
        color: AppThemeColors.textSecondary,
      ));

  InputDecoration _deco(String label, String hint, IconData icon) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: Icon(icon, size: 20),
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

  Widget _statusBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        text,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
