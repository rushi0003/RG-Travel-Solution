import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../core/theme/app_theme.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_card.dart';

class DriverProfileScreen extends StatefulWidget {
  const DriverProfileScreen({
    super.key,
    required this.driverId,
    this.baseUrl,
  });
  final String driverId;
  final String? baseUrl;

  @override
  State<DriverProfileScreen> createState() => _DriverProfileScreenState();
}

class _DriverProfileScreenState extends State<DriverProfileScreen> {
  late String _baseUrl;
  late final TextEditingController _baseUrlCtrl;

  bool _loading = false;
  String? _error;

  Map<String, dynamic>? _profile;

  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _dlCtrl = TextEditingController();
  final _cabCtrl = TextEditingController();
  final _homeCtrl = TextEditingController();
  String _vehicleType = '4';

  @override
  void initState() {
    super.initState();
    _baseUrl = widget.baseUrl ??
        (kIsWeb ? 'http://127.0.0.1:5000' : 'http://10.0.2.2:5000');
    _baseUrlCtrl = TextEditingController(text: _baseUrl);

    _loadProfile();
  }

  @override
  void dispose() {
    _baseUrlCtrl.dispose();
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _dlCtrl.dispose();
    _cabCtrl.dispose();
    _homeCtrl.dispose();
    super.dispose();
  }

  void safeSetState(VoidCallback fn) {
    if (!mounted) return;
    setState(fn);
  }

  void toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Uri _u(String path) {
    final p = path.startsWith('/') ? path : '/$path';
    return Uri.parse('${_baseUrl.trim()}$p');
  }

