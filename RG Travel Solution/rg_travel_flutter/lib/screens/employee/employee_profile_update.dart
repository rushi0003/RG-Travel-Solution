import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geocoding/geocoding.dart';
import 'package:latlong2/latlong.dart';

import '../../core/theme/app_theme.dart';
import '../../services/employee_service.dart';
import '../../widgets/common/map_coordinate_picker_sheet.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_card.dart';

class EmployeeProfileUpdateScreen extends StatefulWidget {
  final String employeeId;
  const EmployeeProfileUpdateScreen({super.key, required this.employeeId});

  @override
  State<EmployeeProfileUpdateScreen> createState() =>
      _EmployeeProfileUpdateScreenState();
}

class _EmployeeProfileUpdateScreenState
    extends State<EmployeeProfileUpdateScreen> {
  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _loginCtrl = TextEditingController();
  final _logoutCtrl = TextEditingController();

  Timer? _addressDebounce;
  bool _isResolvingAddress = false;
  String? _addressResolveNote;
  double? _pickedLat;
  double? _pickedLng;

  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() => _loading = true);
    try {
      final id = int.tryParse(widget.employeeId) ?? 0;
      final data = await EmployeeService.getEmployeeProfile(id);

      setState(() {
        _nameCtrl.text = (data['name'] ?? '').toString();
        _mobileCtrl.text = (data['mobile'] ?? '').toString();
        _addressCtrl.text = (data['home_address'] ?? '').toString();
        _loginCtrl.text = (data['login_time'] ?? '').toString();
        _logoutCtrl.text = (data['logout_time'] ?? '').toString();
        _pickedLat = _asDouble(data['home_lat'] ?? data['lat']);
        _pickedLng = _asDouble(data['home_lng'] ?? data['lng']);
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Load failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _mobileCtrl.dispose();
    _addressCtrl.dispose();
    _loginCtrl.dispose();
    _logoutCtrl.dispose();
    _addressDebounce?.cancel();
    super.dispose();
  }

  double? _asDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  String _coordLabel() {
    if (_pickedLat == null || _pickedLng == null) {
      return 'No map point selected';
    }
    return '${_pickedLat!.toStringAsFixed(6)}, ${_pickedLng!.toStringAsFixed(6)}';
  }

  Future<void> _openMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Update Home Location',
        addressHint: _addressCtrl.text.trim(),
        initialLat: _pickedLat,
        initialLng: _pickedLng,
      ),
    );

    if (selected == null) return;
    if (!mounted) return;
    setState(() {
      _pickedLat = selected.latitude;
      _pickedLng = selected.longitude;
      _addressResolveNote = 'Map location selected';
    });
  }

  void _onAddressChanged(String value) {
    _addressDebounce?.cancel();
    final address = value.trim();
    if (address.length < 5) {
      if (mounted) {
        setState(() {
          _addressResolveNote = null;
        });
      }
      return;
    }
    _addressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveAddress(address);
    });
  }

  Future<void> _autoResolveAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    setState(() {
      _isResolvingAddress = true;
      _addressResolveNote = 'Resolving address on map...';
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final loc = locations.first;
        setState(() {
          _pickedLat = loc.latitude;
          _pickedLng = loc.longitude;
          _addressResolveNote = 'Auto-centered from typed address';
        });
      } else {
        setState(() {
          _addressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _addressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isResolvingAddress = false;
      });
    }
  }

  Future<void> _submitRequest() async {
    setState(() => _loading = true);
    try {
      final id = int.tryParse(widget.employeeId) ?? 0;
      await EmployeeService.requestProfileChange(
        id,
        name: _nameCtrl.text.trim(),
        mobile: _mobileCtrl.text.trim(),
        homeAddress: _addressCtrl.text.trim(),
        loginTime: _loginCtrl.text.trim(),
        logoutTime: _logoutCtrl.text.trim(),
        homeLat: _pickedLat,
        homeLng: _pickedLng,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Change Request Submitted!')),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Request failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final initialLoading = _loading && _nameCtrl.text.isEmpty;

    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Update Profile'),
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: initialLoading
              ? const Center(child: CircularProgressIndicator())
              : LayoutBuilder(
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
                            title: 'Request Profile Changes',
                            subtitle: 'Updates require admin approval.',
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _tf(_nameCtrl, 'Full Name', Icons.person),
                                const SizedBox(height: AppSpacing.sm),
                                _tf(
                                  _mobileCtrl,
                                  'Mobile',
                                  Icons.phone,
                                  keyboard: TextInputType.phone,
                                ),
                                const SizedBox(height: AppSpacing.sm),
                                _tf(
                                  _addressCtrl,
                                  'Home Address',
                                  Icons.home_outlined,
                                  maxLines: 2,
                                  onChanged: _onAddressChanged,
                                ),
                                const SizedBox(height: AppSpacing.sm),
                                _LocationSummary(
                                  coordinateLabel: _coordLabel(),
                                  isResolving: _isResolvingAddress,
                                  note: _addressResolveNote,
                                  onPickMap: _openMapPicker,
                                ),
                                const SizedBox(height: AppSpacing.sm),
                                LayoutBuilder(
                                  builder: (context, fieldConstraints) {
                                    final stackFields =
                                        fieldConstraints.maxWidth < 520;
                                    final loginField = _tf(
                                      _loginCtrl,
                                      'Login Time (HH:mm)',
                                      Icons.access_time,
                                    );
                                    final logoutField = _tf(
                                      _logoutCtrl,
                                      'Logout Time (HH:mm)',
                                      Icons.access_time_filled,
                                    );

                                    if (stackFields) {
                                      return Column(
                                        children: [
                                          loginField,
                                          const SizedBox(
                                            height: AppSpacing.sm,
                                          ),
                                          logoutField,
                                        ],
                                      );
                                    }

                                    return Row(
                                      children: [
                                        Expanded(child: loginField),
                                        const SizedBox(width: AppSpacing.sm),
                                        Expanded(child: logoutField),
                                      ],
                                    );
                                  },
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: AppSpacing.lg),
                          RGButton(
                            text: _loading ? 'Sending...' : 'Submit Request',
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

  Widget _tf(
    TextEditingController c,
    String hint,
    IconData icon, {
    TextInputType keyboard = TextInputType.text,
    int maxLines = 1,
    ValueChanged<String>? onChanged,
  }) {
    return TextField(
      controller: c,
      keyboardType: keyboard,
      maxLines: maxLines,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: hint,
        prefixIcon: Icon(icon, size: 20),
      ),
    );
  }
}

class _LocationSummary extends StatelessWidget {
  const _LocationSummary({
    required this.coordinateLabel,
    required this.isResolving,
    required this.note,
    required this.onPickMap,
  });

  final String coordinateLabel;
  final bool isResolving;
  final String? note;
  final VoidCallback onPickMap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(
          color: AppThemeColors.borderLight.withValues(alpha: 0.42),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Icon(
                Icons.location_on_outlined,
                color: AppThemeColors.primary.withValues(alpha: 0.9),
                size: 18,
              ),
              Text(
                'Coordinates',
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                coordinateLabel,
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          if (isResolving || note != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Row(
              children: [
                if (isResolving) ...[
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                ],
                Expanded(
                  child: Text(
                    isResolving ? 'Resolving address...' : (note ?? ''),
                    style: AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textTertiary,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.sm),
          Align(
            alignment: Alignment.centerRight,
            child: OutlinedButton.icon(
              onPressed: onPickMap,
              icon: const Icon(Icons.map_outlined, size: 16),
              label: const Text('Pick on Map'),
            ),
          ),
        ],
      ),
    );
  }
}
