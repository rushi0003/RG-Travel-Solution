import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

import '../../core/config/env.dart';
import '../../core/storage/session_store.dart';
import '../../core/theme/app_theme.dart';
import '../../services/employee_service.dart';
import '../../services/location_service.dart';
import '../../widgets/tracking/osm_live_map.dart';

class EmployeeLiveTrackingScreen extends StatefulWidget {
  const EmployeeLiveTrackingScreen({super.key});

  @override
  State<EmployeeLiveTrackingScreen> createState() =>
      _EmployeeLiveTrackingScreenState();
}

class _EmployeeLiveTrackingScreenState
    extends State<EmployeeLiveTrackingScreen> {
  final MapController _mapController = MapController();

  StreamSubscription<Map<String, dynamic>>? _locationSub;
  StreamSubscription<bool>? _connectionSub;
  StreamSubscription<String>? _errorSub;
  Timer? _pollingTimer;

  bool _loading = true;
  String? _error;

  bool _hasActiveTrip = false;
  Map<String, dynamic>? _tripData;
  String? _routeNo;
  String? _driverName;
  String? _vehicleNo;
  String? _vehicleType;

  final List<LatLng> _routeHistory = [];
  final List<Marker> _markers = [];
  LatLng? _currentPos;
  bool _isConnected = false;
  String? _statusMessage;

  double? _speed;
  DateTime? _lastUpdate;
  DateTime? _lastFetchSuccessAt;
  String? _lastFetchError;
  bool _isStale = false;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      await _fetchAssignedTrip();
      if (_hasActiveTrip && _routeNo != null) {
        await _fetchLatestLocation();
        await _fetchRouteHistory();

        final token = await SessionStore.getToken();
        if (token != null) {
          LocationService().initialize(token);
          LocationService().joinRoute(_routeNo!);

          _locationSub =
              LocationService().driverLocationStream.listen(_onLocationUpdate);
          _connectionSub = LocationService()
              .connectionStatusStream
              .listen(_onConnectionChange);
          _errorSub = LocationService().errorStream.listen(_onError);

          if (LocationService().isConnected) {
            _onConnectionChange(true);
          }
          _startPollingFallback();
        }
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Failed to load trip: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _fetchAssignedTrip() async {
    final userIdStr = await SessionStore.getUserId();
    final token = await SessionStore.getToken();
    if (userIdStr == null || token == null) {
      throw 'User not logged in';
    }

    final userId = int.tryParse(userIdStr) ?? 0;
    final data = await EmployeeService.getMyTrip(userId, token: token);
    if (data == null || data['has_trip'] != true) return;

    final trip = data['trip'] as Map<String, dynamic>;
    final status = (trip['status'] ?? '').toString().toLowerCase();
    if (!['assigned', 'in_progress', 'started', 'active', 'live']
        .contains(status)) return;

    _hasActiveTrip = true;
    _tripData = Map<String, dynamic>.from(trip);
    _routeNo = trip['route_no']?.toString();
    _driverName = trip['driver_name']?.toString();
    _vehicleNo = trip['vehicle_no']?.toString();
    _vehicleType = trip['vehicle_type']?.toString();
  }

  Future<void> _fetchLatestLocation() async {
    if (_routeNo == null) return;
    try {
      final token = await SessionStore.getToken();
      final url =
          Uri.parse('${Env.baseUrl}/api/tracking/route/$_routeNo/latest');
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
    }
  }

  Future<void> _fetchRouteHistory() async {
    if (_routeNo == null) return;
    try {
      final token = await SessionStore.getToken();
      final url = Uri.parse(
          '${Env.baseUrl}/api/tracking/route/$_routeNo/history?duration=30');
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

  void _onConnectionChange(bool connected) {
    if (!mounted) return;
    setState(() {
      _isConnected = connected;
      _refreshStatusMessage();
    });
  }

  void _onError(String err) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(err), backgroundColor: AppThemeColors.errorDark),
    );
  }

  void _onLocationUpdate(Map<String, dynamic> data) {
    if (data['routeNo'] != _routeNo) return;

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
    _markers
      ..clear()
      ..add(
        Marker(
          point: _currentPos!,
          width: 48,
          height: 48,
          alignment: Alignment.center,
          child: const Icon(Icons.navigation,
              color: AppThemeColors.primary, size: 32),
        ),
      );
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
  void dispose() {
    _pollingTimer?.cancel();
    LocationService().leaveRoute();
    _locationSub?.cancel();
    _connectionSub?.cancel();
    _errorSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: AppThemeColors.background,
        body: Center(
            child: CircularProgressIndicator(color: AppThemeColors.primary)),
      );
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: AppThemeColors.background,
        appBar: AppBar(backgroundColor: Colors.transparent, elevation: 0),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Text(
              _error!,
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.error),
            ),
          ),
        ),
      );
    }

    if (!_hasActiveTrip) {
      return Scaffold(
        backgroundColor: AppThemeColors.background,
        appBar: AppBar(
          title: const Text('Live Tracking'),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.location_off,
                  size: AppIconSizes.xxl,
                  color: AppThemeColors.textDisabled,
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  'No Active Trip Assigned',
                  textAlign: TextAlign.center,
                  style: AppTypography.headlineLarge
                      .copyWith(color: AppThemeColors.textPrimary),
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'You can only track trips you are assigned to.',
                  textAlign: TextAlign.center,
                  style: AppTypography.bodyMedium
                      .copyWith(color: AppThemeColors.textTertiary),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      body: Stack(
        children: [
          _currentPos == null ? _buildWaitingView() : _buildOsmMap(),
          _buildHeader(context),
          _buildHealthBanner(context),
          if (_currentPos != null) _buildBottomCard(),
        ],
      ),
    );
  }

  Widget _buildWaitingView() {
    return Container(
      color: AppThemeColors.background,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.map,
                color: AppThemeColors.textTertiary, size: AppIconSizes.xxl),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Waiting for driver location...',
              style: AppTypography.bodyMedium
                  .copyWith(color: AppThemeColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.sm),
            OutlinedButton(
                onPressed: _refreshNow, child: const Text('Retry now')),
            if (_isConnected)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.sm),
                child: Text(
                  'Connected',
                  style: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.success),
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
      polylineColor: AppThemeColors.primary.withValues(alpha: 0.8),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final statusColor = !_isConnected
        ? AppThemeColors.error
        : (_isStale ? AppThemeColors.warning : AppThemeColors.success);

    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        color: AppThemeColors.background.withValues(alpha: 0.92),
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
                    'Trip #${_tripData?['id']}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.titleSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'Route $_routeNo • ${_tripData?['status']?.toString().toUpperCase()}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textSecondary),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(AppRadius.full),
                border: Border.all(color: statusColor.withValues(alpha: 0.45)),
              ),
              child: Text(
                (_statusMessage ??
                        (_isConnected
                            ? (_isStale ? 'STALE' : 'LIVE')
                            : 'OFFLINE'))
                    .toUpperCase(),
                style: AppTypography.labelSmall.copyWith(
                  color: statusColor,
                  fontWeight: FontWeight.bold,
                ),
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
        ? AppThemeColors.error.withValues(alpha: 0.20)
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

  Widget _buildBottomCard() {
    return Positioned(
      bottom: 20,
      left: AppSpacing.md,
      right: AppSpacing.md,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          gradient: AppGradients.cardGradient,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: AppThemeColors.border),
          boxShadow: AppShadows.card,
        ),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: AppThemeColors.primary.withValues(alpha: 0.16),
              child: const Icon(Icons.person, color: AppThemeColors.primary),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _driverName ?? 'Driver',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.titleSmall.copyWith(
                      color: AppThemeColors.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    '$_vehicleType • $_vehicleNo',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.labelSmall
                        .copyWith(color: AppThemeColors.textTertiary),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${((_speed ?? 0) * 3.6).toStringAsFixed(0)} km/h',
                  style: AppTypography.titleSmall.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  _lastUpdate != null ? _timeAgo(_lastUpdate!) : 'Now',
                  style: AppTypography.labelSmall
                      .copyWith(color: AppThemeColors.textTertiary),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _timeAgo(DateTime dt) {
    final seconds = DateTime.now().toUtc().difference(dt.toUtc()).inSeconds;
    if (seconds < 60) return '${seconds}s ago';
    return '${seconds ~/ 60}m ago';
  }

  String _formatTime(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
  }
}
