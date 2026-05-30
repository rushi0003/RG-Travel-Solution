import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:socket_io_client/socket_io_client.dart' as io;
import 'package:http/http.dart' as http;

import '../core/config/env.dart';

class LocationService {
  // Singleton
  static final LocationService _instance = LocationService._internal();
  factory LocationService() => _instance;
  LocationService._internal();

  io.Socket? _socket;
  StreamSubscription<Position>? _positionStreamSubscription;
  String? _currentRouteNo;
  String? _authToken;

  // Stream controller for location updates (for listeners like Admin/Employee)
  final _driverLocationController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get driverLocationStream => _driverLocationController.stream;

  // Connection Status (true = connected, false = disconnected)
  final _connectionStatusController = StreamController<bool>.broadcast();
  Stream<bool> get connectionStatusStream => _connectionStatusController.stream;

  // Error Stream
  final _errorController = StreamController<String>.broadcast();
  Stream<String> get errorStream => _errorController.stream;
  
  // Upload status stream for driver-side tracking reliability
  final _uploadStatusController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get uploadStatusStream => _uploadStatusController.stream;

  // Socket reconnect with exponential backoff
  int _reconnectAttempts = 0;
  Timer? _reconnectTimer;
  String? _pendingJoinRouteNo;
  DateTime? _lastSuccessfulUploadAt;
  String? _lastUploadError;
  int? _lastUploadServerCode;

  bool get isConnected => _socket?.connected ?? false;
  DateTime? get lastSuccessfulUploadAt => _lastSuccessfulUploadAt;
  String? get lastUploadError => _lastUploadError;
  int? get lastUploadServerCode => _lastUploadServerCode;

  /// Initialize Socket connection
  void initialize(String token) {
    _authToken = token;
    if (_socket != null) {
      if (!_socket!.connected) {
        _socket!.connect();
      }
      return;
    }

    // Use Env.apiBaseUrl but trim '/api' if present to get root URL for socket
    // Or just use the hostname + port. 
    // Usually socket.io connects to root, e.g. http://192.168.x.x:5000
    // Env.apiBaseUrl might be "http://192.168.x.x:5000" or ".../api"
    // Let's assume Env.apiBaseUrl is the base host for now.
    
    // Construct Socket URI
    // socket_io_client needs just the host usually, namespacing is handled separately
    // If Env.apiBaseUrl is "http://10.0.2.2:5000", that's perfect.
    
    _socket = io.io(Env.baseUrl, io.OptionBuilder()
      .setTransports(['websocket']) // for Flutter or Dart VM
      .setExtraHeaders({'Authorization': 'Bearer $token'}) // Auth Header
      .disableAutoConnect() // Connect manually
      .build());

    _socket!.connect();

    _socket!.onConnect((_) {
      debugPrint('âœ… Socket Connected');
      _connectionStatusController.add(true);
      _reconnectAttempts = 0;  // Reset on successful connect
      _reconnectTimer?.cancel();
      final routeToJoin = _pendingJoinRouteNo ?? _currentRouteNo;
      if (routeToJoin != null && routeToJoin.isNotEmpty) {
        _emitJoinRoute(routeToJoin);
      }
    });

    _socket!.onConnectError((data) {
      debugPrint('âŒ Socket Connect Error: $data');
      _errorController.add('Socket connect error: $data');
      _connectionStatusController.add(false);
    });

    _socket!.onDisconnect((_) {
      debugPrint('âŒ Socket Disconnected');
      _connectionStatusController.add(false);
      _scheduleSocketReconnect();  // Auto-reconnect
    });

    _socket!.onError((data) {
      debugPrint('âŒ Socket Error: $data');
      _errorController.add("Connection Error: $data");
      _connectionStatusController.add(false);
    });

    // Listen for broadcast events (Admin/Employee view)
    _socket!.on('driver_location_update', (data) {
      if (data != null) {
        debugPrint('ðŸ“¡ Location Recv: $data');
        _driverLocationController.add(Map<String, dynamic>.from(data as Map));
      }
    });

    _socket!.on('tracking_error', (data) {
      debugPrint('âŒ Tracking Error: $data');
      _errorController.add("Tracking Error: $data");
    });

    _socket!.on('joined_route', (data) {
      if (data is Map) {
        final joinedRoute = (data['routeNo'] ?? '').toString();
        if (joinedRoute.isNotEmpty) {
          _currentRouteNo = joinedRoute;
          if (_pendingJoinRouteNo == joinedRoute) {
            _pendingJoinRouteNo = null;
          }
        }
      }
    });
  }

  /// Join a specific route room to listen for updates (Admin/Employee)
  void joinRoute(String routeNo) {
    _currentRouteNo = routeNo;
    _pendingJoinRouteNo = routeNo;
    if (_socket == null) {
      debugPrint('Socket not initialized. Route join queued.');
      return;
    }

    // Remove old listener to avoid duplicates
    _socket!.off('driver_location_update');

    // Add new listener
    _socket!.on('driver_location_update', (data) {
      if (data != null) {
        debugPrint('Location Recv: $data');
        _driverLocationController.add(Map<String, dynamic>.from(data as Map));
      }
    });

    // Emit now if connected, otherwise queue for onConnect.
    if (_socket!.connected) {
      _emitJoinRoute(routeNo);
    } else {
      debugPrint('Socket not connected. Route join queued.');
    }
  }
  /// Leave current route room
  void leaveRoute() {
    if (_currentRouteNo != null && _socket != null) {
      _socket!.emit('leave_route', {'routeNo': _currentRouteNo});
      _currentRouteNo = null;
    }
    _pendingJoinRouteNo = null;
  }

