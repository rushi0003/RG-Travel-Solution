import 'package:shared_preferences/shared_preferences.dart';

class TokenStore {
  TokenStore._();

  static const _kToken = 'auth_token';
  static const _kRole = 'auth_role';
  static const _kExpires = 'auth_expires';

  static Future<void> saveToken({required String token, required String role, required String expiresAt}) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kToken, token);
    await p.setString(_kRole, role);
    await p.setString(_kExpires, expiresAt);
  }

  static Future<String?> getToken() async {
    final p = await SharedPreferences.getInstance();
    return p.getString(_kToken);
  }

  static Future<String?> getRole() async {
    final p = await SharedPreferences.getInstance();
    return p.getString(_kRole);
  }

  static Future<String?> getExpiresAt() async {
    final p = await SharedPreferences.getInstance();
    return p.getString(_kExpires);
  }

  static Future<void> clearAll() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_kToken);
    await p.remove(_kRole);
    await p.remove(_kExpires);
  }

  static Future<bool> hasToken() async {
    final p = await SharedPreferences.getInstance();
    return p.containsKey(_kToken);
  }
}