  Future<Map<String, dynamic>> _getJson(String path) async {
    final r = await http.get(_u(path));
    final body = jsonDecode(r.body);
    if (r.statusCode >= 400) {
      final msg = (body is Map && body['message'] != null)
          ? body['message'].toString()
          : 'HTTP ${r.statusCode}';
      throw Exception(msg);
    }
    if (body is Map<String, dynamic>) return body;
    throw Exception('Invalid response format');
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, dynamic> data,
  ) async {
    final r = await http.post(
      _u(path),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    final body = jsonDecode(r.body);
    if (r.statusCode >= 400) {
      final msg = (body is Map && body['message'] != null)
          ? body['message'].toString()
          : 'HTTP ${r.statusCode}';
      throw Exception(msg);
    }
    if (body is Map<String, dynamic>) return body;
    throw Exception('Invalid response format');
  }

  bool _isMobile10(String s) => RegExp(r'^\d{10}$').hasMatch(s);

  bool _isDL(String s) => RegExp(r'^[A-Za-z]{2}\d{13}$').hasMatch(s);

  bool _isVehicleNo(String s) =>
      RegExp(r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$').hasMatch(s);

  String? _validateForm() {
    final name = _nameCtrl.text.trim();
    final mobile = _mobileCtrl.text.trim();
    final dl = _dlCtrl.text.trim().toUpperCase();
    final cab = _cabCtrl.text.trim().toUpperCase();

    if (name.length < 2) return 'Enter valid name';
    if (!_isMobile10(mobile)) return 'Mobile must be exactly 10 digits';
    if (dl.isNotEmpty && !_isDL(dl)) return 'DL must be 2 letters + 13 digits';
    if (cab.isNotEmpty && !_isVehicleNo(cab)) {
      return 'Cab number format invalid (MH12AB1234)';
    }
    if (!['4', '6'].contains(_vehicleType)) {
      return 'Select vehicle type 4 or 6';
    }
    return null;
  }

  Future<void> _loadProfile() async {
    safeSetState(() {
      _loading = true;
      _error = null;
    });

    try {
      final res = await _getJson('/api/driver/profile/${widget.driverId}');
      final data = (res['data'] is Map)
          ? (res['data'] as Map).cast<String, dynamic>()
          : null;
      if (data == null) throw Exception('Profile not found');

      safeSetState(() {
        _profile = data;

        _nameCtrl.text = (data['name'] ?? '').toString();
        _mobileCtrl.text = (data['mobile'] ?? '').toString();
        _dlCtrl.text = (data['dl_no'] ?? '').toString();
        _cabCtrl.text = (data['cab_no'] ?? '').toString();
        _homeCtrl.text = (data['hometown'] ?? '').toString();

        final vt = (data['vehicle_type'] ?? '').toString().toLowerCase();
        if (vt.contains('6')) _vehicleType = '6';
        if (vt.contains('4')) _vehicleType = '4';
        if (vt == '6') _vehicleType = '6';
        if (vt == '4') _vehicleType = '4';
      });
    } catch (e) {
      safeSetState(() => _error = 'Profile load failed: $e');
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  Future<void> _sendChangeRequest() async {
    final err = _validateForm();
    if (err != null) {
      toast(err);
      return;
    }

    final body = {
      'name': _nameCtrl.text.trim(),
      'mobile': _mobileCtrl.text.trim(),
      'dl_no': _dlCtrl.text.trim().toUpperCase(),
      'cab_no': _cabCtrl.text.trim().toUpperCase(),
      'hometown': _homeCtrl.text.trim(),
    };

    safeSetState(() => _loading = true);
    try {
      final res = await _postJson(
        '/api/driver/profile/${widget.driverId}/change-request',
        body,
      );
      toast(res['message']?.toString() ?? 'Change request submitted');
    } catch (e) {
      toast('Request failed: $e');
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = _profile;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Driver Profile'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loadProfile,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final horizontalPadding = constraints.maxWidth > 800
                  ? (constraints.maxWidth - 800) / 2 + AppSpacing.md
                  : AppSpacing.md;

              return ListView(
                padding: EdgeInsets.fromLTRB(
                  horizontalPadding,
                  AppSpacing.md,
                  horizontalPadding,
                  AppSpacing.lg,
                ),
                children: [
                  _backendCard(),
                  if (_loading) ...[
                    const LinearProgressIndicator(minHeight: 3),
                    const SizedBox(height: AppSpacing.md),
                  ],
                  if (_error != null) ...[
                    _msg(_error!, error: true),
                    const SizedBox(height: AppSpacing.md),
                  ],
                  _card(
                    title: 'Current Profile',
                    subtitle: 'Latest approved driver details.',
                    child: p == null
                        ? _hint('No profile loaded.')
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Wrap(
                                spacing: AppSpacing.sm,
                                runSpacing: AppSpacing.sm,
                                children: [
                                  _badge('Name: ${p['name'] ?? '-'}'),
                                  _badge('Mobile: ${p['mobile'] ?? '-'}'),
                                  _badge('Cab: ${p['cab_no'] ?? '-'}'),
                                  _badge('Type: ${p['vehicle_type'] ?? '-'}'),
                                ],
                              ),
                              const SizedBox(height: AppSpacing.md),
                              _kv('DL No', (p['dl_no'] ?? '-').toString()),
                              _kv(
                                'Hometown',
                                (p['hometown'] ?? '-').toString(),
                              ),
                              _kv('Status', (p['status'] ?? '-').toString()),
                            ],
                          ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _card(
                    title: 'Update Profile',
                    subtitle: 'Changes apply only after admin approval.',
                    child: Column(
                      children: [
                        _tf(_nameCtrl, 'Name', Icons.person_outline_rounded),
                        const SizedBox(height: AppSpacing.sm),
                        _tf(
                          _mobileCtrl,
                          'Mobile (10 digits)',
                          Icons.phone_outlined,
                          keyboard: TextInputType.phone,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        _tf(
                          _dlCtrl,
                          'DL No (2 letters + 13 digits)',
                          Icons.badge_outlined,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        _tf(
                          _cabCtrl,
                          'Cab No (MH12AB1234)',
                          Icons.local_taxi_outlined,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        _tf(
                          _homeCtrl,
                          'Hometown Location / Address',
                          Icons.home_work_outlined,
                          maxLines: 2,
                        ),
                        const SizedBox(height: AppSpacing.md),
                        _VehicleTypeSelector(
                          value: _vehicleType,
                          onChanged: (value) {
                            safeSetState(() => _vehicleType = value);
                          },
                        ),
                        const SizedBox(height: AppSpacing.md),
                        RGButton(
                          text: 'Send Change Request',
                          icon: Icons.send_rounded,
                          isLoading: _loading,
                          onPressed: _loading ? null : _sendChangeRequest,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        _hint(
                          'Note: Your changes will apply only after admin approval.',
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _backendCard() {
    return const SizedBox.shrink();
  }

  Widget _card({
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    return RGCard(
      title: title,
      subtitle: subtitle,
      child: child,
    );
  }

  Widget _msg(String t, {required bool error}) {
    final accent = error ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: accent.withValues(alpha: 0.30)),
      ),
      child: Text(
        t,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _hint(String t) {
    return Text(
      t,
      style: AppTypography.bodySmall.copyWith(
        color: AppThemeColors.textSecondary,
      ),
    );
  }

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          Expanded(
            child: Text(
              k,
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              v,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _badge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlassActive,
        borderRadius: BorderRadius.circular(AppRadius.full),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.45),
        ),
      ),
      child: Text(
        text,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }

  Widget _tf(
    TextEditingController c,
    String hint,
    IconData icon, {
    TextInputType keyboard = TextInputType.text,
    int maxLines = 1,
  }) {
    return TextField(
      controller: c,
      maxLines: maxLines,
      keyboardType: keyboard,
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: Icon(icon, size: 20),
      ),
    );
  }
}

class _VehicleTypeSelector extends StatelessWidget {
  const _VehicleTypeSelector({
    required this.value,
    required this.onChanged,
  });

  final String value;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.42),
        ),
      ),
      child: Wrap(
        spacing: AppSpacing.sm,
        runSpacing: AppSpacing.sm,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Text(
            'Vehicle Type',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
              fontWeight: FontWeight.w700,
            ),
          ),
          ChoiceChip(
            selected: value == '4',
            label: const Text('4 Seater'),
            onSelected: (_) => onChanged('4'),
          ),
          ChoiceChip(
            selected: value == '6',
            label: const Text('6 Seater'),
            onSelected: (_) => onChanged('6'),
          ),
        ],
      ),
    );
  }
}