  /// Stop all services
  void dispose() {
    stopBroadcasting();
    leaveRoute();
    _reconnectTimer?.cancel();
    _socket?.disconnect();
    _socket = null;
  }

  /// Schedule socket reconnect with exponential backoff
  void _scheduleSocketReconnect() {
    _reconnectTimer?.cancel();
    
    // Exponential backoff: 2, 4, 8, 16, 30 seconds max
    final delaySeconds = (2 << _reconnectAttempts).clamp(2, 30);
    _reconnectAttempts = (_reconnectAttempts + 1).clamp(0, 5);
    
    _reconnectTimer = Timer(Duration(seconds: delaySeconds), () {
      if (_socket != null && !_socket!.connected) {
        debugPrint('ðŸ”„ Reconnecting socket (attempt $_reconnectAttempts)...');
        _socket!.connect();
      }
    });
    
    if (kDebugMode) {
      debugPrint('â±ï¸ Socket reconnect scheduled in $delaySeconds seconds');
    }
  }

  void _emitJoinRoute(String routeNo) {
    _pendingJoinRouteNo = routeNo;
    _socket?.emit('join_route', {
      'routeNo': routeNo,
      'token': _authToken,
    });
  }

  // ----------------------------------------------------------------------
  // DRIVER BROADCASTING LOGIC
  // ----------------------------------------------------------------------

  Timer? _broadcastTimer;
  Position? _lastPosition;
  bool _isBroadcasting = false;
  
  // Reliability: Single latest unsent location (not queue)
  Map<String, dynamic>? _latestUnsentPayload;
  bool _isUploading = false;
  
  // Exponential backoff retry
  int _retryAttempts = 0;
  Timer? _retryTimer;

  /// Check GPS and location permissions
  Future<Map<String, bool>> checkGPSAndPermissions() async {
    final bool gpsEnabled = await Geolocator.isLocationServiceEnabled();
    final LocationPermission permission = await Geolocator.checkPermission();
    
    return {
      'gpsEnabled': gpsEnabled,
      'permissionGranted': permission == LocationPermission.always || 
                           permission == LocationPermission.whileInUse
    };
  }

  /// Start broadcasting driver location to API
  /// Returns true if started successfully, false if permissions/service disabled.
  Future<bool> startBroadcasting({required String routeNo}) async {
    if (_isBroadcasting) return true;

    // 1. Check Service Status
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      debugPrint('âŒ Location services are disabled.');
      return false; // UI should handle prompting user to enable it
    }

