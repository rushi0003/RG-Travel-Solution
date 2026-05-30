// flutter/lib/widgets/trip/otp_dialog.dart
//
// RG Travel Solution — OTP Dialog
//
// Supports two modes:
// 1) Employee mode: request OTP + display OTP + expiry countdown
// 2) Driver mode: enter OTP + verify OTP
//
// This dialog DOES NOT call backend directly.
// Screen/Service should pass callbacks that call endpoints.
//
// Recommended endpoints mapping (your backend):
// - Employee GET OTP:
//    GET /api/employee/{employeeId}/otp?route_no=XXXX&type=start|end
// - Driver Verify OTP:
//    POST /api/driver/trip/{routeNo}/verify-otp
//    body: { "type": "start"|"end", "otp": "123456" }
//
// You can adapt callback signatures accordingly.

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/theme/app_theme.dart';
import '../../models/trip_model.dart';
import '../common/rg_button.dart';

enum OtpKind { start, end }

enum OtpDialogRole { employee, driver }

class OtpDialog extends StatefulWidget {
  final TripModel trip;

  /// role decides UI
  final OtpDialogRole role;

  /// start or end OTP
  final OtpKind kind;

  /// Employee identity (needed to request OTP)
  final int? employeeId;

  /// Already received OTP info (optional)
  /// If provided, dialog shows OTP instantly.
  final OtpInfo? initialOtp;

  /// When true, allow employee to request OTP again (resend)
  final bool allowResend;

  /// Employee callback: fetch OTP from backend
  /// Should return OtpInfo { otp, expiresAt, verified? }.
  final Future<OtpInfo> Function({
    required String routeNo,
    required OtpKind kind,
    required int employeeId,
  })? onRequestOtp;

  /// Driver callback: verify OTP entered by driver
  /// Should return true if verified successfully, else false.
  final Future<bool> Function({
    required String routeNo,
    required OtpKind kind,
    required String otp,
  })? onVerifyOtp;

  const OtpDialog({
    super.key,
    required this.trip,
    required this.role,
    required this.kind,
    this.employeeId,
    this.initialOtp,
    this.allowResend = true,
    this.onRequestOtp,
    this.onVerifyOtp,
  });

  // Convenient show helper
  static Future<T?> show<T>(
    BuildContext context, {
    required TripModel trip,
    required OtpDialogRole role,
    required OtpKind kind,
    int? employeeId,
    OtpInfo? initialOtp,
    bool allowResend = true,
    Future<OtpInfo> Function({
      required String routeNo,
      required OtpKind kind,
      required int employeeId,
    })? onRequestOtp,
    Future<bool> Function({
      required String routeNo,
      required OtpKind kind,
      required String otp,
    })? onVerifyOtp,
  }) {
    return showDialog<T>(
      context: context,
      barrierDismissible: false,
      builder: (_) => OtpDialog(
        trip: trip,
        role: role,
        kind: kind,
        employeeId: employeeId,
        initialOtp: initialOtp,
        allowResend: allowResend,
        onRequestOtp: onRequestOtp,
        onVerifyOtp: onVerifyOtp,
      ),
    );
  }

  @override
  State<OtpDialog> createState() => _OtpDialogState();
}

class _OtpDialogState extends State<OtpDialog> {
  // Employee mode state
  OtpInfo? _otp;
  int? _remainingSec;
  Timer? _timer;

  // Driver mode state
  final TextEditingController _otpController = TextEditingController();
  String? _error;

  bool _isBusy = false;

