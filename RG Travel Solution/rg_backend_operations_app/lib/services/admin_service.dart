import 'dart:convert';

import 'package:http/http.dart' as http;

import 'ops_session_store.dart';

class AdminService {
  AdminService._();

  static String baseUrl = 'http://127.0.0.1:5000';

  static void setBaseUrl(String value) {
    final trimmed = value.trim();
    if (trimmed.isNotEmpty) baseUrl = trimmed;
  }

  static Uri _uri(String path) {
    final normalized = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$baseUrl$normalized');
  }

  static Future<Map<String, String>> _headers() async {
    final headers = <String, String>{
      'Accept': 'application/json',
    };
    final token = await OpsSessionStore.getToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  static Future<dynamic> _getData(String path) async {
    final response = await http.get(_uri(path), headers: await _headers());
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      throw Exception(body['message'] ?? 'Request failed');
    }
    return body['data'];
  }

  static Future<dynamic> post(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final response = await http.post(
      _uri(path),
      headers: {
        ...await _headers(),
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body ?? <String, dynamic>{}),
    );
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      throw Exception(payload['message'] ?? 'Request failed');
    }
    return payload['data'];
  }

  static Future<dynamic> delete(String path) async {
    final response = await http.delete(_uri(path), headers: await _headers());
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      throw Exception(payload['message'] ?? 'Request failed');
    }
    return payload['data'];
  }

  static Future<dynamic> put(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final response = await http.put(
      _uri(path),
      headers: {
        ...await _headers(),
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body ?? <String, dynamic>{}),
    );
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      throw Exception(payload['message'] ?? 'Request failed');
    }
    return payload['data'];
  }

  static Future<int> countFromList(String path) async {
    final data = await _getData(path);
    if (data is List) return data.length;
    return 0;
  }

  static Future<List<Map<String, dynamic>>> fetchList(String path) async {
    final data = await _getData(path);
    if (data is! List) return const <Map<String, dynamic>>[];
    return data
        .whereType<Map>()
        .map((item) => item.cast<String, dynamic>())
        .toList();
  }
}