    // 2. Check Permissions
    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        debugPrint('âŒ Location permissions denied');
        return false;
      }
    }
    
    if (permission == LocationPermission.deniedForever) {
      debugPrint('âŒ Location permissions permanently denied');
      return false;
    }

    _isBroadcasting = true;
    _currentRouteNo = routeNo;

    // 3. Start Stream (High Accuracy, but we throttle sending)
    const locationSettings = LocationSettings(
      accuracy: LocationAccuracy.bestForNavigation,
      distanceFilter: 0, // Get all updates, we filter by time
    );

    _positionStreamSubscription?.cancel();
    _positionStreamSubscription = Geolocator.getPositionStream(locationSettings: locationSettings)
        .listen((Position position) {
      _lastPosition = position;
    });

    // 4. Start 8-second Timer for Network Push
    _broadcastTimer?.cancel();
    _broadcastTimer = Timer.periodic(const Duration(seconds: 8), (timer) {
      if (_lastPosition != null) {
        _queueAndSend(_lastPosition!, routeNo);
      }
      // Retry queued items
      // Retry logic handled by _scheduleRetry on failure
    });

    debugPrint('ðŸš€ Broadcasting started for Route: $routeNo');
    return true;
  }

  /// Trigger an immediate upload attempt (used by manual "Retry now" actions).
  Future<void> forceUploadNow({String? routeNo}) async {
    final activeRoute = (routeNo != null && routeNo.isNotEmpty) ? routeNo : _currentRouteNo;
    if (activeRoute == null || activeRoute.isEmpty) {
      _errorController.add('Cannot retry upload: route is missing.');
      return;
    }

    if (_lastPosition != null) {
      _queueAndSend(_lastPosition!, activeRoute);
      return;
    }

    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        _errorController.add('GPS is disabled. Enable location services to retry.');
        return;
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        _errorController.add('Location permission denied.');
        return;
      }

      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      ).timeout(const Duration(seconds: 8));
      _lastPosition = pos;
      _queueAndSend(pos, activeRoute);
    } catch (e) {
      _lastUploadError = 'Manual retry failed: $e';
      _uploadStatusController.add({
        'ok': false,
        'routeNo': activeRoute,
        'error': _lastUploadError,
        'at': DateTime.now().toUtc().toIso8601String(),
      });
    }
  }

  /// Stop broadcasting
  void stopBroadcasting() {
    _isBroadcasting = false;
    _positionStreamSubscription?.cancel();
    _positionStreamSubscription = null;
    _broadcastTimer?.cancel();
    _broadcastTimer = null;
    _retryTimer?.cancel();
    _retryTimer = null;
    _lastPosition = null;
    _latestUnsentPayload = null;
    _retryAttempts = 0;
    debugPrint('ðŸ›‘ Broadcasting stopped');
  }

  void _queueAndSend(Position pos, String routeNo) {
    final payload = {
      'routeNo': routeNo,
      'lat': pos.latitude,
      'lng': pos.longitude,
      'speed': pos.speed, // m/s
      'heading': pos.heading,
      'accuracy': pos.accuracy,
      'deviceTime': DateTime.now().toIso8601String(),
    };
    
    // Payload already set in _latestUnsentPayload by _queueAndSend
    _latestUnsentPayload = payload;
    _sendLatestLocation();
  }

  Future<void> _sendLatestLocation() async {
    if (_isUploading || _latestUnsentPayload == null || _authToken == null) return;

    _isUploading = true;
    final payload = _latestUnsentPayload!;

    try {
      final url = Uri.parse('${Env.baseUrl}/api/driver/location');
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_authToken',
        },
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Success - clear unsent payload and reset retry
        _latestUnsentPayload = null;
        _retryAttempts = 0;
        _retryTimer?.cancel();
        _lastSuccessfulUploadAt = DateTime.now().toUtc();
        _lastUploadError = null;
        _lastUploadServerCode = response.statusCode;
        _uploadStatusController.add({
          'ok': true,
          'routeNo': payload['routeNo'],
          'serverCode': response.statusCode,
          'at': _lastSuccessfulUploadAt!.toIso8601String(),
        });
        if (kDebugMode) {
          debugPrint('âœ… Location Sent: ${payload['lat']},${payload['lng']}');
        }
      } else if (response.statusCode == 429) {
        // Rate-limit at backend (non-fatal): keep latest payload and retry quickly.
        _lastUploadError = 'Rate limited by server (429)';
        _lastUploadServerCode = response.statusCode;
        _uploadStatusController.add({
          'ok': false,
          'routeNo': payload['routeNo'],
          'serverCode': response.statusCode,
          'error': _lastUploadError,
          'at': DateTime.now().toUtc().toIso8601String(),
        });
        _scheduleRetry(secondsOverride: 2);
      } else if (response.statusCode == 401 || response.statusCode == 403) {
        // Auth failed -> Stop everything
        debugPrint('ðŸ›‘ Auth Failed (401/403). Stopping tracking.');
        stopBroadcasting();
        _lastUploadError = 'Authentication failed';
        _lastUploadServerCode = response.statusCode;
        _uploadStatusController.add({
          'ok': false,
          'routeNo': payload['routeNo'],
          'serverCode': response.statusCode,
          'error': _lastUploadError,
          'at': DateTime.now().toUtc().toIso8601String(),
        });
        _errorController.add('Authentication failed. Please log in again.');
      } else {
        // Server error - schedule retry with backoff
        debugPrint('âš ï¸ Upload failed: ${response.statusCode}');
        _lastUploadError = 'Upload failed with HTTP ${response.statusCode}';
        _lastUploadServerCode = response.statusCode;
        _uploadStatusController.add({
          'ok': false,
          'routeNo': payload['routeNo'],
          'serverCode': response.statusCode,
          'error': _lastUploadError,
          'at': DateTime.now().toUtc().toIso8601String(),
        });
        _scheduleRetry();
      }
    } catch (e) {
      debugPrint('âš ï¸ Network error: $e');
      _lastUploadError = 'Network error: $e';
      _lastUploadServerCode = null;
      _uploadStatusController.add({
        'ok': false,
        'routeNo': payload['routeNo'],
        'error': _lastUploadError,
        'at': DateTime.now().toUtc().toIso8601String(),
      });
      _scheduleRetry();
    } finally {
      _isUploading = false;
    }
  }

  /// Schedule retry with exponential backoff
  void _scheduleRetry({int? secondsOverride}) {
    _retryTimer?.cancel();
    
    // Exponential backoff: 2, 4, 8, 16, 32, max 60 seconds
    final delaySeconds = secondsOverride ?? (2 << _retryAttempts).clamp(2, 60);
    if (secondsOverride == null) {
      _retryAttempts = (_retryAttempts + 1).clamp(0, 5);
    }
    
    _retryTimer = Timer(Duration(seconds: delaySeconds), () {
      if (_latestUnsentPayload != null && _isBroadcasting) {
        _sendLatestLocation();
      }
    });
    
    if (kDebugMode) {
      debugPrint('â±ï¸ Retry scheduled in $delaySeconds seconds (attempt $_retryAttempts)');
    }
  }
}

