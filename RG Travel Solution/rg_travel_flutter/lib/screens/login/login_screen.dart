// lib/screens/login/login_screen.dart
//
// RG Travel Solution — Role-Based Login Screen (Redesigned)
//
// Production-ready login screen with:
// - Dark futuristic glassmorphism UI
// - Responsive layout (desktop 2-column, mobile 1-column)
// - Role-based authentication (Admin, Driver, Employee)
// - Sub-tabs for Driver/Employee (Login/Registration)
// - Field validations with inline errors
// - Backend integration via AuthService
// - Session management via SessionStore

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geocoding/geocoding.dart';
import 'package:latlong2/latlong.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/core/utils/constants.dart';
import 'package:rg_travel_flutter/core/storage/session_store.dart';
import 'package:rg_travel_flutter/services/auth_service.dart';
import 'package:rg_travel_flutter/utils/validators.dart';
import 'package:rg_travel_flutter/widgets/auth/role_tabs.dart' as role_tab;
import 'package:rg_travel_flutter/widgets/auth/sub_tabs.dart';
import 'package:rg_travel_flutter/widgets/auth/custom_text_field.dart';
import 'package:rg_travel_flutter/widgets/common/map_coordinate_picker_sheet.dart';
import 'package:rg_travel_flutter/widgets/common/rg_logo.dart';
import 'package:rg_travel_flutter/widgets/common/status_banner.dart';
import 'dart:async';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // ==================== State Variables ====================
  role_tab.UserRole _selectedRole = role_tab.UserRole.admin;
  AuthMode _authMode = AuthMode.login;
  bool _loading = false;
  String? _statusMessage;
  StatusType? _statusType;
  bool _loadingCompanies = false;
  List<CompanyOption> _companies = const [];
  String? _selectedDriverAdminId;
  String? _selectedEmployeeAdminId;
  final _driverCompanySearchCtrl = TextEditingController();
  final _employeeCompanySearchCtrl = TextEditingController();

  // ==================== Form Controllers ====================
  // Admin
  final _adminNameCtrl = TextEditingController();
  final _adminMobileCtrl = TextEditingController();
  final _adminPasswordCtrl = TextEditingController();

  // Driver
  final _driverNameCtrl = TextEditingController();
  final _driverMobileCtrl = TextEditingController();
  final _driverDLCtrl = TextEditingController();
  final _driverCabCtrl = TextEditingController();
  final _driverHomeTownCtrl = TextEditingController();
  String _driverVehicleType = '4'; // 4 or 6 seater
  Timer? _driverAddressDebounce;
  bool _isResolvingDriverAddress = false;
  String? _driverAddressResolveNote;
  double? _driverPickedLat;
  double? _driverPickedLng;

  // Employee
  final _employeeNameCtrl = TextEditingController();
  final _employeeMobileCtrl = TextEditingController();
  final _employeeIdCtrl = TextEditingController();
  final _employeeLoginTimeCtrl = TextEditingController();
  final _employeeLogoutTimeCtrl = TextEditingController();
  final _employeeHomeCtrl = TextEditingController();
  Timer? _employeeAddressDebounce;
  bool _isResolvingEmployeeAddress = false;
  String? _employeeAddressResolveNote;
  double? _employeePickedLat;
  double? _employeePickedLng;

  // ==================== Validation Errors ====================
  final Map<String, String?> _errors = {};

  @override
  void initState() {
    super.initState();
    _loadCompanies();
  }

  @override
  void dispose() {
    // Admin
    _adminNameCtrl.dispose();
    _adminMobileCtrl.dispose();
    _adminPasswordCtrl.dispose();

    // Driver
    _driverNameCtrl.dispose();
    _driverMobileCtrl.dispose();
    _driverDLCtrl.dispose();
    _driverCabCtrl.dispose();
    _driverHomeTownCtrl.dispose();
    _driverCompanySearchCtrl.dispose();
    _driverAddressDebounce?.cancel();

    // Employee
    _employeeNameCtrl.dispose();
    _employeeMobileCtrl.dispose();
    _employeeIdCtrl.dispose();
    _employeeLoginTimeCtrl.dispose();
    _employeeLogoutTimeCtrl.dispose();
    _employeeHomeCtrl.dispose();
    _employeeCompanySearchCtrl.dispose();
    _employeeAddressDebounce?.cancel();

    super.dispose();
  }

  // ==================== Validation Methods ====================
  void _clearErrors() {
    setState(() {
      _errors.clear();
    });
  }

  void _clearStatus() {
    setState(() {
      _statusMessage = null;
      _statusType = null;
    });
  }

  bool _validateAdminLogin() {
    _clearErrors();
    bool isValid = true;

    final nameError = Validators.validateName(_adminNameCtrl.text);
    if (nameError != null) {
      _errors['adminName'] = nameError;
      isValid = false;
    }

    final mobileError = Validators.validateMobile(_adminMobileCtrl.text);
    if (mobileError != null) {
      _errors['adminMobile'] = mobileError;
      isValid = false;
    }

    final passwordError = Validators.validatePassword(_adminPasswordCtrl.text);
    if (passwordError != null) {
      _errors['adminPassword'] = passwordError;
      isValid = false;
    }

    setState(() {});
    return isValid;
  }

  bool _validateDriverLogin() {
    _clearErrors();
    bool isValid = true;

    final mobileError = Validators.validateMobile(_driverMobileCtrl.text);
    if (mobileError != null) {
      _errors['driverMobile'] = mobileError;
      isValid = false;
    }

    final dlError = Validators.validateDLNo(_driverDLCtrl.text);
    if (dlError != null) {
      _errors['driverDL'] = dlError;
      isValid = false;
    }

    final cabError = Validators.validateCabNo(_driverCabCtrl.text);
    if (cabError != null) {
      _errors['driverCab'] = cabError;
      isValid = false;
    }

    setState(() {});
    return isValid;
  }

  bool _validateDriverRegistration() {
    _clearErrors();
    bool isValid = true;

    final nameError = Validators.validateName(_driverNameCtrl.text);
    if (nameError != null) {
      _errors['driverName'] = nameError;
      isValid = false;
    }

    final mobileError = Validators.validateMobile(_driverMobileCtrl.text);
    if (mobileError != null) {
      _errors['driverMobile'] = mobileError;
      isValid = false;
    }

    final dlError = Validators.validateDLNo(_driverDLCtrl.text);
    if (dlError != null) {
      _errors['driverDL'] = dlError;
      isValid = false;
    }

    final cabError = Validators.validateCabNo(_driverCabCtrl.text);
    if (cabError != null) {
      _errors['driverCab'] = cabError;
      isValid = false;
    }

    final homeTownError = Validators.validateAddress(_driverHomeTownCtrl.text);
    if (homeTownError != null) {
      _errors['driverHomeTown'] = homeTownError;
      isValid = false;
    }

    if ((_selectedDriverAdminId ?? '').trim().isEmpty) {
      _errors['driverCompany'] = 'Select your company';
      isValid = false;
    }

    setState(() {});
    return isValid;
  }

  bool _validateEmployeeLogin() {
    _clearErrors();
    bool isValid = true;

    final mobileError = Validators.validateMobile(_employeeMobileCtrl.text);
    if (mobileError != null) {
      _errors['employeeMobile'] = mobileError;
      isValid = false;
    }

    final idError = Validators.validateEmployeeId(_employeeIdCtrl.text);
    if (idError != null) {
      _errors['employeeId'] = idError;
      isValid = false;
    }

    setState(() {});
    return isValid;
  }

  bool _validateEmployeeRegistration() {
    _clearErrors();
    bool isValid = true;

    final nameError = Validators.validateName(_employeeNameCtrl.text);
    if (nameError != null) {
      _errors['employeeName'] = nameError;
      isValid = false;
    }

    final mobileError = Validators.validateMobile(_employeeMobileCtrl.text);
    if (mobileError != null) {
      _errors['employeeMobile'] = mobileError;
      isValid = false;
    }

    final loginTimeError = Validators.validateTime(_employeeLoginTimeCtrl.text);
    if (loginTimeError != null) {
      _errors['employeeLoginTime'] = loginTimeError;
      isValid = false;
    }

    final logoutTimeError =
        Validators.validateTime(_employeeLogoutTimeCtrl.text);
    if (logoutTimeError != null) {
      _errors['employeeLogoutTime'] = logoutTimeError;
      isValid = false;
    }

    final homeError = Validators.validateAddress(_employeeHomeCtrl.text);
    if (homeError != null) {
      _errors['employeeHome'] = homeError;
      isValid = false;
    }

    if ((_selectedEmployeeAdminId ?? '').trim().isEmpty) {
      _errors['employeeCompany'] = 'Select your company';
      isValid = false;
    }

    setState(() {});
    return isValid;
  }

  Future<void> _loadCompanies() async {
    setState(() {
      _loadingCompanies = true;
    });
    try {
      final companies = await AuthService.getCompanies();
      if (!mounted) return;
      setState(() {
        _companies = companies;
        if (_selectedEmployeeAdminId == null && companies.length == 1) {
          _selectedEmployeeAdminId = companies.first.id;
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _companies = const [];
      });
    } finally {
      if (mounted) {
        setState(() {
          _loadingCompanies = false;
        });
      }
    }
  }

  // ==================== Actions ====================
  Future<void> _handleSubmit() async {
    if (_loading) return;

    _clearStatus();

    // Validate based on role and mode
    bool isValid = false;
    if (_selectedRole == role_tab.UserRole.admin) {
      isValid = _validateAdminLogin();
    } else if (_selectedRole == role_tab.UserRole.driver) {
      isValid = _authMode == AuthMode.login
          ? _validateDriverLogin()
          : _validateDriverRegistration();
    } else {
      isValid = _authMode == AuthMode.login
          ? _validateEmployeeLogin()
          : _validateEmployeeRegistration();
    }

    if (!isValid) {
      setState(() {
        _statusMessage = 'Please fix the errors above';
        _statusType = StatusType.error;
      });
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      if (_selectedRole == role_tab.UserRole.admin) {
        await _loginAdmin();
      } else if (_selectedRole == role_tab.UserRole.driver) {
        if (_authMode == AuthMode.login) {
          await _loginDriver();
        } else {
          await _registerDriver();
        }
      } else {
        if (_authMode == AuthMode.login) {
          await _loginEmployee();
        } else {
          await _registerEmployee();
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _statusMessage = e.toString().replaceFirst('Exception: ', '');
          _statusType = StatusType.error;
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _loginAdmin() async {
    final result = await AuthService.adminLogin(
      name: _adminNameCtrl.text.trim(),
      mobile: _adminMobileCtrl.text.trim(),
      password: _adminPasswordCtrl.text.trim(),
    );

    // ✅ ROBUST: AuthService now guarantees (success=true + token + id) OR (success=false)
    if (!result.success) {
      // Real failure (wrong password, etc.)
      throw Exception(result.message);
    }

    // Safety check just in case ID is somehow null but success=true
    if (result.userId == null) {
      throw Exception("Login succeeded but User ID is missing from response.");
    }

    // Save session
    await SessionStore.saveSession(
      role: UserRole.admin,
      userId: result.userId!,
      token: result.token,
      name: _adminNameCtrl.text.trim(),
      mobile: _adminMobileCtrl.text.trim(),
    );

    if (!mounted) return;

    debugPrint(
        "✅ Admin Login Success. Navigating to Dashboard with adminId: ${result.userId}");

    // ✅ NAVIGATE IMMEDIATELY
    Navigator.pushReplacementNamed(
      context,
      AppRoutes.adminDashboard,
      arguments: {'adminId': result.userId},
    );
  }

  Future<void> _loginDriver() async {
    final result = await AuthService.driverLogin(
      mobile: _driverMobileCtrl.text.trim(),
      dlNo: Validators.normalizeDLNo(_driverDLCtrl.text),
      cabNo: Validators.normalizeCabNo(_driverCabCtrl.text),
    );

    if (!result.success) {
      throw Exception(result.message);
    }

    if (result.userId == null) {
      throw Exception("Login succeeded but Driver ID is missing.");
    }

    // Save session
    await SessionStore.saveSession(
      role: UserRole.driver,
      userId: result.userId!,
      token: result.token,
      mobile: _driverMobileCtrl.text.trim(),
    );

    if (mounted) {
      Navigator.pushReplacementNamed(
        context,
        AppRoutes.driverDashboard,
        arguments: {'driverId': result.userId!},
      );
    }
  }

  Future<void> _registerDriver() async {
    final result = await AuthService.driverSignupRequest(
      name: _driverNameCtrl.text.trim(),
      mobile: _driverMobileCtrl.text.trim(),
      dlNo: Validators.normalizeDLNo(_driverDLCtrl.text),
      cabNo: Validators.normalizeCabNo(_driverCabCtrl.text),
      vehicleType: int.parse(_driverVehicleType),
      homeTown: _driverHomeTownCtrl.text.trim(),
      adminId: _selectedDriverAdminId!.trim(),
      homeLat: _driverPickedLat,
      homeLng: _driverPickedLng,
    );

    if (mounted) {
      setState(() {
        _statusMessage = result.message;
        _statusType = result.success ? StatusType.success : StatusType.error;
      });
    }

    // Clear form on success
    if (result.success) {
      _resetForm();
    }
  }

  Future<void> _loginEmployee() async {
    final result = await AuthService.employeeLogin(
      mobile: _employeeMobileCtrl.text.trim(),
      employeeCode: _employeeIdCtrl.text.trim(),
    );

    if (!result.success) {
      throw Exception(result.message);
    }

    if (result.userId == null) {
      throw Exception("Login succeeded but Employee ID is missing.");
    }

    // Save session
    await SessionStore.saveSession(
      role: UserRole.employee,
      userId: result.userId!,
      token: result.token,
      mobile: _employeeMobileCtrl.text.trim(),
    );

    if (mounted) {
      Navigator.pushReplacementNamed(
        context,
        AppRoutes.employeeDashboard,
        arguments: {'employeeId': result.userId!},
      );
    }
  }

  Future<void> _registerEmployee() async {
    final result = await AuthService.employeeSignupRequest(
      name: _employeeNameCtrl.text.trim(),
      mobile: _employeeMobileCtrl.text.trim(),
      loginTime: _employeeLoginTimeCtrl.text.trim(),
      logoutTime: _employeeLogoutTimeCtrl.text.trim(),
      homeAddress: _employeeHomeCtrl.text.trim(),
      adminId: _selectedEmployeeAdminId!.trim(),
      homeLat: _employeePickedLat,
      homeLng: _employeePickedLng,
    );

    if (mounted) {
      setState(() {
        _statusMessage = result.message;
        _statusType = result.success ? StatusType.success : StatusType.error;
      });
    }

    // Clear form on success
    if (result.success) {
      _resetForm();
    }
  }

  void _resetForm() {
    // Clear all controllers
    _adminNameCtrl.clear();
    _adminMobileCtrl.clear();
    _adminPasswordCtrl.clear();

    _driverNameCtrl.clear();
    _driverMobileCtrl.clear();
    _driverDLCtrl.clear();
    _driverCabCtrl.clear();
    _driverHomeTownCtrl.clear();
    _driverAddressDebounce?.cancel();
    _driverAddressResolveNote = null;
    _driverPickedLat = null;
    _driverPickedLng = null;
    _selectedDriverAdminId =
        _companies.length == 1 ? _companies.first.id : null;
    _driverCompanySearchCtrl.clear();

    _employeeNameCtrl.clear();
    _employeeMobileCtrl.clear();
    _employeeIdCtrl.clear();
    _employeeLoginTimeCtrl.clear();
    _employeeLogoutTimeCtrl.clear();
    _employeeHomeCtrl.clear();
    _employeeAddressDebounce?.cancel();
    _employeeAddressResolveNote = null;
    _employeePickedLat = null;
    _employeePickedLng = null;
    _selectedEmployeeAdminId =
        _companies.length == 1 ? _companies.first.id : null;
    _employeeCompanySearchCtrl.clear();

    // Clear errors and status
    _clearErrors();
    _clearStatus();

    // Reset vehicle type
    setState(() {
      _driverVehicleType = '4';
    });
  }

  Future<void> _pickTime(TextEditingController controller) async {
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: AppThemeColors.primary,
              surface: AppThemeColors.surface,
            ),
          ),
          child: child!,
        );
      },
    );

    if (time != null) {
      controller.text = Validators.formatTime(time.hour, time.minute);
    }
  }

  CompanyOption? _findCompanyById(String? companyId) {
    if (companyId == null || companyId.trim().isEmpty) return null;
    for (final company in _companies) {
      if (company.id == companyId) return company;
    }
    return null;
  }

  List<CompanyOption> _filterCompanies(String query) {
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) return _companies;
    return _companies.where((company) {
      final haystack = [
        company.companyName,
        company.name,
        company.officeAddress,
      ].join(' ').toLowerCase();
      return haystack.contains(normalized);
    }).toList();
  }

  void _applyCompanySearch({
    required TextEditingController controller,
    required bool isDriver,
    required String errorKey,
    required String value,
  }) {
    final filtered = _filterCompanies(value);
    setState(() {
      if (filtered.length == 1) {
        if (isDriver) {
          _selectedDriverAdminId = filtered.first.id;
        } else {
          _selectedEmployeeAdminId = filtered.first.id;
        }
        _errors.remove(errorKey);
      }
    });
  }

  String _driverCoordLabel() {
    if (_driverPickedLat == null || _driverPickedLng == null) {
      return 'No map point selected';
    }
    return '${_driverPickedLat!.toStringAsFixed(6)}, ${_driverPickedLng!.toStringAsFixed(6)}';
  }

  Future<void> _openDriverMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Select Hometown Location',
        addressHint: _driverHomeTownCtrl.text.trim(),
        initialLat: _driverPickedLat,
        initialLng: _driverPickedLng,
      ),
    );

    if (selected == null || !mounted) return;
    setState(() {
      _driverPickedLat = selected.latitude;
      _driverPickedLng = selected.longitude;
      _driverAddressResolveNote = 'Map location selected';
    });
    await _reverseGeocodeDriverSelection();
  }

  Future<void> _reverseGeocodeDriverSelection() async {
    final lat = _driverPickedLat;
    final lng = _driverPickedLng;
    if (lat == null || lng == null || !mounted) return;
    setState(() {
      _isResolvingDriverAddress = true;
      _driverAddressResolveNote = 'Saving selected coordinates in address...';
    });
    setState(() {
      _driverHomeTownCtrl.text =
          '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
      _driverAddressResolveNote = 'Address set to selected map coordinates';
      _isResolvingDriverAddress = false;
    });
  }

  void _onDriverAddressChanged(String value) {
    _driverAddressDebounce?.cancel();
    final address = value.trim();
    if (address.length < 5) {
      if (mounted) {
        setState(() {
          _driverAddressResolveNote = null;
        });
      }
      return;
    }
    _driverAddressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveDriverAddress(address);
    });
  }

  Future<void> _autoResolveDriverAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    setState(() {
      _isResolvingDriverAddress = true;
      _driverAddressResolveNote = 'Resolving address on map...';
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final loc = locations.first;
        setState(() {
          _driverPickedLat = loc.latitude;
          _driverPickedLng = loc.longitude;
          _driverAddressResolveNote = 'Auto-centered from typed address';
        });
      } else {
        setState(() {
          _driverAddressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _driverAddressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isResolvingDriverAddress = false;
      });
    }
  }

  String _employeeCoordLabel() {
    if (_employeePickedLat == null || _employeePickedLng == null) {
      return 'No map point selected';
    }
    return '${_employeePickedLat!.toStringAsFixed(6)}, ${_employeePickedLng!.toStringAsFixed(6)}';
  }

  Future<void> _openEmployeeMapPicker() async {
    final selected = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MapCoordinatePickerSheet(
        title: 'Select Home Location',
        addressHint: _employeeHomeCtrl.text.trim(),
        initialLat: _employeePickedLat,
        initialLng: _employeePickedLng,
      ),
    );

    if (selected == null) return;
    if (!mounted) return;
    setState(() {
      _employeePickedLat = selected.latitude;
      _employeePickedLng = selected.longitude;
      _employeeAddressResolveNote = 'Map location selected';
    });
    await _reverseGeocodeEmployeeSelection();
  }

  Future<void> _reverseGeocodeEmployeeSelection() async {
    final lat = _employeePickedLat;
    final lng = _employeePickedLng;
    if (lat == null || lng == null || !mounted) return;
    setState(() {
      _isResolvingEmployeeAddress = true;
      _employeeAddressResolveNote = 'Saving selected coordinates in address...';
    });
    setState(() {
      _employeeHomeCtrl.text =
          '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}';
      _employeeAddressResolveNote = 'Address set to selected map coordinates';
      _isResolvingEmployeeAddress = false;
    });
  }

  void _onEmployeeAddressChanged(String value) {
    _employeeAddressDebounce?.cancel();
    final address = value.trim();
    if (address.length < 5) {
      if (mounted) {
        setState(() {
          _employeeAddressResolveNote = null;
        });
      }
      return;
    }
    _employeeAddressDebounce = Timer(const Duration(milliseconds: 900), () {
      _autoResolveEmployeeAddress(address);
    });
  }

  Future<void> _autoResolveEmployeeAddress(String address) async {
    if (!mounted || address.trim().length < 5) return;
    setState(() {
      _isResolvingEmployeeAddress = true;
      _employeeAddressResolveNote = 'Resolving address on map...';
    });
    try {
      final locations = await locationFromAddress(address);
      if (!mounted) return;
      if (locations.isNotEmpty) {
        final loc = locations.first;
        setState(() {
          _employeePickedLat = loc.latitude;
          _employeePickedLng = loc.longitude;
          _employeeAddressResolveNote = 'Auto-centered from typed address';
        });
      } else {
        setState(() {
          _employeeAddressResolveNote = "Address not found. Use 'Pick on Map'.";
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _employeeAddressResolveNote = "Auto-geocode failed. Use 'Pick on Map'.";
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isResolvingEmployeeAddress = false;
      });
    }
  }

  // ==================== UI Build ====================
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      body: Container(
        decoration: BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.topRight,
            radius: 1.2,
            colors: [
              AppThemeColors.primary.withValues(alpha: 0.08),
              AppThemeColors.background,
              AppThemeColors.background,
            ],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isDesktop = constraints.maxWidth > 900;
              return isDesktop ? _buildDesktopLayout() : _buildMobileLayout();
            },
          ),
        ),
      ),
    );
  }

  Widget _buildDesktopLayout() {
    return Row(
      children: [
        // Left: Hero Section
        Expanded(
          child: _buildHeroSection(),
        ),
        // Right: Form Card
        SizedBox(
          width: 600,
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: _buildFormCard(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMobileLayout() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          children: [
            const SizedBox(height: AppSpacing.lg),
            _buildMobileHeader(),
            const SizedBox(height: AppSpacing.xl),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 500),
              child: _buildFormCard(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeroSection() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const RGLogo(
            width: 360,
            height: 180,
            showGlow: true,
          ),
          const SizedBox(height: AppSpacing.xl),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Role Based Login System',
            style: AppTypography.bodyLarge.copyWith(
              color: AppThemeColors.textSecondary,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Secure access for Admin, Driver, and Employee',
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMobileHeader() {
    return Column(
      children: [
        const RGLogo(
          width: 240,
          height: 120,
          showGlow: true,
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Role Based Login',
          style: AppTypography.bodyLarge.copyWith(
            color: AppThemeColors.textSecondary,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildFormCard() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: AppDecorations.glassmorphicCard(
        borderRadius: AppRadius.xl,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Text(
                'Login / Registration',
                style: AppTypography.headlineSmall.copyWith(
                  color: AppThemeColors.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppThemeColors.primary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(AppRadius.full),
                  border: Border.all(
                    color: AppThemeColors.primary.withValues(alpha: 0.3),
                  ),
                ),
                child: Text(
                  _getRoleLabel(),
                  style: AppTypography.labelSmall.copyWith(
                    color: AppThemeColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),

          // Role Tabs
          role_tab.RoleTabs(
            selectedRole: _selectedRole,
            enabled: !_loading,
            onRoleChanged: (role) {
              setState(() {
                _selectedRole = role;
                _authMode = AuthMode.login;
                _clearErrors();
                _clearStatus();
              });
            },
          ),
          const SizedBox(height: AppSpacing.lg),

          // Sub Tabs (for Driver/Employee)
          if (_selectedRole != role_tab.UserRole.admin) ...[
            SubTabs(
              selectedMode: _authMode,
              enabled: !_loading,
              onModeChanged: (mode) {
                setState(() {
                  _authMode = mode;
                  _clearErrors();
                  _clearStatus();
                });
              },
            ),
            const SizedBox(height: AppSpacing.lg),
          ],

          // Form Fields
          _buildFormFields(),

          const SizedBox(height: AppSpacing.lg),

          // Status Banner
          if (_statusMessage != null && _statusType != null) ...[
            StatusBanner(
              message: _statusMessage!,
              type: _statusType!,
              onDismiss: _clearStatus,
            ),
            const SizedBox(height: AppSpacing.lg),
          ],

          // Action Buttons
          if (_loading)
            Center(
              child: CircularProgressIndicator(
                valueColor:
                    const AlwaysStoppedAnimation<Color>(AppThemeColors.primary),
              ),
            )
          else
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: ElevatedButton(
                    onPressed: _handleSubmit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          AppThemeColors.primary.withValues(alpha: 0.2),
                      foregroundColor: AppThemeColors.textPrimary,
                      padding:
                          const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md),
                        side: BorderSide(
                          color: AppThemeColors.primary.withValues(alpha: 0.4),
                        ),
                      ),
                    ),
                    child: Text(
                      _getSubmitButtonLabel(),
                      style: AppTypography.labelLarge.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _resetForm,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppThemeColors.textSecondary,
                      padding:
                          const EdgeInsets.symmetric(vertical: AppSpacing.md),
                      side: BorderSide(
                        color: AppThemeColors.border,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadius.md),
                      ),
                    ),
                    child: Text(
                      'Reset',
                      style: AppTypography.labelLarge.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildFormFields() {
    if (_selectedRole == role_tab.UserRole.admin) {
      return _buildAdminFields();
    } else if (_selectedRole == role_tab.UserRole.driver) {
      return _authMode == AuthMode.login
          ? _buildDriverLoginFields()
          : _buildDriverRegistrationFields();
    } else {
      return _authMode == AuthMode.login
          ? _buildEmployeeLoginFields()
          : _buildEmployeeRegistrationFields();
    }
  }

  Widget _buildAdminFields() {
    return Column(
      children: [
        CustomTextField(
          controller: _adminNameCtrl,
          label: 'Admin Name',
          hint: 'Enter your name',
          icon: Icons.person,
          errorText: _errors['adminName'],
          onChanged: (_) {
            if (_errors['adminName'] != null) {
              setState(() => _errors.remove('adminName'));
            }
          },
        ),
        const SizedBox(height: 16),
        CustomTextField(
          controller: _adminMobileCtrl,
          label: 'Mobile Number',
          hint: '10 digits',
          icon: Icons.phone,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          errorText: _errors['adminMobile'],
          onChanged: (_) {
            if (_errors['adminMobile'] != null) {
              setState(() => _errors.remove('adminMobile'));
            }
          },
        ),
        const SizedBox(height: 16),
        CustomTextField(
          controller: _adminPasswordCtrl,
          label: 'Password',
          hint: 'Min 4 characters',
          icon: Icons.lock,
          obscureText: true,
          errorText: _errors['adminPassword'],
          onChanged: (_) {
            if (_errors['adminPassword'] != null) {
              setState(() => _errors.remove('adminPassword'));
            }
          },
        ),
      ],
    );
  }

  Widget _buildDriverLoginFields() {
    return Column(
      children: [
        CustomTextField(
          controller: _driverMobileCtrl,
          label: 'Mobile Number',
          hint: '10 digits',
          icon: Icons.phone,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          errorText: _errors['driverMobile'],
          onChanged: (_) {
            if (_errors['driverMobile'] != null) {
              setState(() => _errors.remove('driverMobile'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverDLCtrl,
          label: 'DL Number',
          hint: 'MH1234567890123 (2 letters + 13 digits)',
          icon: Icons.credit_card,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9]')),
            LengthLimitingTextInputFormatter(15),
            TextInputFormatter.withFunction((oldValue, newValue) {
              return TextEditingValue(
                text: newValue.text.toUpperCase(),
                selection: newValue.selection,
              );
            }),
          ],
          errorText: _errors['driverDL'],
          onChanged: (_) {
            if (_errors['driverDL'] != null) {
              setState(() => _errors.remove('driverDL'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverCabCtrl,
          label: 'Cab Number',
          hint: 'MH12AB1234',
          icon: Icons.directions_car,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9]')),
            LengthLimitingTextInputFormatter(10),
            TextInputFormatter.withFunction((oldValue, newValue) {
              return TextEditingValue(
                text: newValue.text.toUpperCase().replaceAll(' ', ''),
                selection: newValue.selection,
              );
            }),
          ],
          errorText: _errors['driverCab'],
          onChanged: (_) {
            if (_errors['driverCab'] != null) {
              setState(() => _errors.remove('driverCab'));
            }
          },
        ),
      ],
    );
  }

  Widget _buildDriverRegistrationFields() {
    return Column(
      children: [
        CustomTextField(
          controller: _driverNameCtrl,
          label: 'Driver Name',
          hint: 'Enter your full name',
          icon: Icons.person,
          errorText: _errors['driverName'],
          onChanged: (_) {
            if (_errors['driverName'] != null) {
              setState(() => _errors.remove('driverName'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverMobileCtrl,
          label: 'Mobile Number',
          hint: '10 digits',
          icon: Icons.phone,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          errorText: _errors['driverMobile'],
          onChanged: (_) {
            if (_errors['driverMobile'] != null) {
              setState(() => _errors.remove('driverMobile'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverDLCtrl,
          label: 'DL Number',
          hint: 'MH1234567890123',
          icon: Icons.credit_card,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9]')),
            LengthLimitingTextInputFormatter(15),
            TextInputFormatter.withFunction((oldValue, newValue) {
              return TextEditingValue(
                text: newValue.text.toUpperCase(),
                selection: newValue.selection,
              );
            }),
          ],
          errorText: _errors['driverDL'],
          onChanged: (_) {
            if (_errors['driverDL'] != null) {
              setState(() => _errors.remove('driverDL'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverCabCtrl,
          label: 'Cab Number',
          hint: 'MH12AB1234',
          icon: Icons.directions_car,
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[A-Za-z0-9]')),
            LengthLimitingTextInputFormatter(10),
            TextInputFormatter.withFunction((oldValue, newValue) {
              return TextEditingValue(
                text: newValue.text.toUpperCase().replaceAll(' ', ''),
                selection: newValue.selection,
              );
            }),
          ],
          errorText: _errors['driverCab'],
          onChanged: (_) {
            if (_errors['driverCab'] != null) {
              setState(() => _errors.remove('driverCab'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverCompanySearchCtrl,
          label: 'Search Company',
          hint: 'Search by company, admin, or address',
          icon: Icons.search,
          onChanged: (value) => _applyCompanySearch(
            controller: _driverCompanySearchCtrl,
            isDriver: true,
            errorKey: 'driverCompany',
            value: value,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        DropdownButtonFormField<String>(
          // Warning fix: `value` is deprecated for DropdownButtonFormField; use `initialValue`.
          initialValue: _selectedDriverAdminId,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: 'Company',
            prefixIcon: const Icon(Icons.apartment),
            errorText: _errors['driverCompany'],
          ),
          items: _filterCompanies(_driverCompanySearchCtrl.text)
              .map(
                (company) => DropdownMenuItem<String>(
                  value: company.id,
                  child: Text(
                    company.officeAddress.trim().isEmpty
                        ? company.companyName
                        : '${company.companyName} • ${company.officeAddress}',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              )
              .toList(),
          onChanged: _loadingCompanies
              ? null
              : (value) {
                  setState(() {
                    _selectedDriverAdminId = value;
                    _errors.remove('driverCompany');
                  });
                },
          hint: Text(
            _loadingCompanies
                ? 'Loading companies...'
                : (_filterCompanies(_driverCompanySearchCtrl.text).isEmpty
                    ? 'No matching company found'
                    : 'Select your company'),
          ),
        ),
        if (_findCompanyById(_selectedDriverAdminId) != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                _findCompanyById(_selectedDriverAdminId)!
                        .officeAddress
                        .trim()
                        .isEmpty
                    ? 'Admin: ${_findCompanyById(_selectedDriverAdminId)!.name}'
                    : '${_findCompanyById(_selectedDriverAdminId)!.officeAddress}  |  Admin: ${_findCompanyById(_selectedDriverAdminId)!.name}',
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ),
          ),
        const SizedBox(height: AppSpacing.md),
        // Vehicle Type Dropdown
        Container(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md, vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            color: AppThemeColors.cardGlass,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(
              color: AppThemeColors.border,
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.airline_seat_recline_normal,
                color: AppThemeColors.textSecondary,
                size: AppIconSizes.md,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: DropdownButton<String>(
                  value: _driverVehicleType,
                  isExpanded: true,
                  underline: const SizedBox(),
                  dropdownColor: AppThemeColors.surface,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w500,
                  ),
                  items: const [
                    DropdownMenuItem(value: '4', child: Text('4-Seater')),
                    DropdownMenuItem(value: '6', child: Text('6-Seater')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        _driverVehicleType = value;
                      });
                    }
                  },
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _driverHomeTownCtrl,
          label: 'Home Town / Address',
          hint: 'City, Street...',
          icon: Icons.home,
          errorText: _errors['driverHomeTown'],
          onChanged: (value) {
            if (_errors['driverHomeTown'] != null) {
              setState(() => _errors.remove('driverHomeTown'));
            }
            _onDriverAddressChanged(value);
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: Text(
                'Coordinates: ${_driverCoordLabel()}',
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ),
            OutlinedButton.icon(
              onPressed: _openDriverMapPicker,
              icon: const Icon(Icons.map_outlined, size: 16),
              label: const Text('Pick on Map'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppThemeColors.textPrimary,
                side: const BorderSide(color: AppThemeColors.border),
              ),
            ),
          ],
        ),
        if (_isResolvingDriverAddress || _driverAddressResolveNote != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Row(
              children: [
                if (_isResolvingDriverAddress) ...[
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                ],
                Expanded(
                  child: Text(
                    _isResolvingDriverAddress
                        ? 'Resolving address...'
                        : (_driverAddressResolveNote ?? ''),
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.textTertiary,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildEmployeeLoginFields() {
    return Column(
      children: [
        CustomTextField(
          controller: _employeeMobileCtrl,
          label: 'Mobile Number',
          hint: '10 digits',
          icon: Icons.phone,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          errorText: _errors['employeeMobile'],
          onChanged: (_) {
            if (_errors['employeeMobile'] != null) {
              setState(() => _errors.remove('employeeMobile'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _employeeIdCtrl,
          label: 'Employee ID',
          hint: 'EMP001',
          icon: Icons.badge,
          errorText: _errors['employeeId'],
          onChanged: (_) {
            if (_errors['employeeId'] != null) {
              setState(() => _errors.remove('employeeId'));
            }
          },
        ),
      ],
    );
  }

  Widget _buildEmployeeRegistrationFields() {
    return Column(
      children: [
        CustomTextField(
          controller: _employeeNameCtrl,
          label: 'Employee Name',
          hint: 'Enter your full name',
          icon: Icons.person,
          errorText: _errors['employeeName'],
          onChanged: (_) {
            if (_errors['employeeName'] != null) {
              setState(() => _errors.remove('employeeName'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _employeeMobileCtrl,
          label: 'Mobile Number',
          hint: '10 digits',
          icon: Icons.phone,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          errorText: _errors['employeeMobile'],
          onChanged: (_) {
            if (_errors['employeeMobile'] != null) {
              setState(() => _errors.remove('employeeMobile'));
            }
          },
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _employeeCompanySearchCtrl,
          label: 'Search Company',
          hint: 'Search by company, admin, or address',
          icon: Icons.search,
          onChanged: (value) => _applyCompanySearch(
            controller: _employeeCompanySearchCtrl,
            isDriver: false,
            errorKey: 'employeeCompany',
            value: value,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        DropdownButtonFormField<String>(
          // Warning fix: `value` is deprecated for DropdownButtonFormField; use `initialValue`.
          initialValue: _selectedEmployeeAdminId,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: 'Company',
            prefixIcon: const Icon(Icons.apartment),
            errorText: _errors['employeeCompany'],
          ),
          items: _filterCompanies(_employeeCompanySearchCtrl.text)
              .map(
                (company) => DropdownMenuItem<String>(
                  value: company.id,
                  child: Text(
                    company.officeAddress.trim().isEmpty
                        ? company.companyName
                        : '${company.companyName} • ${company.officeAddress}',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              )
              .toList(),
          onChanged: _loadingCompanies
              ? null
              : (value) {
                  setState(() {
                    _selectedEmployeeAdminId = value;
                    _errors.remove('employeeCompany');
                  });
                },
          hint: Text(
            _loadingCompanies
                ? 'Loading companies...'
                : (_filterCompanies(_employeeCompanySearchCtrl.text).isEmpty
                    ? 'No matching company found'
                    : 'Select your company'),
          ),
        ),
        if (_findCompanyById(_selectedEmployeeAdminId) != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                _findCompanyById(_selectedEmployeeAdminId)!
                        .officeAddress
                        .trim()
                        .isEmpty
                    ? 'Admin: ${_findCompanyById(_selectedEmployeeAdminId)!.name}'
                    : '${_findCompanyById(_selectedEmployeeAdminId)!.officeAddress}  |  Admin: ${_findCompanyById(_selectedEmployeeAdminId)!.name}',
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ),
          ),
        const SizedBox(height: AppSpacing.md),
        GestureDetector(
          onTap: () => _pickTime(_employeeLoginTimeCtrl),
          child: AbsorbPointer(
            child: CustomTextField(
              controller: _employeeLoginTimeCtrl,
              label: 'Login Time',
              hint: 'HH:MM',
              icon: Icons.access_time,
              errorText: _errors['employeeLoginTime'],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        GestureDetector(
          onTap: () => _pickTime(_employeeLogoutTimeCtrl),
          child: AbsorbPointer(
            child: CustomTextField(
              controller: _employeeLogoutTimeCtrl,
              label: 'Logout Time',
              hint: 'HH:MM',
              icon: Icons.access_time,
              errorText: _errors['employeeLogoutTime'],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        CustomTextField(
          controller: _employeeHomeCtrl,
          label: 'Home Location / Address',
          hint: 'City, Area...',
          icon: Icons.home,
          errorText: _errors['employeeHome'],
          onChanged: (value) {
            if (_errors['employeeHome'] != null) {
              setState(() => _errors.remove('employeeHome'));
            }
            _onEmployeeAddressChanged(value);
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: Text(
                'Coordinates: ${_employeeCoordLabel()}',
                style: AppTypography.labelSmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              ),
            ),
            OutlinedButton.icon(
              onPressed: _openEmployeeMapPicker,
              icon: const Icon(Icons.map_outlined, size: 16),
              label: const Text('Pick on Map'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppThemeColors.textPrimary,
                side: const BorderSide(color: AppThemeColors.border),
              ),
            ),
          ],
        ),
        if (_isResolvingEmployeeAddress || _employeeAddressResolveNote != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Row(
              children: [
                if (_isResolvingEmployeeAddress) ...[
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                ],
                Expanded(
                  child: Text(
                    _isResolvingEmployeeAddress
                        ? 'Resolving address...'
                        : (_employeeAddressResolveNote ?? ''),
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.textTertiary,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  String _getRoleLabel() {
    switch (_selectedRole) {
      case role_tab.UserRole.admin:
        return 'Admin';
      case role_tab.UserRole.driver:
        return 'Driver';
      case role_tab.UserRole.employee:
        return 'Employee';
    }
  }

  String _getSubmitButtonLabel() {
    if (_selectedRole == role_tab.UserRole.admin) {
      return 'Login';
    }
    if (_authMode == AuthMode.login) {
      return 'Login';
    }
    return 'Request to Admin';
  }
}
