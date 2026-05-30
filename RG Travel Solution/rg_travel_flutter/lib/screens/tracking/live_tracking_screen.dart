import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

import '../../core/config/env.dart';
import '../../core/storage/session_store.dart';
import '../../core/theme/app_theme.dart';
import '../../services/location_service.dart';
import '../../widgets/tracking/osm_live_map.dart';

class LiveTrackingScreen extends StatefulWidget {
  const LiveTrackingScreen({
    super.key,
    required this.routeNo,
    this.driverName,
    this.tripId,
  });

  final String routeNo;
  final String? driverName;
  final int? tripId;

  @override
  State<LiveTrackingScreen> createState() => _LiveTrackingScreenState();
}

class _LiveTrackingScreenState extends State<LiveTrackingScreen> {
  final MapController _mapController = MapController();

  StreamSubscription<Map<String, dynamic>>? _locationSub;
  StreamSubscription<bool>? _connectionSub;
  StreamSubscription<String>? _errorSub;
  Timer? _pollingTimer;

  final List<LatLng> _routeHistory = [];
  final List<Marker> _markers = [];
  LatLng? _currentPos;
  bool _isConnected = false;
  String? _statusMessage;

  double? _speed;
  DateTime? _lastUpdate;
  DateTime? _lastFetchSuccessAt;
  String? _lastFetchError;
  bool _initialLoad = true;
  bool _isStale = false;

  Map<String, dynamic>? _tripData;

  @override
  void initState() {
    super.initState();
    _statusMessage = 'Connecting...';
    _boot();
  }

