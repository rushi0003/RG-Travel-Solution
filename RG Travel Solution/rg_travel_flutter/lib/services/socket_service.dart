import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:flutter/foundation.dart';
import 'package:rg_travel_flutter/services/auth_service.dart';

class SocketService {
  late IO.Socket _socket;
  bool _isConnected = false;

  bool get isConnected => _isConnected;

  void initSocket(String token) {
    if (_isConnected) return;

    final uri = AuthService.baseUrl; // Reuse base URL from AuthService

    try {
      _socket = IO.io(uri, IO.OptionBuilder()
          .setTransports(['websocket']) // for Flutter or Dart VM
          .setExtraHeaders({'Authorization': 'Bearer $token'}) // Optional: if backend checks handshake headers
          .setAuth({'token': token}) // Standard way for socket.io auth
          .disableAutoConnect() // disable auto-connection
          .build());

      _socket.connect();

      _socket.onConnect((_) {
        debugPrint('Socket connected: ${_socket.id}');
        _isConnected = true;
      });

      _socket.onDisconnect((_) {
        debugPrint('Socket disconnected');
        _isConnected = false;
      });

      _socket.onConnectError((err) {
        debugPrint('Socket connection error: $err');
      });

      _socket.onError((err) {
        debugPrint('Socket error: $err');
      });

    } catch (e) {
      debugPrint('Socket init error: $e');
    }
  }

  // Warning fix: declare the callback return type explicitly.
  void onTripAssigned(void Function(dynamic data) callback) {
    _socket.on('trip_assigned', (data) {
      debugPrint('Trip Assigned Event: $data');
      callback(data);
    });
  }

  // Warning fix: declare the callback return type explicitly.
  void onTripUpdated(void Function(dynamic data) callback) {
    _socket.on('trip_updated', (data) {
      debugPrint('Trip Updated Event: $data');
      callback(data);
    });
  }

  void dispose() {
    _socket.disconnect();
    _socket.dispose();
    _isConnected = false;
  }
}
