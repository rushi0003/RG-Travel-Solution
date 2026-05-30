import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../core/theme/app_theme.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_card.dart';

class OtpScreen extends StatefulWidget {
  final String driverId;
  final int tripId;
  final String otpType;
  final String tripType;
  final String? routeNo;
  final String? baseUrl;

  const OtpScreen({
    super.key,
    required this.driverId,
    required this.tripId,
    required this.otpType,
    required this.tripType,
    this.routeNo,
    this.baseUrl,
  });

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  late String _baseUrl;
  late final TextEditingController _baseUrlCtrl;

  final TextEditingController _otpCtrl = TextEditingController();

  bool _loading = false;
  String? _error;
  String? _statusMsg;

  @override
  void initState() {
    super.initState();
    _baseUrl = widget.baseUrl ??
        (kIsWeb ? 'http://127.0.0.1:5000' : 'http://10.0.2.2:5000');
    _baseUrlCtrl = TextEditingController(text: _baseUrl);
  }

  @override
  void dispose() {
    _baseUrlCtrl.dispose();
    _otpCtrl.dispose();
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

  bool _isOtp6(String s) => RegExp(r'^\d{6}$').hasMatch(s);

  bool get _isStart => widget.otpType.toLowerCase() == 'start';
  bool get _isEnd => widget.otpType.toLowerCase() == 'end';
  bool get _isPickup => widget.tripType.toLowerCase() == 'pickup';
  bool get _isDrop => widget.tripType.toLowerCase() == 'drop';

  bool get _startOtpAllowed => _isPickup;

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

  Future<void> _verify() async {
    safeSetState(() {
      _error = null;
      _statusMsg = null;
    });

    if (_isStart && !_startOtpAllowed) {
      toast('Drop trip start OTP is not required.');
      return;
    }

    final otp = _otpCtrl.text.trim();
    if (!_isOtp6(otp)) {
      safeSetState(() => _error = 'OTP must be exactly 6 digits.');
      return;
    }

    safeSetState(() => _loading = true);

    try {
      final res = await _postJson(
        '/api/driver/${widget.driverId}/trip/${widget.tripId}/otp/verify',
        {
          'otp_type': widget.otpType.toLowerCase(),
          'otp': otp,
        },
      );

      final msg = res['message']?.toString() ?? 'OTP verified';
      final data = (res['data'] is Map)
          ? (res['data'] as Map).cast<String, dynamic>()
          : null;
      final newStatus = data?['status']?.toString();

      safeSetState(() {
        _statusMsg = newStatus != null ? '$msg (Status: $newStatus)' : msg;
      });

      toast('OTP verified');

      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      safeSetState(() => _error = 'OTP verification failed: $e');
    } finally {
      safeSetState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = _isStart ? 'Verify Start OTP' : 'Verify End OTP';
    final routeNo = (widget.routeNo ?? '').trim();
    final otpBlocked = _isStart && _isDrop;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: Text(title),
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final horizontalPadding = constraints.maxWidth > 720
                  ? (constraints.maxWidth - 720) / 2 + AppSpacing.md
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
                  const SizedBox(height: AppSpacing.md),
                  _card(
                    title: 'Trip Info',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (routeNo.isNotEmpty) ...[
                          _badge('Route: $routeNo'),
                          const SizedBox(height: AppSpacing.sm),
                        ],
                        Wrap(
                          spacing: AppSpacing.sm,
                          runSpacing: AppSpacing.sm,
                          children: [
                            _badge('Trip ID: ${widget.tripId}'),
                            _badge(
                              'Trip Type: ${widget.tripType.toLowerCase()}',
                            ),
                            _badge(
                              'OTP Type: ${widget.otpType.toLowerCase()}',
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.md),
                        if (otpBlocked)
                          _msg(
                            'Drop trip start OTP is not required. Start the trip from Assigned Trip.',
                            error: false,
                          ),
                        if (_isStart && _isPickup)
                          _hint(
                            'Pickup start requires OTP from the employee.',
                          ),
                        if (_isEnd)
                          _hint(
                            'End trip requires OTP before trip completion.',
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _card(
                    title: 'Enter OTP',
                    child: Column(
                      children: [
                        TextField(
                          controller: _otpCtrl,
                          keyboardType: TextInputType.number,
                          maxLength: 6,
                          enabled: !otpBlocked && !_loading,
                          decoration: const InputDecoration(
                            hintText: '6-digit OTP',
                            counterText: '',
                            prefixIcon: Icon(Icons.password_rounded, size: 20),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        if (_loading)
                          const LinearProgressIndicator(minHeight: 3),
                        if (_error != null) ...[
                          const SizedBox(height: AppSpacing.sm),
                          _msg(_error!, error: true),
                        ],
                        if (_statusMsg != null) ...[
                          const SizedBox(height: AppSpacing.sm),
                          _msg(_statusMsg!, error: false),
                        ],
                        const SizedBox(height: AppSpacing.md),
                        RGButton(
                          text: otpBlocked
                              ? 'Start OTP Not Required'
                              : 'Verify OTP',
                          icon: Icons.verified_rounded,
                          isLoading: _loading,
                          isDisabled: otpBlocked,
                          onPressed: otpBlocked || _loading ? null : _verify,
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
    return RGCard(
      title: 'Connection',
      subtitle: kIsWeb
          ? 'Web uses http://127.0.0.1:5000'
          : 'Android emulator uses http://10.0.2.2:5000',
      child: TextField(
        controller: _baseUrlCtrl,
        style: AppTypography.bodySmall,
        decoration: _deco('Base URL', 'http://127.0.0.1:5000', Icons.link),
        onSubmitted: (v) {
          final nv = v.trim();
          if (nv.isEmpty) return;
          safeSetState(() => _baseUrl = nv);
          toast('Base URL set: $_baseUrl');
        },
      ),
    );
  }

  Widget _card({required String title, required Widget child}) {
    return RGCard(
      title: title,
      child: child,
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

  Widget _msg(String t, {required bool error}) {
    final accent = error ? AppThemeColors.error : AppThemeColors.success;
    return Container(
      width: double.infinity,
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

  InputDecoration _deco(String label, String hint, IconData icon) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: Icon(icon, size: 20),
    );
  }
}
