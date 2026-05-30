import 'package:shared_preferences/shared_preferences.dart';

class OpsSessionStore {
  OpsSessionStore._();

  static const _loggedInKey = 'ops_logged_in';
  static const _tokenKey = 'ops_token';
  static const _mobileKey = 'ops_mobile';
  static const _baseUrlKey = 'ops_base_url';

  static Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_loggedInKey) ?? false;
  }

  static Future<void> saveSession({
    required String token,
    required String mobile,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_loggedInKey, true);
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_mobileKey, mobile);
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_loggedInKey);
    await prefs.remove(_tokenKey);
    await prefs.remove(_mobileKey);
  }

  static Future<void> setBaseUrl(String baseUrl) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_baseUrlKey, baseUrl);
  }

  static Future<String?> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_baseUrlKey);
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  static Future<String?> getMobile() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_mobileKey);
  }
}
