import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../config/env.dart';
import 'api_exception.dart';

class ApiResponse {
  ApiResponse({
    required this.statusCode,
    required this.raw,
    required this.data,
    required this.success,
    this.message,
  });

  final int statusCode;
  final Map<String, dynamic> raw;
  final dynamic data;
  final String? message;
  final bool success;
}

class ApiClient {
  ApiClient({
    http.Client? client,
    String? baseUrlOverride,
    Duration? timeout,
    Map<String, String>? defaultHeaders,
  })  : _client = client ?? http.Client(),
        _baseUrlOverride = baseUrlOverride,
        _timeout = timeout ?? const Duration(seconds: Env.httpTimeoutSeconds),
        _defaultHeaders = defaultHeaders ??
            const {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            };

  final http.Client _client;
  final String? _baseUrlOverride;
  final Duration _timeout;
  final Map<String, String> _defaultHeaders;

  String get baseUrl => _baseUrlOverride ?? Env.baseUrl;

  Uri buildUri(String endpoint, {Map<String, String>? queryParams}) {
    final full = ApiConfig.url(endpoint);
    var uri = Uri.parse(full);
    if (queryParams != null && queryParams.isNotEmpty) {
      uri = uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

  Future<ApiResponse> get(
    String endpoint, {
    Map<String, String>? query,
    Map<String, String>? headers,
  }) {
    final uri = buildUri(endpoint, queryParams: query);
    return _request(method: 'GET', uri: uri, headers: headers);
  }

  Future<ApiResponse> post(
    String endpoint, {
    Map<String, String>? query,
    Map<String, String>? headers,
    dynamic body,
  }) {
    final uri = buildUri(endpoint, queryParams: query);
    return _request(method: 'POST', uri: uri, headers: headers, body: body);
  }

  Future<ApiResponse> put(
    String endpoint, {
    Map<String, String>? query,
    Map<String, String>? headers,
    dynamic body,
  }) {
    final uri = buildUri(endpoint, queryParams: query);
    return _request(method: 'PUT', uri: uri, headers: headers, body: body);
  }

  Future<ApiResponse> del(
    String endpoint, {
    Map<String, String>? query,
    Map<String, String>? headers,
    dynamic body,
  }) {
    final uri = buildUri(endpoint, queryParams: query);
    return _request(method: 'DELETE', uri: uri, headers: headers, body: body);
  }

  Future<ApiResponse> _request({
    required String method,
    required Uri uri,
    Map<String, String>? headers,
    dynamic body,
  }) async {
    final h = <String, String>{..._defaultHeaders, if (headers != null) ...headers};

    String? payload;
    if (body != null) {
      payload = (body is String) ? body : jsonEncode(body);
    }

    if (Env.logApi) {
      _log('Request: $method ${uri.toString()}');
      if (Env.logPayloads && payload != null) {
        _log('   body: $payload');
      }
    }

    http.Response res;
    try {
      switch (method) {
        case 'GET':
          res = await _client.get(uri, headers: h).timeout(_timeout);
          break;
        case 'POST':
          res = await _client.post(uri, headers: h, body: payload).timeout(_timeout);
          break;
        case 'PUT':
          res = await _client.put(uri, headers: h, body: payload).timeout(_timeout);
          break;
        case 'DELETE':
          res = await _client.delete(uri, headers: h, body: payload).timeout(_timeout);
          break;
        default:
          throw ApiException('Unsupported method: $method', endpoint: uri.toString());
      }
    } on TimeoutException {
      throw ApiException.timeout(endpoint: uri.toString());
    } catch (e) {
      final msg = _friendlyNetworkError(e);
      throw ApiException.network(msg, endpoint: uri.toString(), details: e);
    }

    if (Env.logApi) {
      _log('Response: ${res.statusCode} ${uri.toString()}');
    }

    return _decodeResponse(res, uri);
  }

  ApiResponse _decodeResponse(http.Response res, Uri uri) {
    final status = res.statusCode;

    Map<String, dynamic> jsonMap;
    try {
      final decoded = jsonDecode(res.body);
      if (decoded is Map<String, dynamic>) {
        jsonMap = decoded;
      } else {
        jsonMap = {'success': status >= 200 && status < 300, 'data': decoded};
      }
    } catch (_) {
      throw ApiException.server(
        'Server returned invalid JSON',
        statusCode: status,
        endpoint: uri.toString(),
      );
    }

    final bool okStatus = status >= 200 && status < 300;
    final bool? successFlag =
        jsonMap['success'] is bool ? jsonMap['success'] as bool : null;
    final dynamic payloadData =
        jsonMap.containsKey('data') ? jsonMap['data'] : jsonMap;
    final String? message = (jsonMap['message'] ?? jsonMap['error'])?.toString();

    if (!okStatus) {
      if (status == 401) throw ApiException.unauthorized(endpoint: uri.toString(), details: jsonMap);
      if (status == 403) throw ApiException.unauthorized(endpoint: uri.toString(), details: jsonMap);
      if (status == 404) {
        throw ApiException.validation(
          'Endpoint not found',
          statusCode: status,
          endpoint: uri.toString(),
          details: jsonMap,
        );
      }
      throw ApiException.server(
        message ?? 'Request failed (status=$status).',
        statusCode: status,
        endpoint: uri.toString(),
        details: jsonMap,
      );
    }

    if (successFlag == false) {
      throw ApiException.validation(
        message ?? 'Request failed.',
        statusCode: status,
        endpoint: uri.toString(),
        details: jsonMap,
      );
    }

    return ApiResponse(
      statusCode: status,
      raw: jsonMap,
      data: payloadData,
      success: successFlag ?? true,
      message: message,
    );
  }

  String _friendlyNetworkError(Object e) {
    final s = e.toString();
    if (s.contains('Failed to fetch') || s.contains('XMLHttpRequest')) {
      return 'Failed to fetch. Possible reasons: 1) Backend not running, 2) Wrong baseUrl (Web must use 127.0.0.1, Android emulator uses 10.0.2.2), 3) CORS blocked (enable CORS in Flask).';
    }

    if (s.contains('Connection refused') || s.contains('SocketException')) {
      return 'Connection refused. Backend server is not reachable. Check Flask server running on ${Env.baseUrl}.';
    }

    return 'Network error: $s';
  }

  void _log(String msg) {
    // ignore: avoid_print
    print(msg);
  }

  void close() {
    _client.close();
  }
}
