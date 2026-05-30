import 'package:flutter/material.dart';

import '../../core/storage/session_store.dart';
import '../../core/theme/app_theme.dart';
import '../../services/driver_service.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_card.dart';

class DriverHometownScreen extends StatefulWidget {
  const DriverHometownScreen({super.key, required this.driverId});
  final String driverId;

  @override
  State<DriverHometownScreen> createState() => _DriverHometownScreenState();
}

class _DriverHometownScreenState extends State<DriverHometownScreen> {
  final _hometowns = [
    'Kalyan',
    'Dombivli',
    'Ulhasnagar',
    'Ambernath',
    'Badlapur',
    'Thane',
    'Mulund',
    'Bhandup',
    'Ghatkopar',
    'Kurla',
    'Dadar',
    'Andheri',
    'Borivali',
    'Vasai',
    'Virar',
  ];

  String _selectedHometown = 'Kalyan';
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  Future<void> _loadRequests() async {
    try {
      // Reserved for request history when the backend exposes it.
    } catch (e) {
      debugPrint('Error loading requests: $e');
    }
  }

  Future<void> _submitRequest() async {
    setState(() => _loading = true);
    try {
      final token = await SessionStore.getToken();
      await DriverService.requestHometownChange(
        widget.driverId,
        newHometown: _selectedHometown,
        token: token,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Hometown Request Submitted')),
        );
        Navigator.pop(context);
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
        title: const Text('Change Hometown'),
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
                      title: 'Request Permanent Hometown Change',
                      subtitle:
                          'This affects trip assignment priority and requires admin approval.',
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          DropdownButtonFormField<String>(
                            initialValue: _selectedHometown,
                            dropdownColor: AppThemeColors.surface,
                            isExpanded: true,
                            decoration: const InputDecoration(
                              labelText: 'Select New Hometown',
                              prefixIcon:
                                  Icon(Icons.home_work_outlined, size: 20),
                            ),
                            items: _hometowns
                                .map(
                                  (hometown) => DropdownMenuItem(
                                    value: hometown,
                                    child: Text(hometown),
                                  ),
                                )
                                .toList(),
                            onChanged: (value) {
                              if (value == null) return;
                              setState(() => _selectedHometown = value);
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Container(
                            padding: const EdgeInsets.all(AppSpacing.md),
                            decoration: BoxDecoration(
                              color: AppThemeColors.info.withValues(
                                alpha: 0.08,
                              ),
                              borderRadius: BorderRadius.circular(AppRadius.sm),
                              border: Border.all(
                                color: AppThemeColors.info.withValues(
                                  alpha: 0.22,
                                ),
                              ),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.info_outline_rounded,
                                  color: AppThemeColors.info,
                                  size: 20,
                                ),
                                const SizedBox(width: AppSpacing.sm),
                                Expanded(
                                  child: Text(
                                    'Your current route and future assignments may change after approval.',
                                    style: AppTypography.bodySmall.copyWith(
                                      color: AppThemeColors.textSecondary,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    RGButton(
                      text: 'Submit Request',
                      icon: Icons.send_rounded,
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
}
