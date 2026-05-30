import 'dart:convert';

import 'package:http/http.dart' as http;

import 'admin_service.dart';

class OpsAuthResult {
  const OpsAuthResult({
    required this.token,
    required this.mobile,
  });

  final String token;
  final String mobile;
}

class OpsAuthService {
  OpsAuthService._();

  static Future<OpsAuthResult> login({
    required String mobile,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('${AdminService.baseUrl}/api/admin/login'),
      headers: const {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'mobile': mobile.trim(),
        'password': password.trim(),
      }),
    );

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      throw Exception(body['message'] ?? 'Login failed');
    }

    final data = (body['data'] as Map?)?.cast<String, dynamic>() ?? {};
    final token = (data['token'] ?? '').toString();
    final profile = (data['profile'] as Map?)?.cast<String, dynamic>() ?? {};
    final resolvedMobile = (profile['mobile'] ?? mobile).toString();
    if (token.isEmpty) {
      throw Exception('Login succeeded but token is missing');
    }
    return OpsAuthResult(token: token, mobile: resolvedMobile);
  }
}
