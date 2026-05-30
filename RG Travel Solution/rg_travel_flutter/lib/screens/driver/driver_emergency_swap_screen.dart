import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../services/driver_service.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_card.dart';

class DriverEmergencySwapScreen extends StatefulWidget {
  const DriverEmergencySwapScreen({
    super.key,
    required this.driverId,
    required this.tripId,
  });
  final String driverId;
  final int tripId;

  @override
  State<DriverEmergencySwapScreen> createState() =>
      _DriverEmergencySwapScreenState();
}

class _DriverEmergencySwapScreenState extends State<DriverEmergencySwapScreen> {
  final _reasonCtrl = TextEditingController();
  final _newDriverNameCtrl = TextEditingController();
  final _newDriverMobileCtrl = TextEditingController();
  final _newCabCtrl = TextEditingController();

  bool _loading = false;

  @override
  void dispose() {
    _reasonCtrl.dispose();
    _newDriverNameCtrl.dispose();
    _newDriverMobileCtrl.dispose();
    _newCabCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    // image_picker package is not available in this workspace.
    // Keep UI flow: inform user how to enable image capture without breaking compilation.
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Image capture unavailable. Add image_picker to enable.'),
      ),
    );
  }

  Future<void> _submitRequest() async {
    final reason = _reasonCtrl.text.trim();
    final newDriverName = _newDriverNameCtrl.text.trim();
    final newDriverMobile = _newDriverMobileCtrl.text.trim();
    final newCabNo = _newCabCtrl.text.trim();
    if (reason.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reason is required')),
      );
      return;
    }
    if (newDriverName.isEmpty || newDriverMobile.isEmpty || newCabNo.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Replacement driver name, mobile and cab number are required',
          ),
        ),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      await DriverService.createSwapRequest(
        widget.driverId,
        tripId: widget.tripId,
        reason: reason,
        newDriverName: newDriverName,
        newDriverMobile: newDriverMobile,
        newCabNo: newCabNo,
      );

      if (mounted) {
        await showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (_) => AlertDialog(
            title: const Text('Request Sent'),
            content: const Text(
              'Admin has been notified. Please wait for approval.',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pop(context);
                },
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Emergency Swap'),
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final horizontalPadding = constraints.maxWidth > 760
                  ? (constraints.maxWidth - 760) / 2 + AppSpacing.md
                  : AppSpacing.md;

              return SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(
                  horizontalPadding,
                  AppSpacing.md,
                  horizontalPadding,
                  AppSpacing.lg,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    RGCard(
                      title: 'Request Vehicle or Driver Swap',
                      subtitle:
                          'Use this only for breakdowns, safety issues, or urgent replacement needs.',
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _label('Reason for swap *'),
                          TextField(
                            controller: _reasonCtrl,
                            maxLines: 3,
                            textInputAction: TextInputAction.newline,
                            decoration: _inputDeco(
                              'Describe the issue',
                              Icons.report_problem_outlined,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          _label('Photo evidence (optional)'),
                          _PhotoEvidenceTile(onTap: _pickImage),
                          const SizedBox(height: AppSpacing.lg),
                          Text(
                            'Replacement Details',
                            style: AppTypography.titleSmall.copyWith(
                              color: AppThemeColors.textPrimary,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          _label('New driver name'),
                          TextField(
                            controller: _newDriverNameCtrl,
                            textInputAction: TextInputAction.next,
                            decoration: _inputDeco(
                              'Name of replacement driver',
                              Icons.person_outline_rounded,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          _label('New driver mobile'),
                          TextField(
                            controller: _newDriverMobileCtrl,
                            keyboardType: TextInputType.phone,
                            textInputAction: TextInputAction.next,
                            decoration: _inputDeco(
                              '10-digit mobile',
                              Icons.phone_outlined,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          _label('New cab number'),
                          TextField(
                            controller: _newCabCtrl,
                            textInputAction: TextInputAction.done,
                            decoration: _inputDeco(
                              'Vehicle No (e.g. MH-04-AB-1234)',
                              Icons.local_taxi_outlined,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    RGButton(
                      text: 'Submit Emergency Request',
                      icon: Icons.emergency_share_outlined,
                      variant: RGButtonVariant.danger,
                      isLoading: _loading,
                      onPressed: _loading ? null : _submitRequest,
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _label(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Text(
        text,
        style: AppTypography.bodySmall.copyWith(
          color: AppThemeColors.textSecondary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  InputDecoration _inputDeco(String hint, IconData icon) {
    return InputDecoration(
      hintText: hint,
      prefixIcon: Icon(icon, size: 20),
    );
  }
}

class _PhotoEvidenceTile extends StatelessWidget {
  const _PhotoEvidenceTile({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.lg,
          ),
          decoration: BoxDecoration(
            color: AppThemeColors.cardGlass,
            borderRadius: BorderRadius.circular(AppRadius.sm),
            border: Border.all(
              color: AppThemeColors.borderLight.withValues(alpha: 0.45),
            ),
          ),
          child: Column(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: AppThemeColors.primary.withValues(alpha: 0.10),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.camera_alt_outlined,
                  color: AppThemeColors.primary,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Tap to attach photo',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppThemeColors.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Optional evidence for admin review',
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textTertiary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
