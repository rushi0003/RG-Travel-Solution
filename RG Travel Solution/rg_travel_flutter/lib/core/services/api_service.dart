// lib/core/services/api_service.dart
//
// Centralized API service with safe URL building, auth header injection,
// logging, and error handling.

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/env.dart';
import '../storage/session_store.dart';

class ApiService {
  ApiService._();

  /// Build default headers with auth token
  static Future<Map<String, String>> _getHeaders() async {
    return SessionStore.authHeaders(
      baseHeaders: const {'Content-Type': 'application/json'},
    );
  }

  static Uri buildUri(String path) {
    var url = Env.makeUrl(path);
    // Prevent accidental duplicate "/api/api" when baseUrl already contains "/api"
    if (url.contains('/api/api')) {
      url = url.replaceAll('/api/api', '/api');
    }
    return Uri.parse(url);
  }

  static Future<Map<String, dynamic>> getJson(String path) async {
    final uri = buildUri(path);
    final headers = await _getHeaders();
    // ignore: avoid_print
    print('Request: GET $uri');
    final r = await http.get(uri, headers: headers);
    // ignore: avoid_print
    print('Response: ${r.statusCode} ${r.body}');
    _raiseForStatus(r.statusCode, r.body, uri);
    return _decodeBody(r.body);
  }

  static Future<Map<String, dynamic>> postJson(String path, Map<String, dynamic> payload) async {
    final uri = buildUri(path);
    final headers = await _getHeaders();
    // ignore: avoid_print
    print('Request: POST $uri payload=${jsonEncode(payload)}');
    final r = await http.post(uri, headers: headers, body: jsonEncode(payload));
    // ignore: avoid_print
    print('Response: ${r.statusCode} ${r.body}');
    _raiseForStatus(r.statusCode, r.body, uri);
    return _decodeBody(r.body);
  }

  static Future<Map<String, dynamic>> putJson(String path, Map<String, dynamic> payload) async {
    final uri = buildUri(path);
    final headers = await _getHeaders();
    // ignore: avoid_print
    print('Request: PUT $uri payload=${jsonEncode(payload)}');
    final r = await http.put(uri, headers: headers, body: jsonEncode(payload));
    // ignore: avoid_print
    print('Response: ${r.statusCode} ${r.body}');
    _raiseForStatus(r.statusCode, r.body, uri);
    return _decodeBody(r.body);
  }

  static Future<Map<String, dynamic>> deleteJson(String path) async {
    final uri = buildUri(path);
    final headers = await _getHeaders();
    // ignore: avoid_print
    print('Request: DELETE $uri');
    final r = await http.delete(uri, headers: headers);
    // ignore: avoid_print
    print('Response: ${r.statusCode} ${r.body}');
    _raiseForStatus(r.statusCode, r.body, uri);
    return _decodeBody(r.body);
  }

  static void _raiseForStatus(int statusCode, String body, Uri uri) {
    if (statusCode < 400) return;
    String msg = body;
    try {
      final parsed = jsonDecode(body);
      if (parsed is Map && parsed['message'] != null) msg = parsed['message'].toString();
    } catch (_) {
      // leave body as-is
    }

    if (statusCode == 401) throw Exception('Unauthorized: $msg');
    if (statusCode == 403) throw Exception('Forbidden: $msg');
    if (statusCode == 404) throw Exception('Endpoint not found: $uri');
    throw Exception(msg);
  }

  static Map<String, dynamic> _decodeBody(String body) {
    try {
      final parsed = jsonDecode(body);
      if (parsed is Map<String, dynamic>) return parsed;
      throw Exception('Invalid response format');
    } catch (e) {
      throw Exception('Invalid response format: $e');
    }
  }
}