  @override
  void initState() {
    super.initState();
    _otp = widget.initialOtp;

    // Start countdown if expiresAt exists
    if (_otp?.expiresAt != null) {
      _startTimerFromExpiresAt(_otp!.expiresAt!);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _otpController.dispose();
    super.dispose();
  }

  // ---------------------------
  // UI helpers
  // ---------------------------

  String get _kindText =>
      widget.kind == OtpKind.start ? "Start OTP" : "End OTP";

  String get _roleText =>
      widget.role == OtpDialogRole.employee ? "Employee" : "Driver";

  String get _routeText => widget.trip.routeNo;

  bool get _isEmployee => widget.role == OtpDialogRole.employee;

  bool get _isDriver => widget.role == OtpDialogRole.driver;

  bool get _expired => (_remainingSec != null && _remainingSec! <= 0);

  // Pickup/drop OTP rules display note (UI only, backend enforces)
  String _rulesNote() {
    if (widget.trip.isPickup) {
      return "Pickup trip: Start and End OTP both required.";
    }
    if (widget.trip.isDrop) {
      return "Drop trip: End OTP required to complete trip.";
    }
    return "OTP required as per trip rules.";
  }

  // ---------------------------
  // Countdown logic
  // ---------------------------

  void _startTimerFromExpiresAt(String expiresAtIso) {
    _timer?.cancel();

    DateTime? expiresAt = DateTime.tryParse(expiresAtIso);
    if (expiresAt == null) return;

    void tick() {
      final now = DateTime.now();
      final diff = expiresAt.difference(now).inSeconds;
      if (!mounted) return;
      setState(() => _remainingSec = diff);
      if (diff <= 0) {
        _timer?.cancel();
      }
    }

    tick();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
  }

  String _formatRemaining(int sec) {
    if (sec <= 0) return "Expired";
    final m = sec ~/ 60;
    final s = sec % 60;
    final mm = m.toString().padLeft(2, "0");
    final ss = s.toString().padLeft(2, "0");
    return "$mm:$ss";
  }

  // ---------------------------
  // Employee: request/resend OTP
  // ---------------------------

  Future<void> _requestOtp() async {
    setState(() {
      _error = null;
      _isBusy = true;
    });

    try {
      final cb = widget.onRequestOtp;
      final employeeId = widget.employeeId;

      if (cb == null) {
        throw Exception("onRequestOtp callback not provided.");
      }
      if (employeeId == null) {
        throw Exception("employeeId is required for employee OTP.");
      }

      final otpInfo = await cb(
        routeNo: widget.trip.routeNo,
        kind: widget.kind,
        employeeId: employeeId,
      );

      if (!mounted) return;
      setState(() {
        _otp = otpInfo;
        _isBusy = false;
      });

      if (otpInfo.expiresAt != null) {
        _startTimerFromExpiresAt(otpInfo.expiresAt!);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isBusy = false;
        _error = e.toString().replaceFirst("Exception: ", "");
      });
    }
  }

  // ---------------------------
  // Driver: verify OTP
  // ---------------------------

