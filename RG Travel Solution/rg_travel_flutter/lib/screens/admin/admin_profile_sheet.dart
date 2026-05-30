// lib/screens/admin/admin_profile_sheet.dart
//
// RG Travel Solution — Admin Profile Sheet (BottomSheet / Drawer style)
//
// Dependencies (pubspec.yaml):
//   http: ^1.2.2
//
// Usage Example:
// showModalBottomSheet(
//   context: context,
//   isScrollControlled: true,
//   backgroundColor: Colors.transparent,
//   builder: (_) => AdminProfileSheet(adminId: adminId),
// );

import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:rg_travel_flutter/core/theme/app_theme.dart';

class AdminProfileSheet extends StatefulWidget {
  final int adminId;

  // Optional: allow passing baseUrl from parent
  final String? baseUrl;

  const AdminProfileSheet({
    super.key,
    required this.adminId,
    this.baseUrl,
  });

  @override
  State<AdminProfileSheet> createState() => _AdminProfileSheetState();
}

class _AdminProfileSheetState extends State<AdminProfileSheet> {
  // -----------------------
  // Base URL
  // -----------------------
  late String _baseUrl;
  late final TextEditingController _baseUrlCtrl;

  // -----------------------
  // Controllers
  // -----------------------
  late final TextEditingController _nameCtrl;
  late final TextEditingController _mobileCtrl;
  late final TextEditingController _officeNameCtrl;
  late final TextEditingController _officeAddressCtrl;

  // -----------------------
  // UI states
  // -----------------------
  bool _loading = false;
  bool _saving = false;
  String? _error;
  String? _success;

  // -----------------------
  // init/dispose
  // -----------------------
  @override
  void initState() {
    super.initState();

    // Default baseUrl: web uses 127.0.0.1, emulator uses 10.0.2.2
    _baseUrl = widget.baseUrl ??
        (kIsWeb ? "http://127.0.0.1:5000" : "http://10.0.2.2:5000");

    _baseUrlCtrl = TextEditingController(text: _baseUrl);

    _nameCtrl = TextEditingController();
    _mobileCtrl = TextEditingController();
    _officeNameCtrl = TextEditingController();
    _officeAddressCtrl = TextEditingController();

    _loadProfile();
  }

  @override
  void dispose() {
    _baseUrlCtrl.dispose();
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _officeNameCtrl.dispose();
    _officeAddressCtrl.dispose();
    super.dispose();
  }

  // -----------------------
  // Helpers
  // -----------------------
  Uri _u(String path) {
    final normalized = path.startsWith("/") ? path : "/$path";
    var base = _baseUrl.trim();
    if (base.endsWith('/')) base = base.substring(0, base.length - 1);
    if (base.endsWith('/api') && normalized.startsWith('/api')) {
      return Uri.parse(base + normalized.substring(4));
    }
    return Uri.parse(base + normalized);
  }