  Future<void> _boot() async {
    await _fetchLatestLocation();
    await _fetchRouteHistory();
    if (widget.tripId != null) {
      await _fetchTripDetails();
    }

    final token = await SessionStore.getToken();
    if (token != null) {
      LocationService().initialize(token);
      LocationService().joinRoute(widget.routeNo);
    }

    _locationSub =
        LocationService().driverLocationStream.listen(_onLocationUpdate);

    _connectionSub =
        LocationService().connectionStatusStream.listen((connected) {
      if (!mounted) return;
      setState(() {
        _isConnected = connected;
        _refreshStatusMessage();
      });
    });

    _errorSub = LocationService().errorStream.listen((err) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err), backgroundColor: AppThemeColors.errorDark),
      );
    });

    if (LocationService().isConnected && mounted) {
      setState(() {
        _isConnected = true;
        _refreshStatusMessage();
      });
    }

    _startPollingFallback();
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    LocationService().leaveRoute();
    _locationSub?.cancel();
    _connectionSub?.cancel();
    _errorSub?.cancel();
    super.dispose();
  }

  Future<void> _fetchTripDetails() async {
    if (widget.tripId == null) return;
    try {
      final token = await SessionStore.getToken();
      final url = Uri.parse('${Env.baseUrl}/api/v2/trips/${widget.tripId}');
      final res =
          await http.get(url, headers: {'Authorization': 'Bearer $token'});
      if (res.statusCode != 200) return;

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      if (data['success'] == true && mounted) {
        setState(() {
          _tripData = data['data'] as Map<String, dynamic>?;
          _rebuildMarkers();
        });
      }
    } catch (_) {}
  }

  Future<void> _fetchLatestLocation() async {
    try {
      final token = await SessionStore.getToken();
      final url = Uri.parse(
          '${Env.baseUrl}/api/tracking/route/${widget.routeNo}/latest');
      final res =
          await http.get(url, headers: {'Authorization': 'Bearer $token'});
      if (res.statusCode != 200) {
        if (mounted) {
          setState(() {
            _lastFetchError =
                'Latest location fetch failed (HTTP ${res.statusCode})';
          });
        }
        return;
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      if (data['success'] != true || data['location'] == null) {
        if (mounted) {
          setState(() {
            _lastFetchError = 'Latest location not available';
          });
        }
        return;
      }

      final loc = data['location'] as Map<String, dynamic>;
      final lat = double.tryParse(loc['latitude'].toString());
      final lng = double.tryParse(loc['longitude'].toString());
      final speed = double.tryParse(loc['speed'].toString()) ?? 0.0;
      final heading = double.tryParse(loc['heading'].toString()) ?? 0.0;
      final ts = _parseDateTime(loc['timestamp']);
      if (lat != null && lng != null) {
        _updateMapState(LatLng(lat, lng), speed, heading, ts);
      }
      if (mounted) {
        setState(() {
          _lastFetchSuccessAt = DateTime.now().toUtc();
          _lastFetchError = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _lastFetchError = 'Latest location fetch failed: $e';
        });
      }
    } finally {
      if (mounted) {
        setState(() => _initialLoad = false);
      }
    }
  }

  Future<void> _fetchRouteHistory() async {
    try {
      final token = await SessionStore.getToken();
      final url = Uri.parse(
          '${Env.baseUrl}/api/tracking/route/${widget.routeNo}/history?duration=30');
      final res =
          await http.get(url, headers: {'Authorization': 'Bearer $token'});
      if (res.statusCode != 200) {
        if (mounted && _routeHistory.isEmpty) {
          setState(() {
            _lastFetchError =
                'Route history fetch failed (HTTP ${res.statusCode})';
          });
        }
        return;
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      if (data['success'] != true) return;

      final points = data['points'] as List<dynamic>? ?? <dynamic>[];
      if (!mounted) return;
      setState(() {
        _routeHistory
          ..clear()
          ..addAll(
            points.map((p) {
              final row = p as Map<String, dynamic>;
              return LatLng(
                double.parse(row['lat'].toString()),
                double.parse(row['lng'].toString()),
              );
            }),
          );
        _lastFetchSuccessAt = DateTime.now().toUtc();
        _lastFetchError = null;
      });
    } catch (e) {
      if (mounted && _routeHistory.isEmpty) {
        setState(() {
          _lastFetchError = 'Route history fetch failed: $e';
        });
      }
    }
  }

  void _onLocationUpdate(Map<String, dynamic> data) {
    if (data['routeNo'] != widget.routeNo) return;

    final lat = double.tryParse(data['lat'].toString());
    final lng = double.tryParse(data['lng'].toString());
    final speed = double.tryParse(data['speed'].toString()) ?? 0.0;
    final heading = double.tryParse(data['heading'].toString()) ?? 0.0;
    final ts = _parseDateTime(data['timestamp'] ?? data['serverTime']);
    if (lat == null || lng == null) return;

    setState(() {
      _routeHistory.add(LatLng(lat, lng));
      if (_routeHistory.length > 200) {
        _routeHistory.removeAt(0);
      }
    });
    _updateMapState(
        LatLng(lat, lng), speed, heading, ts ?? DateTime.now().toUtc());
  }

  void _updateMapState(
      LatLng pos, double speed, double heading, DateTime? time) {
    if (!mounted) return;
    setState(() {
      _currentPos = pos;
      _speed = speed;
      _lastUpdate = time;
      _refreshStaleStatus();
      _rebuildMarkers();
    });
    _mapController.move(pos, 16);
  }

  void _rebuildMarkers() {
    if (_currentPos == null) return;

    final items = <Marker>[
      Marker(
        point: _currentPos!,
        width: 48,
        height: 48,
        alignment: Alignment.center,
        child: const Icon(Icons.navigation,
            color: AppThemeColors.primary, size: 32),
      ),
    ];

    final office = _tripData?['office_location'];
    if (office is Map) {
      final lat = double.tryParse((office['lat'] ?? '').toString());
      final lng = double.tryParse((office['lng'] ?? '').toString());
      if (lat != null && lng != null) {
        items.add(
          Marker(
            point: LatLng(lat, lng),
            width: 40,
            height: 40,
            alignment: Alignment.center,
            child: const Icon(Icons.business,
                color: AppThemeColors.secondary, size: 26),
          ),
        );
      }
    }

    final tripType = (_tripData?['trip_type'] ?? '').toString();
    final employees = _tripData?['employees'] as List<dynamic>? ?? <dynamic>[];
    for (final raw in employees) {
      if (raw is! Map) continue;
      final lat = double.tryParse(
          (tripType == 'pickup' ? raw['pickup_lat'] : raw['drop_lat'])
              .toString());
      final lng = double.tryParse(
          (tripType == 'pickup' ? raw['pickup_lng'] : raw['drop_lng'])
              .toString());
      if (lat == null || lng == null) continue;
      items.add(
        Marker(
          point: LatLng(lat, lng),
          width: 26,
          height: 26,
          alignment: Alignment.center,
          child: Container(
            decoration: BoxDecoration(
              color: AppThemeColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: AppThemeColors.primary.withValues(alpha: 0.35)),
            ),
            child: const Icon(Icons.person_pin_circle,
                size: 18, color: AppThemeColors.warning),
          ),
        ),
      );
    }

    _markers
      ..clear()
      ..addAll(items);
  }

  void _startPollingFallback() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) async {
      await _fetchLatestLocation();
      if (_routeHistory.isEmpty) {
        await _fetchRouteHistory();
      }
      if (mounted) {
        setState(_refreshStaleStatus);
      }
    });
  }

  void _refreshStaleStatus() {
    final now = DateTime.now().toUtc();
    final last = _lastUpdate?.toUtc();
    _isStale = last == null || now.difference(last).inSeconds > 60;
    _refreshStatusMessage();
  }

  void _refreshStatusMessage() {
    if (!_isConnected) {
      _statusMessage = 'Reconnecting...';
      return;
    }
    _statusMessage = _isStale ? 'Live (stale)' : 'Live';
  }

  Future<void> _refreshNow() async {
    await _fetchLatestLocation();
    await _fetchRouteHistory();
    if (mounted) {
      setState(_refreshStaleStatus);
    }
  }

  DateTime? _parseDateTime(dynamic input) {
    if (input == null) return null;
    return DateTime.tryParse(input.toString())?.toUtc();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          _currentPos == null ? _buildWaitingView() : _buildOsmMap(),
          _buildHeader(context),
          _buildHealthBanner(context),
          if (_currentPos != null) _buildBottomInfo(),
        ],
      ),
    );
  }

  Widget _buildWaitingView() {
    return Container(
      color: AppThemeColors.background,
      child: Center(
        child: _initialLoad
            ? const CircularProgressIndicator(color: AppThemeColors.primary)
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.location_off,
                      color: AppThemeColors.textSecondary, size: 48),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    'Waiting for location updates...',
                    style: AppTypography.bodyMedium
                        .copyWith(color: AppThemeColors.textSecondary),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  TextButton(
                    onPressed: _refreshNow,
                    child: Text(
                      'Retry Fetch',
                      style: AppTypography.labelLarge
                          .copyWith(color: AppThemeColors.secondary),
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _buildOsmMap() {
    return OsmLiveMap(
      mapController: _mapController,
      initialCenter: _currentPos!,
      routeHistory: _routeHistory,
      markers: _markers,
      polylineColor: AppThemeColors.primary.withValues(alpha: 0.75),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        color: _isConnected
            ? AppThemeColors.background.withValues(alpha: 0.9)
            : AppThemeColors.error.withValues(alpha: 0.9),
        padding: EdgeInsets.fromLTRB(
          AppSpacing.md,
          MediaQuery.of(context).padding.top + 10,
          AppSpacing.md,
          AppSpacing.md,
        ),
        child: Row(
          children: [
            GestureDetector(
              onTap: () => Navigator.pop(context),
              child: const Icon(Icons.arrow_back,
                  color: AppThemeColors.textPrimary),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Route ${widget.routeNo}',
                    style: AppTypography.titleMedium.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: !_isConnected
                              ? AppThemeColors.textSecondary
                              : (_isStale
                                  ? AppThemeColors.warning
                                  : AppThemeColors.success),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _statusMessage ?? 'Connecting...',
                        style: AppTypography.labelSmall
                            .copyWith(color: AppThemeColors.textSecondary),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHealthBanner(BuildContext context) {
    final hasIssue = !_isConnected || _isStale || _lastFetchError != null;
    if (!hasIssue) {
      return const SizedBox.shrink();
    }

    final topInset = MediaQuery.of(context).padding.top + 78;
    final title = _lastFetchError != null
        ? _lastFetchError!
        : (!_isConnected
            ? 'Connection lost. Showing last known location.'
            : 'Live feed stale. Last update is delayed.');
    final bg = _lastFetchError != null
        ? AppThemeColors.error.withValues(alpha: 0.18)
        : (_isConnected
            ? AppThemeColors.warning.withValues(alpha: 0.18)
            : AppThemeColors.error.withValues(alpha: 0.18));
    final borderColor = _lastFetchError != null
        ? AppThemeColors.error
        : (_isConnected ? AppThemeColors.warning : AppThemeColors.error);
    final subtitle = _lastFetchSuccessAt != null
        ? 'Last sync: ${_formatTime(_lastFetchSuccessAt!)}'
        : null;

    return Positioned(
      left: AppSpacing.md,
      right: AppSpacing.md,
      top: topInset,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(color: borderColor),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, color: borderColor, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: AppTypography.labelSmall
                          .copyWith(color: AppThemeColors.textPrimary)),
                  if (subtitle != null)
                    Text(subtitle,
                        style: AppTypography.labelSmall
                            .copyWith(color: AppThemeColors.textSecondary)),
                ],
              ),
            ),
            TextButton(onPressed: _refreshNow, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomInfo() {
    return Positioned(
      bottom: 20,
      left: AppSpacing.md,
      right: AppSpacing.md,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppThemeColors.cardGlass.withValues(alpha: 0.95),
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: AppThemeColors.border),
          boxShadow: AppShadows.card,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppThemeColors.info.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child:
                  const Icon(Icons.directions_car, color: AppThemeColors.info),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.driverName ?? 'Assigned Driver',
                    style: AppTypography.titleSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _lastUpdate != null
                        ? 'Updated ${_formatTime(_lastUpdate!)} (${_timeAgo(_lastUpdate!)})'
                        : 'Just now',
                    style: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textSecondary),
                  ),
                ],
              ),
            ),
            Column(
              children: [
                Text(
                  ((_speed ?? 0) * 3.6).toStringAsFixed(0),
                  style: AppTypography.headlineMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text('km/h',
                    style: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textSecondary)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
  }

  String _timeAgo(DateTime dt) {
    final seconds = DateTime.now().toUtc().difference(dt.toUtc()).inSeconds;
    if (seconds < 60) return '${seconds}s ago';
    return '${seconds ~/ 60}m ago';
  }
}