  Future<void> _verifyOtp() async {
    final otp = _otpController.text.trim();

    if (otp.length != 6 || int.tryParse(otp) == null) {
      setState(() => _error = "Enter a valid 6-digit OTP.");
      return;
    }

    setState(() {
      _error = null;
      _isBusy = true;
    });

    try {
      final cb = widget.onVerifyOtp;
      if (cb == null) {
        throw Exception("onVerifyOtp callback not provided.");
      }

      final ok = await cb(
        routeNo: widget.trip.routeNo,
        kind: widget.kind,
        otp: otp,
      );

      if (!mounted) return;

      if (ok) {
        Navigator.pop(context, true);
        return;
      } else {
        setState(() {
          _isBusy = false;
          _error = "OTP verification failed. Please check and try again.";
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isBusy = false;
        _error = e.toString().replaceFirst("Exception: ", "");
      });
    }
  }

  // ---------------------------
  // Build UI
  // ---------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      backgroundColor: theme.colorScheme.surface.withValues(alpha: 0.95),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      titlePadding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      contentPadding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      actionsPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      title: _Header(
        title: _kindText,
        subtitle: "Route No: $_routeText  •  $_roleText",
      ),
      content: SizedBox(
        width: 420,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _InfoPill(text: _rulesNote()),
            const SizedBox(height: 12),
            if (_isEmployee) _buildEmployeeBody(context),
            if (_isDriver) _buildDriverBody(context),
            if ((_error ?? "").trim().isNotEmpty) ...[
              const SizedBox(height: 12),
              _ErrorBox(message: _error!.trim()),
            ],
            const SizedBox(height: 8),
          ],
        ),
      ),
      actions: [
        RGButton(
          text: "Close",
          variant: RGButtonVariant.outline,
          isLoading: false,
          onPressed: _isBusy ? null : () => Navigator.pop(context, false),
        ),
        const SizedBox(width: 10),
        if (_isDriver)
          RGButton(
            text: "Verify",
            icon: Icons.verified_rounded,
            variant: RGButtonVariant.primary,
            isLoading: _isBusy,
            onPressed: _isBusy ? null : _verifyOtp,
          ),
        if (_isEmployee)
          RGButton(
            text: _otp == null
                ? "Get OTP"
                : (widget.allowResend ? "Resend OTP" : "Get OTP"),
            icon: _otp == null ? Icons.lock : Icons.refresh_rounded,
            variant: RGButtonVariant.primary,
            isLoading: _isBusy,
            onPressed: _isBusy
                ? null
                : () {
                    if (_otp != null && !widget.allowResend) return;
                    _requestOtp();
                  },
          ),
      ],
    );
  }

  Widget _buildEmployeeBody(BuildContext context) {
    final theme = Theme.of(context);

    final otpText = (_otp?.otp ?? "").trim();
    final hasOtp = otpText.isNotEmpty;

    final exp = _otp?.expiresAt;
    final remaining = _remainingSec;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!hasOtp) ...[
          Text(
            "Click “Get OTP” to generate OTP for ${widget.kind == OtpKind.start ? "starting" : "ending"} the trip.",
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.80),
            ),
          ),
        ],
        if (hasOtp) ...[
          _OtpBox(
            otp: otpText,
            isExpired: _expired,
            onCopy: () async {
              await Clipboard.setData(ClipboardData(text: otpText));
              if (!mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("OTP copied")),
              );
            },
          ),
          const SizedBox(height: 10),
          if (exp != null) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Expires",
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.70),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  remaining == null ? exp : _formatRemaining(remaining),
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w900,
                    color: _expired
                        ? AppThemeColors.error
                        : AppThemeColors.success,
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 8),
          Text(
            "Share this OTP with the driver for verification.",
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.78),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildDriverBody(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          "Enter the 6-digit OTP received from employee to verify ${widget.kind == OtpKind.start ? "Start" : "End"} of trip.",
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.80),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _otpController,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(6),
          ],
          decoration: InputDecoration(
            labelText: "Enter OTP",
            hintText: "6-digit OTP",
            prefixIcon: const Icon(Icons.lock_outline),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          ),
          onChanged: (_) {
            if ((_error ?? "").trim().isNotEmpty) {
              setState(() => _error = null);
            }
          },
        ),
      ],
    );
  }
}

// =============================================================
// UI sub widgets
// =============================================================

class _Header extends StatelessWidget {
  final String title;
  final String subtitle;

  const _Header({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.w900,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          subtitle,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _InfoPill extends StatelessWidget {
  final String text;
  const _InfoPill({required this.text});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline, size: 18, color: theme.colorScheme.primary),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _OtpBox extends StatelessWidget {
  final String otp;
  final bool isExpired;
  final VoidCallback onCopy;

  const _OtpBox({
    required this.otp,
    required this.isExpired,
    required this.onCopy,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final bg = isExpired
        ? AppThemeColors.error.withValues(alpha: 0.12)
        : theme.colorScheme.surface.withValues(alpha: 0.25);

    final border = isExpired
        ? AppThemeColors.error.withValues(alpha: 0.25)
        : theme.dividerColor.withValues(alpha: 0.40);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              otp.split("").join("  "),
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
          IconButton(
            onPressed: onCopy,
            icon: const Icon(Icons.copy_rounded),
            tooltip: "Copy OTP",
          ),
        ],
      ),
    );
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;
  const _ErrorBox({required this.message});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppThemeColors.error.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: AppThemeColors.error.withValues(alpha: 0.22),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.error_outline,
            size: 18,
            color: AppThemeColors.error,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