  void _safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  bool _isMobile10(String s) => RegExp(r'^\d{10}$').hasMatch(s);

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg)),
    );
  }

  // -----------------------
  // API: GET profile
  // -----------------------
  Future<void> _loadProfile() async {
    _safeSetState(() {
      _loading = true;
      _error = null;
      _success = null;
    });

    try {
      final res = await http.get(_u("/api/admin/${widget.adminId}"));
      final body = jsonDecode(res.body);

      if (res.statusCode >= 400) {
        final msg = (body is Map && body["message"] != null)
            ? body["message"].toString()
            : "HTTP ${res.statusCode}";
        throw Exception(msg);
      }

      final data = (body is Map && body["data"] is Map)
          ? (body["data"] as Map).cast<String, dynamic>()
          : <String, dynamic>{};

      _safeSetState(() {
        _nameCtrl.text = (data["name"] ?? "").toString();
        _mobileCtrl.text = (data["mobile"] ?? "").toString();
        _officeNameCtrl.text = (data["office_name"] ?? "").toString();
        _officeAddressCtrl.text =
            (data["office_address"] ?? data["office_location"] ?? "")
                .toString();
      });
    } catch (e) {
      _safeSetState(() => _error = "Failed to load profile: $e");
    } finally {
      _safeSetState(() => _loading = false);
    }
  }

  // -----------------------
  // API: PUT profile update
  // -----------------------
  Future<void> _saveProfile() async {
    _safeSetState(() {
      _error = null;
      _success = null;
    });

    final name = _nameCtrl.text.trim();
    final mobile = _mobileCtrl.text.trim();
    final officeName = _officeNameCtrl.text.trim();
    final officeAddress = _officeAddressCtrl.text.trim();

    if (name.length < 2) {
      _toast("Enter admin name (min 2 chars).");
      return;
    }
    if (!_isMobile10(mobile)) {
      _toast("Mobile must be exactly 10 digits.");
      return;
    }
    if (officeName.length < 2) {
      _toast("Enter office name.");
      return;
    }
    if (officeAddress.length < 5) {
      _toast("Enter office address (min 5 chars).");
      return;
    }

    final payload = {
      "name": name,
      "mobile": mobile,
      "office_name": officeName,
      "office_address": officeAddress,
      "office_location": officeAddress,
    };

    _safeSetState(() => _saving = true);

    try {
      final res = await http.put(
        _u("/api/admin/${widget.adminId}"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(payload),
      );
      final body = jsonDecode(res.body);

      if (res.statusCode >= 400) {
        final msg = (body is Map && body["message"] != null)
            ? body["message"].toString()
            : "HTTP ${res.statusCode}";
        throw Exception(msg);
      }

      _safeSetState(() => _success = "Profile updated successfully ✅");
      _toast("Profile saved ✅");

      // Optional: close sheet automatically after save
      // Navigator.pop(context, true);
    } catch (e) {
      _safeSetState(() => _error = "Update failed: $e");
      _toast("Update failed: $e");
    } finally {
      _safeSetState(() => _saving = false);
    }
  }

  // -----------------------
  // UI
  // -----------------------
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => FocusScope.of(context).unfocus(),
      child: Container(
        padding: EdgeInsets.only(
          left: 14,
          right: 14,
          top: 10,
          bottom: MediaQuery.of(context).viewInsets.bottom + 14,
        ),
        decoration: const BoxDecoration(
          color: Colors.transparent,
        ),
        child: _glassCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _handleBar(),
              const SizedBox(height: AppSpacing.md),

              Row(
                children: [
                  const Icon(Icons.person, color: AppThemeColors.textPrimary),
                  const SizedBox(width: AppSpacing.md),
                   Expanded(
                    child: Text(
                      "Admin Profile",
                      style: AppTypography.titleMedium.copyWith(
                        shadows: AppShadows.card,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: "Reload",
                    onPressed: _loading ? null : _loadProfile,
                    icon: const Icon(Icons.refresh, color: AppThemeColors.textPrimary),
                  ),
                ],
              ),

              const SizedBox(height: 10),

              if (_loading) ...[
                const SizedBox(height: 8),
                const LinearProgressIndicator(minHeight: 3),
                const SizedBox(height: 10),
              ],

              if (_error != null)
                _msgBox(_error!, isError: true),

              if (_success != null)
                _msgBox(_success!, isError: false),

              const SizedBox(height: 10),

              // Base URL override box (important for Web vs Emulator)
              _sectionTitle("Backend URL"),
              _input(
                controller: _baseUrlCtrl,
                label: "Base URL",
                hint: "http://127.0.0.1:5000",
                icon: Icons.link,
                keyboard: TextInputType.url,
                onSubmitted: (v) {
                  final nv = v.trim();
                  if (nv.isEmpty) return;
                  _safeSetState(() => _baseUrl = nv);
                  _toast("Base URL updated: $_baseUrl");
                  _loadProfile();
                },
              ),

              const SizedBox(height: 12),

              _sectionTitle("Admin Details"),
              _input(
                controller: _nameCtrl,
                label: "Admin Name",
                hint: "Enter name",
                icon: Icons.badge,
              ),
              _input(
                controller: _mobileCtrl,
                label: "Mobile Number",
                hint: "10 digits",
                icon: Icons.phone,
                keyboard: TextInputType.phone,
              ),

              const SizedBox(height: 12),

              _sectionTitle("Office Details"),
              _input(
                controller: _officeNameCtrl,
                label: "Office Name",
                hint: "Company/Office",
                icon: Icons.apartment,
              ),
              _input(
                controller: _officeAddressCtrl,
                label: "Office Address",
                hint: "Full address",
                icon: Icons.location_city,
                maxLines: 2,
              ),

              const SizedBox(height: 14),

              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _saving ? null : () => Navigator.pop(context, false),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: AppThemeColors.border),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.lg)),
                      ),
                      child: Text(
                        "Close",
                        style: AppTypography.labelLarge.copyWith(color: AppThemeColors.textSecondary),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _saving ? null : _saveProfile,
                      icon: _saving
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: AppThemeColors.textPrimary),
                            )
                          : const Icon(Icons.save, size: 20),
                      label: Text(_saving ? "Saving..." : "Save"),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppThemeColors.primary,
                        foregroundColor: AppThemeColors.textPrimary,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.lg)),
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  // -----------------------
  // UI widgets
  // -----------------------
  Widget _handleBar() {
    return Container(
      width: 46,
      height: 5,
      decoration: BoxDecoration(
        color: AppThemeColors.textTertiary,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
    );
  }

  Widget _glassCard({required Widget child}) {
    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(AppRadius.xl)),
        border: Border.all(color: AppThemeColors.border),
        boxShadow: AppShadows.card,
      ),
      padding: const EdgeInsets.all(AppSpacing.md),
      child: child,
    );
  }

  Widget _sectionTitle(String t) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
        child: Text(
          t,
          style: AppTypography.titleSmall.copyWith(
            color: AppThemeColors.textSecondary,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }

  Widget _msgBox(String msg, {required bool isError}) {
    final color = isError ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: color.withValues(alpha: 0.30),
        ),
      ),
      child: Text(
        msg,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _input({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    TextInputType? keyboard,
    int maxLines = 1,
    void Function(String)? onSubmitted,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: TextField(
        controller: controller,
        keyboardType: keyboard,
        maxLines: maxLines,
        onSubmitted: onSubmitted,
        style: AppTypography.bodyMedium.copyWith(color: AppThemeColors.textPrimary),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: AppTypography.labelMedium.copyWith(color: AppThemeColors.textSecondary),
          hintText: hint,
          hintStyle: AppTypography.bodyMedium.copyWith(color: AppThemeColors.textTertiary),
          prefixIcon: Icon(icon, color: AppThemeColors.textSecondary),
          filled: true,
          fillColor: AppThemeColors.background,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
            borderSide: BorderSide.none,
          ),
        ),
      ),
    );
  }
}
