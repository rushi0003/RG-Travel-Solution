import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geocoding/geocoding.dart';
import 'package:latlong2/latlong.dart';

import '../services/admin_access_service.dart';
import '../theme/ops_ui_tokens.dart';
import 'map_coordinate_picker_sheet.dart';
import 'operations_ui.dart';

class AdminAccessScreen extends StatefulWidget {
  const AdminAccessScreen({super.key});

  @override
  State<AdminAccessScreen> createState() => _AdminAccessScreenState();
}

class _AdminAccessScreenState extends State<AdminAccessScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _mobileController = TextEditingController();
  final _passwordController = TextEditingController();
  final _emailController = TextEditingController();
  final _officeNameController = TextEditingController();
  final _officeAddressController = TextEditingController();
  final _searchController = TextEditingController();

  List<Map<String, dynamic>> _admins = const [];
  Timer? _officeAddressDebounce;
  bool _loading = true;
  bool _saving = false;
  bool _obscurePassword = true;
  bool _ignoreOfficeAddressChange = false;
  bool _isResolvingOfficeAddress = false;
  double? _officeLat;
  double? _officeLng;
  String _searchQuery = '';
  String? _officeAddressResolveNote;
  String? _error;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_handleSearchChanged);
    _loadAdmins();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _mobileController.dispose();
    _passwordController.dispose();
    _emailController.dispose();
    _officeNameController.dispose();
    _officeAddressController.dispose();
    _officeAddressDebounce?.cancel();
    _searchController
      ..removeListener(_handleSearchChanged)
      ..dispose();
    super.dispose();
  }

  void _handleSearchChanged() {
    final value = _searchController.text.trim();
    if (value == _searchQuery) return;
    setState(() => _searchQuery = value);
  }

  void _resetOfficeLocationState() {
    _officeAddressDebounce?.cancel();
    if (!mounted) {
      _officeLat = null;
      _officeLng = null;
      _officeAddressResolveNote = null;
      _isResolvingOfficeAddress = false;
      _ignoreOfficeAddressChange = false;
      return;
    }
    setState(() {
      _officeLat = null;
      _officeLng = null;
      _officeAddressResolveNote = null;
      _isResolvingOfficeAddress = false;
      _ignoreOfficeAddressChange = false;
    });
  }

  String _officeCoordLabel() {
    if (_officeLat == null || _officeLng == null) {
      return 'No map point selected';
    }
    return '${_officeLat!.toStringAsFixed(6)}, ${_officeLng!.toStringAsFixed(6)}';
  }

  Future<void> _openOfficeMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Select Office Location',
        addressHint: _officeAddressController.text.trim(),
        initialLat: _officeLat,
        initialLng: _officeLng,
      ),
    );

    if (selected == null || !mounted) return;
    setState(() {
      _officeLat = selected.latitude;
      _officeLng = selected.longitude;
      _officeAddressResolveNote = 'Map location selected';
    });
    await _reverseGeocodeOfficeSelection();
  }

  Future<void> _reverseGeocodeOfficeSelection() async {
    final lat = _officeLat;
    final lng = _officeLng;
    if (lat == null || lng == null || !mounted) return;
    setState(() {
      _isResolvingOfficeAddress = true;
      _officeAddressResolveNote =
          'Fetching office address from selected map point...';
    });
    try {
      final placemarks = await placemarkFromCoordinates(lat, lng);
      if (!mounted) return;
      final resolvedAddress =
          placemarks.isNotEmpty ? _formatPlacemark(placemarks.first) : '';
      setState(() {
        _ignoreOfficeAddressChange = true;
        _officeAddressController.text = resolvedAddress.isEmpty
            ? '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}'
            : resolvedAddress;
        _officeAddressResolveNote = resolvedAddress.isEmpty
            ? 'Coordinates saved from map selection'
            : 'Address filled from selected map location';
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _ignoreOfficeAddressChange = true;
        _officeAddressController.text =
            '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
        _officeAddressResolveNote = 'Coordinates saved from map selection';
      });
    } finally {
      // Keep the mounted guard without returning from finally.
      if (mounted) {
        setState(() {
          _isResolvingOfficeAddress = false;
        });
      }
    }
  }

  void _onOfficeAddressChanged(String value) {
    if (_ignoreOfficeAddressChange) {
      _ignoreOfficeAddressChange = false;
      return;
    }

    _officeAddressDebounce?.cancel();
    final address = value.trim();
    setState(() {
      _officeLat = null;
      _officeLng = null;
      _isResolvingOfficeAddress = false;
      _officeAddressResolveNote = address.isEmpty
          ? null
          : 'Address changed. Map point will update after lookup.';
    });

    if (address.length < 5) return;
    _officeAddressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveOfficeAddress(address);
    });
  }

  Future<void> _autoResolveOfficeAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    setState(() {
      _isResolvingOfficeAddress = true;
      _officeAddressResolveNote = 'Resolving office address on map...';
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final location = locations.first;
        setState(() {
          _officeLat = location.latitude;
          _officeLng = location.longitude;
          _officeAddressResolveNote =
              'Map coordinates linked from typed address';
        });
      } else {
        setState(() {
          _officeAddressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _officeAddressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (mounted) {
        setState(() {
          _isResolvingOfficeAddress = false;
        });
      }
    }
  }

  Future<void> _loadAdmins() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final admins = await AdminAccessService.fetchAdmins();
      if (!mounted) return;
      setState(() {
        _admins = admins;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _createAdmin() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await AdminAccessService.createAdmin(
        name: _nameController.text,
        mobile: _mobileController.text,
        password: _passwordController.text,
        email: _emailController.text,
        officeName: _officeNameController.text,
        officeLocation: _officeAddressController.text,
        officeAddress: _officeAddressController.text,
        officeLat: _officeLat,
        officeLng: _officeLng,
      );
      _nameController.clear();
      _mobileController.clear();
      _passwordController.clear();
      _emailController.clear();
      _officeNameController.clear();
      _officeAddressController.clear();
      _resetOfficeLocationState();
      await _loadAdmins();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Admin created successfully'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  Future<void> _deleteAdmin(Map<String, dynamic> admin) async {
    final adminId = (admin['id'] ?? '').toString();
    final display = _normalizeAdmin(admin);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove admin'),
        content: Text(
          'Delete ${display.name.isEmpty ? 'this admin' : display.name} from login access?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await AdminAccessService.deleteAdmin(adminId);
      await _loadAdmins();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Admin removed successfully'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Future<void> _editAdmin(Map<String, dynamic> admin) async {
    final adminId = (admin['id'] ?? '').toString().trim();
    if (adminId.isEmpty) return;
    final display = _normalizeAdmin(admin);

    final formKey = GlobalKey<FormState>();
    final nameController = TextEditingController(text: display.name);
    final mobileController = TextEditingController(text: display.mobile);
    final emailController = TextEditingController(text: display.email);
    final officeNameController =
        TextEditingController(text: display.officeName);
    final officeAddressController = TextEditingController(
      text: display.officeAddress,
    );
    Timer? addressDebounce;
    var ignoreAddressChange = false;
    var isResolvingAddress = false;
    var officeAddressResolveNote =
        display.officeLat != null && display.officeLng != null
            ? 'Saved office map point available'
            : null;
    double? officeLat = display.officeLat;
    double? officeLng = display.officeLng;
    var saving = false;

    try {
      final updated = await showDialog<bool>(
        context: context,
        barrierDismissible: !saving,
        builder: (context) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              String officeCoordLabel() {
                if (officeLat == null || officeLng == null) {
                  return 'No map point selected';
                }
                return '${officeLat!.toStringAsFixed(6)}, ${officeLng!.toStringAsFixed(6)}';
              }

              Future<void> reverseGeocodeSelection() async {
                final lat = officeLat;
                final lng = officeLng;
                if (lat == null || lng == null || !context.mounted) return;
                setDialogState(() {
                  isResolvingAddress = true;
                  officeAddressResolveNote =
                      'Fetching office address from selected map point...';
                });
                try {
                  final placemarks = await placemarkFromCoordinates(lat, lng);
                  if (!context.mounted) return;
                  final resolvedAddress = placemarks.isNotEmpty
                      ? _formatPlacemark(placemarks.first)
                      : '';
                  setDialogState(() {
                    ignoreAddressChange = true;
                    officeAddressController.text = resolvedAddress.isEmpty
                        ? '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}'
                        : resolvedAddress;
                    officeAddressResolveNote = resolvedAddress.isEmpty
                        ? 'Coordinates saved from map selection'
                        : 'Address filled from selected map location';
                  });
                } catch (_) {
                  if (!context.mounted) return;
                  setDialogState(() {
                    ignoreAddressChange = true;
                    officeAddressController.text =
                        '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
                    officeAddressResolveNote =
                        'Coordinates saved from map selection';
                  });
                } finally {
                  if (context.mounted) {
                    setDialogState(() {
                      isResolvingAddress = false;
                    });
                  }
                }
              }

              Future<void> openOfficeMapPicker() async {
                final selected = await showModalBottomSheet<LatLng>(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.transparent,
                  builder: (_) => MapCoordinatePickerSheet(
                    title: 'Update Office Location',
                    addressHint: officeAddressController.text.trim(),
                    initialLat: officeLat,
                    initialLng: officeLng,
                  ),
                );

                if (selected == null || !context.mounted) return;
                setDialogState(() {
                  officeLat = selected.latitude;
                  officeLng = selected.longitude;
                  officeAddressResolveNote = 'Map location selected';
                });
                await reverseGeocodeSelection();
              }

              Future<void> autoResolveOfficeAddress(String address) async {
                if (!context.mounted || address.trim().length < 5) return;
                setDialogState(() {
                  isResolvingAddress = true;
                  officeAddressResolveNote =
                      'Resolving office address on map...';
                });
                try {
                  final locations = await locationFromAddress(address);
                  if (!context.mounted) return;
                  if (locations.isNotEmpty) {
                    final location = locations.first;
                    setDialogState(() {
                      officeLat = location.latitude;
                      officeLng = location.longitude;
                      officeAddressResolveNote =
                          'Map coordinates linked from typed address';
                    });
                  } else {
                    setDialogState(() {
                      officeAddressResolveNote =
                          "Address not found. Use 'Pick on Map'.";
                    });
                  }
                } catch (_) {
                  if (!context.mounted) return;
                  setDialogState(() {
                    officeAddressResolveNote =
                        "Auto-geocode failed. Use 'Pick on Map'.";
                  });
                } finally {
                  if (context.mounted) {
                    setDialogState(() {
                      isResolvingAddress = false;
                    });
                  }
                }
              }

              void onOfficeAddressChanged(String value) {
                if (ignoreAddressChange) {
                  ignoreAddressChange = false;
                  return;
                }
                addressDebounce?.cancel();
                final address = value.trim();
                setDialogState(() {
                  officeLat = null;
                  officeLng = null;
                  isResolvingAddress = false;
                  officeAddressResolveNote = address.isEmpty
                      ? null
                      : 'Address changed. Map point will update after lookup.';
                });
                if (address.length < 5) return;
                addressDebounce = Timer(const Duration(milliseconds: 900), () {
                  autoResolveOfficeAddress(address);
                });
              }

              Future<void> submit() async {
                if (!formKey.currentState!.validate()) return;
                setDialogState(() => saving = true);
                try {
                  await AdminAccessService.updateAdmin(
                    adminId: adminId,
                    name: nameController.text,
                    mobile: mobileController.text,
                    email: emailController.text,
                    officeName: officeNameController.text,
                    officeLocation: officeAddressController.text,
                    officeAddress: officeAddressController.text,
                    officeLat: officeLat,
                    officeLng: officeLng,
                  );
                  if (!context.mounted) return;
                  Navigator.of(context).pop(true);
                } catch (e) {
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(e.toString()),
                      behavior: SnackBarBehavior.floating,
                    ),
                  );
                  setDialogState(() => saving = false);
                }
              }

              return AlertDialog(
                title: const Text('Edit admin'),
                content: SizedBox(
                  width: 420,
                  child: Form(
                    key: formKey,
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          TextFormField(
                            controller: nameController,
                            decoration: const InputDecoration(
                              labelText: 'Admin name',
                            ),
                            validator: (value) =>
                                (value == null || value.trim().length < 2)
                                    ? 'Enter valid name'
                                    : null,
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: mobileController,
                            keyboardType: TextInputType.phone,
                            decoration: const InputDecoration(
                              labelText: 'Mobile',
                            ),
                            validator: (value) {
                              final digits = (value ?? '').replaceAll(
                                RegExp(r'\D'),
                                '',
                              );
                              return digits.length == 10
                                  ? null
                                  : 'Enter 10 digit mobile';
                            },
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: emailController,
                            decoration: const InputDecoration(
                              labelText: 'Email (optional)',
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: officeNameController,
                            decoration: const InputDecoration(
                              labelText: 'Office name (optional)',
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: officeAddressController,
                            decoration: const InputDecoration(
                              labelText: 'Office address (optional)',
                            ),
                            onChanged: onOfficeAddressChanged,
                            maxLines: 2,
                          ),
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(OpsSpacing.lg),
                            decoration: OpsDecorations.mutedPanel(
                              borderColor: OpsUiTokens.outlineStrong,
                              radius: OpsRadius.lg,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.all(
                                        OpsSpacing.md,
                                      ),
                                      decoration: BoxDecoration(
                                        color: OpsUiTokens.primarySoft
                                            .withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(
                                          OpsRadius.md,
                                        ),
                                      ),
                                      child: const Icon(
                                        Icons.map_outlined,
                                        size: 18,
                                        color: OpsUiTokens.primarySoft,
                                      ),
                                    ),
                                    const SizedBox(width: OpsSpacing.md),
                                    const Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'Update office on map',
                                            style: OpsTypography.bodyStrong,
                                          ),
                                          SizedBox(height: OpsSpacing.xs),
                                          Text(
                                            'Pick a new map point to refresh office address and save latitude/longitude together.',
                                            style: OpsTypography.body,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: OpsSpacing.lg),
                                Row(
                                  children: [
                                    Expanded(
                                      child: FilledButton.tonalIcon(
                                        onPressed:
                                            saving ? null : openOfficeMapPicker,
                                        icon: const Icon(Icons.place_rounded),
                                        label: const Text('Pick on Map'),
                                      ),
                                    ),
                                    if ((officeLat != null &&
                                            officeLng != null) ||
                                        officeAddressController.text
                                            .trim()
                                            .isNotEmpty) ...[
                                      const SizedBox(width: OpsSpacing.sm),
                                      IconButton(
                                        onPressed: saving
                                            ? null
                                            : () {
                                                addressDebounce?.cancel();
                                                officeAddressController.clear();
                                                setDialogState(() {
                                                  officeLat = null;
                                                  officeLng = null;
                                                  isResolvingAddress = false;
                                                  officeAddressResolveNote =
                                                      null;
                                                  ignoreAddressChange = false;
                                                });
                                              },
                                        tooltip: 'Clear location',
                                        icon: const Icon(Icons.refresh_rounded),
                                      ),
                                    ],
                                  ],
                                ),
                                const SizedBox(height: OpsSpacing.md),
                                Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: OpsSpacing.md,
                                    vertical: OpsSpacing.md,
                                  ),
                                  decoration: OpsDecorations.mutedPanel(
                                    radius: OpsRadius.md,
                                    borderColor: OpsUiTokens.divider,
                                  ),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      const Padding(
                                        padding: EdgeInsets.only(top: 2),
                                        child: Icon(
                                          Icons.pin_drop_outlined,
                                          size: 16,
                                          color: OpsUiTokens.primarySoft,
                                        ),
                                      ),
                                      const SizedBox(width: OpsSpacing.sm),
                                      Expanded(
                                        child: Text(
                                          officeCoordLabel(),
                                          style: OpsTypography.body,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                if (officeAddressResolveNote != null) ...[
                                  const SizedBox(height: OpsSpacing.md),
                                  Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: isResolvingAddress
                                            ? const CircularProgressIndicator(
                                                strokeWidth: 2,
                                              )
                                            : const Icon(
                                                Icons.info_outline_rounded,
                                                size: 16,
                                                color: OpsUiTokens.primarySoft,
                                              ),
                                      ),
                                      const SizedBox(width: OpsSpacing.sm),
                                      Expanded(
                                        child: Text(
                                          officeAddressResolveNote!,
                                          style: OpsTypography.body,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed:
                        saving ? null : () => Navigator.of(context).pop(false),
                    child: const Text('Cancel'),
                  ),
                  FilledButton.icon(
                    onPressed: saving ? null : submit,
                    icon: saving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.save_rounded),
                    label: Text(saving ? 'Saving...' : 'Save Changes'),
                  ),
                ],
              );
            },
          );
        },
      );

      if (updated == true) {
        await _loadAdmins();
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Admin updated successfully'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      addressDebounce?.cancel();
      nameController.dispose();
      mobileController.dispose();
      emailController.dispose();
      officeNameController.dispose();
      officeAddressController.dispose();
    }
  }

  Future<void> _resetAdminPassword(Map<String, dynamic> admin) async {
    final adminId = (admin['id'] ?? '').toString().trim();
    if (adminId.isEmpty) return;
    final display = _normalizeAdmin(admin);

    final formKey = GlobalKey<FormState>();
    final passwordController = TextEditingController();
    final confirmPasswordController = TextEditingController();
    var obscurePassword = true;
    var obscureConfirm = true;
    var saving = false;

    try {
      final updated = await showDialog<bool>(
        context: context,
        builder: (context) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              Future<void> submit() async {
                if (!formKey.currentState!.validate()) return;
                setDialogState(() => saving = true);
                try {
                  await AdminAccessService.updateAdmin(
                    adminId: adminId,
                    name: display.name,
                    mobile: display.mobile,
                    email: display.email,
                    officeName: display.officeName,
                    officeLocation: display.officeLocation,
                    officeAddress: display.officeAddress,
                    officeLat: display.officeLat,
                    officeLng: display.officeLng,
                    password: passwordController.text,
                  );
                  if (!context.mounted) return;
                  Navigator.of(context).pop(true);
                } catch (e) {
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(e.toString()),
                      behavior: SnackBarBehavior.floating,
                    ),
                  );
                  setDialogState(() => saving = false);
                }
              }

              return AlertDialog(
                title: const Text('Reset admin password'),
                content: SizedBox(
                  width: 420,
                  child: Form(
                    key: formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Set a new password for ${display.name.isEmpty ? 'this admin' : display.name}.',
                          style: OpsTypography.body,
                        ),
                        const SizedBox(height: OpsSpacing.lg),
                        TextFormField(
                          controller: passwordController,
                          obscureText: obscurePassword,
                          decoration: InputDecoration(
                            labelText: 'New password',
                            suffixIcon: IconButton(
                              onPressed: () {
                                setDialogState(
                                  () => obscurePassword = !obscurePassword,
                                );
                              },
                              icon: Icon(
                                obscurePassword
                                    ? Icons.visibility_off_rounded
                                    : Icons.visibility_rounded,
                              ),
                            ),
                          ),
                          validator: (value) =>
                              (value == null || value.trim().length < 6)
                                  ? 'Minimum 6 characters'
                                  : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: confirmPasswordController,
                          obscureText: obscureConfirm,
                          decoration: InputDecoration(
                            labelText: 'Confirm password',
                            suffixIcon: IconButton(
                              onPressed: () {
                                setDialogState(
                                  () => obscureConfirm = !obscureConfirm,
                                );
                              },
                              icon: Icon(
                                obscureConfirm
                                    ? Icons.visibility_off_rounded
                                    : Icons.visibility_rounded,
                              ),
                            ),
                          ),
                          validator: (value) => value == passwordController.text
                              ? null
                              : 'Passwords do not match',
                        ),
                      ],
                    ),
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed:
                        saving ? null : () => Navigator.of(context).pop(false),
                    child: const Text('Cancel'),
                  ),
                  FilledButton.icon(
                    onPressed: saving ? null : submit,
                    icon: saving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.lock_reset_rounded),
                    label: Text(saving ? 'Updating...' : 'Update Password'),
                  ),
                ],
              );
            },
          );
        },
      );

      if (updated == true && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Admin password updated successfully'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      passwordController.dispose();
      confirmPasswordController.dispose();
    }
  }

  List<Map<String, dynamic>> get _filteredAdmins {
    if (_searchQuery.isEmpty) return _admins;
    final query = _searchQuery.toLowerCase();
    return _admins.where((admin) {
      final values = [
        admin['name'],
        admin['mobile'],
        admin['email'],
        admin['office_name'],
        admin['office_address'],
      ];
      return values.any(
        (value) => value.toString().toLowerCase().contains(query),
      );
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final filteredAdmins = _filteredAdmins;
    final adminsWithEmail = _admins
        .where((admin) => (admin['email'] ?? '').toString().trim().isNotEmpty)
        .length;
    final adminsWithOffice = _admins
        .where(
          (admin) => (admin['office_name'] ?? '').toString().trim().isNotEmpty,
        )
        .length;

    return Scaffold(
      backgroundColor: OpsUiTokens.background,
      appBar: AppBar(
        title: const Text('Admin Access Control'),
        actions: [
          IconButton(
            onPressed: _loadAdmins,
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh admins',
          ),
        ],
      ),
      body: Container(
        decoration: OpsDecorations.pageBackground(),
        child: RefreshIndicator(
          onRefresh: _loadAdmins,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= OpsBreakpoints.desktop;
              final formWidth = isWide ? 430.0 : constraints.maxWidth;
              return ListView(
                padding: context.opsPagePadding,
                children: [
                  OpsResponsiveContainer(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHero(theme),
                        const SizedBox(height: OpsSpacing.xl),
                        Wrap(
                          spacing: OpsSpacing.lg,
                          runSpacing: OpsSpacing.lg,
                          children: [
                            _buildMetricCard(
                              title: 'Total Admins',
                              value: '${_admins.length}',
                              icon: Icons.verified_user_rounded,
                              tone: OpsUiTokens.primary,
                            ),
                            _buildMetricCard(
                              title: 'Email Ready',
                              value: '$adminsWithEmail',
                              icon: Icons.alternate_email_rounded,
                              tone: OpsUiTokens.success,
                            ),
                            _buildMetricCard(
                              title: 'Office Tagged',
                              value: '$adminsWithOffice',
                              icon: Icons.apartment_rounded,
                              tone: OpsUiTokens.warningDeep,
                            ),
                            _buildVisibleNowCard(filteredAdmins.length),
                          ],
                        ),
                        const SizedBox(height: OpsSpacing.xl),
                        if (isWide)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(
                                width: formWidth,
                                child: _buildCreateCard(theme),
                              ),
                              const SizedBox(width: OpsSpacing.xl),
                              Expanded(
                                child: _buildAdminRoster(
                                  theme: theme,
                                  admins: filteredAdmins,
                                ),
                              ),
                            ],
                          )
                        else ...[
                          _buildCreateCard(theme),
                          const SizedBox(height: OpsSpacing.xl),
                          _buildAdminRoster(
                            theme: theme,
                            admins: filteredAdmins,
                          ),
                        ],
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

  Widget _buildHero(ThemeData theme) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < OpsBreakpoints.compact;
        final iconBox = Container(
          padding: const EdgeInsets.all(OpsSpacing.lg),
          decoration: BoxDecoration(
            color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(OpsRadius.lg),
          ),
          child: const Icon(
            Icons.admin_panel_settings_rounded,
            size: 32,
            color: OpsUiTokens.primarySoft,
          ),
        );
        final copy = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Admin access workspace',
                style: theme.textTheme.headlineLarge),
            const SizedBox(height: OpsSpacing.sm),
            Text(
              'Create backend admins, review contact readiness, and clean up old access without touching hardcoded app credentials.',
              style: OpsTypography.body.copyWith(
                color: OpsUiTokens.textSecondary,
              ),
            ),
          ],
        );

        return Container(
          width: double.infinity,
          padding: EdgeInsets.all(compact ? OpsSpacing.xl : OpsSpacing.xxl),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(OpsRadius.xxl),
            gradient: OpsGradients.accessHero,
            border: Border.all(color: OpsUiTokens.outlineStrong),
            boxShadow: OpsShadows.glow(OpsUiTokens.primary),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (compact)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    iconBox,
                    const SizedBox(height: OpsSpacing.lg),
                    copy,
                  ],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    iconBox,
                    const SizedBox(width: OpsSpacing.lg),
                    Expanded(child: copy),
                  ],
                ),
              const SizedBox(height: OpsSpacing.xl),
              const Wrap(
                spacing: OpsSpacing.md,
                runSpacing: OpsSpacing.md,
                children: [
                  _HeroChip(
                    icon: Icons.storage_rounded,
                    label: 'Database-backed credentials',
                  ),
                  _HeroChip(
                    icon: Icons.manage_accounts_rounded,
                    label: 'Searchable admin roster',
                  ),
                  _HeroChip(
                    icon: Icons.lock_outline_rounded,
                    label: 'Dedicated access control',
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildMetricCard({
    required String title,
    required String value,
    required IconData icon,
    required Color tone,
  }) {
    return Container(
      width: 220,
      padding: OpsSpacing.cardCompact,
      decoration: OpsDecorations.tonalPanel(tone: tone, alpha: 0.35),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: tone, size: 24),
          const SizedBox(height: OpsSpacing.md),
          Text(value, style: OpsTypography.heading),
          const SizedBox(height: OpsSpacing.xs),
          Text(title, style: OpsTypography.body),
        ],
      ),
    );
  }

  Widget _buildVisibleNowCard(int visibleCount) {
    final hasSearch = _searchQuery.isNotEmpty;
    final helperText = hasSearch
        ? 'Filtered by "${_searchQuery.trim()}"'
        : 'Showing full admin roster';

    return Container(
      width: 280,
      padding: OpsSpacing.cardCompact,
      decoration: BoxDecoration(
        color: OpsUiTokens.panelStrong,
        borderRadius: BorderRadius.circular(OpsRadius.xl),
        border: Border.all(
          color: OpsUiTokens.danger.withValues(alpha: 0.35),
        ),
        gradient: OpsGradients.danger,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(OpsSpacing.md),
                decoration: BoxDecoration(
                  color: OpsUiTokens.danger.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(OpsRadius.md),
                ),
                child: const Icon(
                  Icons.filter_alt_rounded,
                  color: OpsUiTokens.danger,
                  size: 20,
                ),
              ),
              const Spacer(),
              OpsStatusBadge(
                label: hasSearch ? 'Filtered' : 'All',
                tone: OpsUiTokens.danger,
                compact: true,
              ),
            ],
          ),
          const SizedBox(height: OpsSpacing.lg),
          Text('$visibleCount', style: OpsTypography.display),
          const SizedBox(height: OpsSpacing.xs),
          Text(
            'Visible Now',
            style: OpsTypography.subtitle.copyWith(
              color: OpsUiTokens.textSecondary,
            ),
          ),
          const SizedBox(height: OpsSpacing.md),
          Text(
            helperText,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: OpsTypography.body,
          ),
        ],
      ),
    );
  }

  Widget _buildCreateCard(ThemeData theme) {
    return OpsPanel(
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Create Admin',
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: OpsSpacing.sm),
            const Text(
              'Fill the fields below to provision a new admin profile for backend operations access.',
              style: OpsTypography.body,
            ),
            const SizedBox(height: OpsSpacing.xl),
            _buildSectionLabel('Identity'),
            const SizedBox(height: OpsSpacing.md),
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Admin name',
                prefixIcon: Icon(Icons.person_outline_rounded),
              ),
              validator: (value) => (value == null || value.trim().length < 2)
                  ? 'Enter valid name'
                  : null,
            ),
            const SizedBox(height: OpsSpacing.md),
            TextFormField(
              controller: _mobileController,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(
                labelText: 'Mobile',
                prefixIcon: Icon(Icons.phone_iphone_rounded),
              ),
              validator: (value) {
                final digits = (value ?? '').replaceAll(RegExp(r'\D'), '');
                return digits.length == 10 ? null : 'Enter 10 digit mobile';
              },
            ),
            const SizedBox(height: OpsSpacing.xl),
            _buildSectionLabel('Credentials'),
            const SizedBox(height: OpsSpacing.md),
            TextFormField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: const Icon(Icons.lock_outline_rounded),
                suffixIcon: IconButton(
                  onPressed: () {
                    setState(() => _obscurePassword = !_obscurePassword);
                  },
                  icon: Icon(
                    _obscurePassword
                        ? Icons.visibility_off_rounded
                        : Icons.visibility_rounded,
                  ),
                ),
              ),
              validator: (value) => (value == null || value.length < 6)
                  ? 'Minimum 6 characters'
                  : null,
            ),
            const SizedBox(height: OpsSpacing.xl),
            _buildSectionLabel('Office details'),
            const SizedBox(height: OpsSpacing.md),
            TextFormField(
              controller: _emailController,
              decoration: const InputDecoration(
                labelText: 'Email (optional)',
                prefixIcon: Icon(Icons.alternate_email_rounded),
              ),
            ),
            const SizedBox(height: OpsSpacing.md),
            TextFormField(
              controller: _officeNameController,
              decoration: const InputDecoration(
                labelText: 'Office name (optional)',
                prefixIcon: Icon(Icons.apartment_rounded),
              ),
            ),
            const SizedBox(height: OpsSpacing.md),
            TextFormField(
              controller: _officeAddressController,
              decoration: const InputDecoration(
                labelText: 'Office address (optional)',
                prefixIcon: Icon(Icons.location_on_outlined),
              ),
              onChanged: _onOfficeAddressChanged,
              maxLines: 2,
            ),
            const SizedBox(height: OpsSpacing.md),
            Container(
              padding: OpsSpacing.cardCompact,
              decoration: OpsDecorations.mutedPanel(
                borderColor: OpsUiTokens.panelInfoBorder,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color:
                              OpsUiTokens.primarySoft.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(OpsRadius.md),
                        ),
                        child: const Icon(
                          Icons.map_outlined,
                          size: 18,
                          color: OpsUiTokens.primarySoft,
                        ),
                      ),
                      const SizedBox(width: OpsSpacing.md),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Pick office on map',
                              style: OpsTypography.bodyStrong,
                            ),
                            SizedBox(height: OpsSpacing.xs),
                            Text(
                              'Map selection automatically fills address and saves latitude/longitude for the admin office.',
                              style: OpsTypography.body,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: OpsSpacing.lg),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: _saving ? null : _openOfficeMapPicker,
                          icon: const Icon(Icons.place_rounded),
                          label: const Text('Pick on Map'),
                        ),
                      ),
                      if ((_officeLat != null && _officeLng != null) ||
                          _officeAddressController.text.trim().isNotEmpty) ...[
                        const SizedBox(width: OpsSpacing.md),
                        IconButton(
                          onPressed: _saving
                              ? null
                              : () {
                                  _officeAddressController.clear();
                                  _resetOfficeLocationState();
                                },
                          tooltip: 'Clear location',
                          icon: const Icon(Icons.refresh_rounded),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: OpsSpacing.md),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                      horizontal: OpsSpacing.md,
                      vertical: OpsSpacing.sm,
                    ),
                    decoration: OpsDecorations.mutedPanel(
                      borderColor: OpsUiTokens.divider,
                      radius: OpsRadius.md,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Padding(
                          padding: EdgeInsets.only(top: 2),
                          child: Icon(
                            Icons.pin_drop_outlined,
                            size: 16,
                            color: OpsUiTokens.primarySoft,
                          ),
                        ),
                        const SizedBox(width: OpsSpacing.sm),
                        Expanded(
                          child: Text(
                            _officeCoordLabel(),
                            style: OpsTypography.body,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (_officeAddressResolveNote != null) ...[
                    const SizedBox(height: OpsSpacing.md),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: _isResolvingOfficeAddress
                              ? const CircularProgressIndicator(strokeWidth: 2)
                              : const Icon(
                                  Icons.info_outline_rounded,
                                  size: 16,
                                  color: OpsUiTokens.primarySoft,
                                ),
                        ),
                        const SizedBox(width: OpsSpacing.sm),
                        Expanded(
                          child: Text(
                            _officeAddressResolveNote!,
                            style: OpsTypography.body,
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: OpsSpacing.xl),
            Container(
              padding: OpsSpacing.cardCompact,
              decoration: OpsDecorations.mutedPanel(
                borderColor: OpsUiTokens.panelInfoBorder,
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.info_outline_rounded,
                    size: 18,
                    color: OpsUiTokens.primarySoft,
                  ),
                  SizedBox(width: OpsSpacing.md),
                  Expanded(
                    child: Text(
                      'New admin credentials are stored in the backend database and become part of the shared operations login flow.',
                      style: OpsTypography.body,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: OpsSpacing.xl),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _saving ? null : _createAdmin,
                icon: _saving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.person_add_alt_1_rounded),
                label: Text(_saving ? 'Saving...' : 'Create Admin Access'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionLabel(String text) {
    return Text(
      text.toUpperCase(),
      style: OpsTypography.caption.copyWith(
        color: OpsUiTokens.primarySoft,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  Widget _buildAdminRoster({
    required ThemeData theme,
    required List<Map<String, dynamic>> admins,
  }) {
    return OpsPanel(
      borderColor: OpsUiTokens.outline,
      elevated: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Admin Roster',
                      style: theme.textTheme.titleLarge,
                    ),
                    const SizedBox(height: OpsSpacing.sm),
                    Text(
                      _searchQuery.isEmpty
                          ? 'Review all active admin accounts and remove unused access.'
                          : 'Showing ${admins.length} result(s) for "$_searchQuery".',
                      style: OpsTypography.body,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: OpsSpacing.md),
              OpsStatusBadge(
                label: '${admins.length}',
                tone: OpsUiTokens.primarySoft,
                compact: true,
              ),
            ],
          ),
          const SizedBox(height: OpsSpacing.xl),
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              labelText: 'Search admins',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: _searchQuery.isEmpty
                  ? null
                  : IconButton(
                      onPressed: () => _searchController.clear(),
                      icon: const Icon(Icons.close_rounded),
                    ),
            ),
          ),
          const SizedBox(height: OpsSpacing.xl),
          if (_loading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 48),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_error != null)
            ErrorCard(message: _error!)
          else if (admins.isEmpty)
            _buildEmptyState()
          else
            ...admins.map(_buildAdminCard),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    final label = _searchQuery.isEmpty
        ? 'No admin accounts found yet.'
        : 'No admin matches the current search.';
    return OpsEmptyState(
      title: label,
      message:
          'Use the create form to add a new admin profile for operations access.',
      icon: Icons.manage_accounts_outlined,
    );
  }

  Widget _buildAdminCard(Map<String, dynamic> admin) {
    final display = _normalizeAdmin(admin);
    final name = display.name;
    final mobile = display.mobile;
    final email = display.email;
    final officeName = display.officeName;
    final officeAddress = display.officeAddress;
    final hasMapLocation =
        display.officeLat != null && display.officeLng != null;
    final summaryItems = <({IconData icon, String label})>[
      if (mobile.isNotEmpty)
        (icon: Icons.phone_iphone_rounded, label: _compactValue(mobile)),
      if (email.isNotEmpty)
        (icon: Icons.alternate_email_rounded, label: _compactValue(email)),
      if (officeName.isNotEmpty)
        (icon: Icons.apartment_rounded, label: _compactValue(officeName)),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 430;

        return Container(
          margin: const EdgeInsets.only(bottom: OpsSpacing.lg),
          padding: EdgeInsets.all(isCompact ? OpsSpacing.lg : OpsSpacing.xl),
          decoration: OpsDecorations.mutedPanel(
            borderColor: OpsUiTokens.panelInfoBorder,
            radius: OpsRadius.lg,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (isCompact)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        CircleAvatar(
                          radius: 22,
                          backgroundColor: OpsUiTokens.panelSidebarAccent,
                          child: Text(
                            _initialsFor(name),
                            style: OpsTypography.bodyStrong.copyWith(
                              color: OpsUiTokens.primarySoft,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: OpsSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _compactValue(
                                  name.isEmpty ? 'Unnamed Admin' : name,
                                  maxLength: 24,
                                ),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: OpsTypography.subtitle.copyWith(
                                  color: OpsUiTokens.textPrimary,
                                ),
                              ),
                              if (summaryItems.isNotEmpty) ...[
                                const SizedBox(height: OpsSpacing.xs),
                                Text(
                                  summaryItems.first.label,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: OpsTypography.body,
                                ),
                              ],
                              const SizedBox(height: OpsSpacing.sm),
                              _locationStatusPill(
                                  hasMapLocation: hasMapLocation),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: OpsSpacing.md),
                    SizedBox(
                      width: double.infinity,
                      child: Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _editAdmin(admin),
                              icon: const Icon(Icons.edit_outlined, size: 18),
                              label: const Text('Edit'),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: OpsUiTokens.primarySoft,
                                side: BorderSide(
                                  color: OpsUiTokens.primarySoft.withValues(
                                    alpha: 0.35,
                                  ),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  vertical: OpsSpacing.md,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.circular(OpsRadius.md),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: OpsSpacing.md),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _resetAdminPassword(admin),
                              icon: const Icon(
                                Icons.lock_reset_rounded,
                                size: 18,
                              ),
                              label: const Text('Password'),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: OpsUiTokens.warningDeep,
                                side: BorderSide(
                                  color: OpsUiTokens.warningDeep.withValues(
                                    alpha: 0.35,
                                  ),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  vertical: OpsSpacing.md,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.circular(OpsRadius.md),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: OpsSpacing.md),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _deleteAdmin(admin),
                              icon: const Icon(
                                Icons.delete_outline_rounded,
                                size: 18,
                              ),
                              label: const Text('Remove'),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: OpsUiTokens.danger,
                                side: BorderSide(
                                  color: OpsUiTokens.danger.withValues(
                                    alpha: 0.35,
                                  ),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  vertical: OpsSpacing.md,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.circular(OpsRadius.md),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CircleAvatar(
                      radius: 24,
                      backgroundColor: OpsUiTokens.panelSidebarAccent,
                      child: Text(
                        _initialsFor(name),
                        style: OpsTypography.bodyStrong.copyWith(
                          color: OpsUiTokens.primarySoft,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: OpsSpacing.lg),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            name.isEmpty ? 'Unnamed Admin' : name,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: OpsTypography.subtitle.copyWith(
                              color: OpsUiTokens.textPrimary,
                            ),
                          ),
                          const SizedBox(height: OpsSpacing.md),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              ...summaryItems.map(
                                (item) => _detailChip(
                                  icon: item.icon,
                                  label: item.label,
                                ),
                              ),
                              _locationStatusPill(
                                  hasMapLocation: hasMapLocation),
                            ],
                          ),
                        ],
                      ),
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          onPressed: () => _editAdmin(admin),
                          icon: const Icon(Icons.edit_outlined),
                          tooltip: 'Edit admin',
                        ),
                        IconButton(
                          onPressed: () => _resetAdminPassword(admin),
                          icon: const Icon(Icons.lock_reset_rounded),
                          tooltip: 'Reset password',
                        ),
                        IconButton(
                          onPressed: () => _deleteAdmin(admin),
                          icon: const Icon(Icons.delete_outline_rounded),
                          tooltip: 'Remove admin',
                        ),
                      ],
                    ),
                  ],
                ),
              if (isCompact && summaryItems.length > 1) ...[
                const SizedBox(height: 12),
                ...summaryItems.skip(1).map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _detailRow(icon: item.icon, label: item.label),
                      ),
                    ),
              ],
              ..._buildAdminMetaRows(display),
              if (officeAddress.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: OpsSpacing.cardCompact,
                  decoration: OpsDecorations.mutedPanel(
                    borderColor: OpsUiTokens.divider,
                    radius: OpsRadius.md,
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(
                          Icons.location_on_outlined,
                          size: 16,
                          color: OpsUiTokens.primarySoft,
                        ),
                      ),
                      const SizedBox(width: OpsSpacing.sm),
                      Expanded(
                        child: Text(
                          _compactValue(officeAddress, maxLength: 110),
                          style: OpsTypography.body,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _detailChip({required IconData icon, required String label}) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: OpsSpacing.md,
        vertical: OpsSpacing.sm,
      ),
      decoration: OpsDecorations.status(OpsUiTokens.primarySoft),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: OpsUiTokens.primarySoft),
          const SizedBox(width: OpsSpacing.sm),
          Text(
            label,
            style: OpsTypography.caption.copyWith(
              color: OpsUiTokens.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _detailRow({required IconData icon, required String label}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 15, color: OpsUiTokens.primarySoft),
        const SizedBox(width: OpsSpacing.sm),
        Expanded(
          child: Text(
            label,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: OpsTypography.body,
          ),
        ),
      ],
    );
  }

  Widget _locationStatusPill({required bool hasMapLocation}) {
    final tone = hasMapLocation ? OpsUiTokens.success : OpsUiTokens.warningDeep;
    final icon = hasMapLocation
        ? Icons.explore_rounded
        : Icons.location_searching_rounded;
    final label = hasMapLocation ? 'Map Linked' : 'Address Only';
    return OpsStatusBadge(
      label: label,
      tone: tone,
      icon: icon,
      compact: true,
    );
  }

  List<Widget> _buildAdminMetaRows(_AdminDisplayData display) {
    final rows = <Widget>[];

    if (display.id.isNotEmpty) {
      rows.add(const SizedBox(height: 12));
      rows.add(
        _labeledDetailRow(
          label: 'Admin ID',
          value: _compactValue(display.id, maxLength: 42),
          icon: Icons.badge_outlined,
        ),
      );
    }

    final createdLabel = _formatUpdatedAt(display.createdAt);
    if (createdLabel.isNotEmpty) {
      rows.add(const SizedBox(height: 8));
      rows.add(
        _labeledDetailRow(
          label: 'Created At',
          value: createdLabel,
          icon: Icons.event_available_rounded,
        ),
      );
    }

    final updatedLabel = _formatUpdatedAt(display.updatedAt);
    if (updatedLabel.isNotEmpty) {
      rows.add(const SizedBox(height: 8));
      rows.add(
        _labeledDetailRow(
          label: 'Updated At',
          value: updatedLabel,
          icon: Icons.schedule_rounded,
        ),
      );
    }

    if (display.officeLat != null && display.officeLng != null) {
      rows.add(const SizedBox(height: 8));
      rows.add(
        _labeledDetailRow(
          label: 'Office Coordinates',
          value: _formatCoordinatePair(display.officeLat!, display.officeLng!),
          icon: Icons.pin_drop_outlined,
        ),
      );
    }

    return rows;
  }

  Widget _labeledDetailRow({
    required String label,
    required String value,
    required IconData icon,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: OpsSpacing.md,
        vertical: OpsSpacing.sm,
      ),
      decoration: OpsDecorations.mutedPanel(
        borderColor: OpsUiTokens.divider,
        radius: OpsRadius.md,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon, size: 15, color: OpsUiTokens.primarySoft),
          ),
          const SizedBox(width: OpsSpacing.sm),
          Expanded(
            child: RichText(
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              text: TextSpan(
                children: [
                  TextSpan(
                    text: '$label: ',
                    style: OpsTypography.caption.copyWith(
                      color: OpsUiTokens.textTertiary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  TextSpan(
                    text: value,
                    style: OpsTypography.caption.copyWith(
                      color: OpsUiTokens.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _compactValue(String value, {int maxLength = 36}) {
    final cleaned = value.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (cleaned.length <= maxLength) return cleaned;
    return '${cleaned.substring(0, maxLength - 1)}…';
  }

  _AdminDisplayData _normalizeAdmin(Map<String, dynamic> admin) {
    final blob =
        admin.entries.map((entry) => '${entry.key}: ${entry.value}').join(', ');

    String pick(String key) {
      final direct = _cleanAdminValue(admin[key]);
      if (direct.isNotEmpty && !_looksLikeAdminBlob(direct)) {
        return direct;
      }

      final parsed = _parseAdminField(blob, key);
      if (parsed.isNotEmpty) return parsed;

      return direct;
    }

    return _AdminDisplayData(
      id: pick('id'),
      name: pick('name'),
      mobile: pick('mobile'),
      email: pick('email'),
      officeName: pick('office_name'),
      officeLocation: pick('office_location'),
      officeAddress: pick('office_address').isNotEmpty
          ? pick('office_address')
          : pick('office_location'),
      officeLat: _parseDoubleValue(admin['office_lat']) ??
          _parseDoubleValue(pick('office_lat')),
      officeLng: _parseDoubleValue(admin['office_lng']) ??
          _parseDoubleValue(pick('office_lng')),
      createdAt: pick('created_at'),
      updatedAt: pick('updated_at'),
    );
  }

  String _cleanAdminValue(dynamic value) {
    if (value == null) return '';
    final text = value.toString().trim();
    if (text.isEmpty || text.toLowerCase() == 'null') return '';
    return text;
  }

  double? _parseDoubleValue(dynamic value) {
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty || text.toLowerCase() == 'null') return null;
    return double.tryParse(text);
  }

  bool _looksLikeAdminBlob(String value) {
    return value.contains('id:') ||
        value.contains('name:') ||
        value.contains('mobile:') ||
        value.contains('office_name:') ||
        value.contains('{') ||
        value.contains('}');
  }

  String _parseAdminField(String blob, String field) {
    final pattern = RegExp(
      '${RegExp.escape(field)}\\s*:\\s*([^,]+)',
      caseSensitive: false,
    );
    final match = pattern.firstMatch(blob);
    if (match == null) return '';
    final value = (match.group(1) ?? '').trim();
    if (value.toLowerCase() == 'null') return '';
    return value;
  }

  String _formatUpdatedAt(String value) {
    final cleaned = value.trim();
    if (cleaned.isEmpty) return '';
    try {
      final parsed = DateTime.parse(cleaned).toLocal();
      const months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
      ];
      final day = parsed.day.toString().padLeft(2, '0');
      final month = months[parsed.month - 1];
      final year = parsed.year.toString();
      final minute = parsed.minute.toString().padLeft(2, '0');
      final hour12 = parsed.hour == 0
          ? 12
          : parsed.hour > 12
              ? parsed.hour - 12
              : parsed.hour;
      final amPm = parsed.hour >= 12 ? 'PM' : 'AM';
      return '$day $month $year, $hour12:$minute $amPm';
    } catch (_) {
      return _compactValue(cleaned.replaceFirst('T', ' '), maxLength: 24);
    }
  }

  String _formatPlacemark(Placemark placemark) {
    final parts = <String>[
      placemark.name ?? '',
      placemark.street ?? '',
      placemark.subLocality ?? '',
      placemark.locality ?? '',
      placemark.administrativeArea ?? '',
      placemark.postalCode ?? '',
    ];
    final seen = <String>{};
    final cleaned = <String>[];
    for (final part in parts) {
      final value = part.trim();
      if (value.isEmpty) continue;
      final normalized = value.toLowerCase();
      if (seen.add(normalized)) {
        cleaned.add(value);
      }
    }
    return cleaned.join(', ');
  }

  String _formatCoordinatePair(double lat, double lng) {
    return '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
  }

  String _initialsFor(String name) {
    final parts = name
        .split(RegExp(r'\s+'))
        .where((part) => part.isNotEmpty)
        .take(2)
        .map((part) => part[0].toUpperCase())
        .toList();
    if (parts.isEmpty) return 'AD';
    return parts.join();
  }
}

class _AdminDisplayData {
  const _AdminDisplayData({
    required this.id,
    required this.name,
    required this.mobile,
    required this.email,
    required this.officeName,
    required this.officeLocation,
    required this.officeAddress,
    required this.officeLat,
    required this.officeLng,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String name;
  final String mobile;
  final String email;
  final String officeName;
  final String officeLocation;
  final String officeAddress;
  final double? officeLat;
  final double? officeLng;
  final String createdAt;
  final String updatedAt;
}

class _HeroChip extends StatelessWidget {
  const _HeroChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: OpsSpacing.lg,
        vertical: OpsSpacing.md,
      ),
      decoration: BoxDecoration(
        color: OpsUiTokens.textPrimary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(OpsRadius.full),
        border: Border.all(
          color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: OpsUiTokens.primarySoft),
          const SizedBox(width: OpsSpacing.sm),
          Text(
            label,
            style: OpsTypography.caption.copyWith(
              color: OpsUiTokens.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
