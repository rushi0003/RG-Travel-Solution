import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/models/admin_billing_model.dart';
import 'package:rg_travel_flutter/services/admin_billing_pdf_service.dart';
import 'package:rg_travel_flutter/services/admin_service.dart';

class AdminBillingScreen extends StatefulWidget {
  final String adminId;
  final bool embedded;

  const AdminBillingScreen({
    super.key,
    required this.adminId,
    this.embedded = false,
  });

  @override
  State<AdminBillingScreen> createState() => _AdminBillingScreenState();
}

class _AdminBillingScreenState extends State<AdminBillingScreen> {
  static const String _defaultRgGst = '27RGTSL7842A1Z5';
  static const String _defaultBankName = 'Axis Bank';
  static const String _defaultAccountNo = '918273645001';
  static const String _defaultIfsc = 'UTIB0001234';

  final TextEditingController _companyNameCtrl = TextEditingController();
  final TextEditingController _companyAddressCtrl = TextEditingController();
  final TextEditingController _companyEmailCtrl = TextEditingController();
  final TextEditingController _contactPersonCtrl = TextEditingController();
  final TextEditingController _clientGstCtrl = TextEditingController();
  final TextEditingController _serviceTypeCtrl =
      TextEditingController(text: 'Employee Transportation');
  final TextEditingController _officeAddressCtrl = TextEditingController();
  final TextEditingController _rgGstCtrl = TextEditingController();
  final TextEditingController _employeesCtrl = TextEditingController();
  final TextEditingController _notesCtrl = TextEditingController();
  final TextEditingController _bankNameCtrl = TextEditingController();
  final TextEditingController _accountNoCtrl = TextEditingController();
  final TextEditingController _ifscCtrl = TextEditingController();
  final TextEditingController _upiCtrl =
      TextEditingController(text: 'rgtravelsolution@gmail.com');
  final TextEditingController _perKmCtrl = TextEditingController(text: '0');
  final TextEditingController _advanceCtrl = TextEditingController(text: '0');
  final TextEditingController _gstCtrl = TextEditingController(text: '18');

  BillingMode _mode = BillingMode.dateRange;
  DateTime? _fromDate;
  DateTime? _toDate;
  BillableVehicleAssignment? _selectedAssignment;
  BillableTripSummary? _selectedTrip;

  List<BillableVehicleAssignment> _vehicleAssignments =
      <BillableVehicleAssignment>[];
  List<BillableTripSummary> _availableTrips = <BillableTripSummary>[];
  List<Map<String, dynamic>> _billingHistory = <Map<String, dynamic>>[];

  bool _loadingVehicles = false;
  bool _loadingTrips = false;
  bool _loadingHistory = false;
  bool _loadingProfile = false;
  bool _creatingPdf = false;
  String? _vehicleLoadError;
  String? _tripLoadError;
  String? _profileLoadError;
  String? _pdfStatusMessage;
  int _excludedCancelledTrips = 0;
  double _fetchedTotalKm = 0;
  int _fetchedTotalTrips = 0;

  @override
  void initState() {
    super.initState();
    _companyNameCtrl.addListener(_refresh);
    _companyAddressCtrl.addListener(_refresh);
    _companyEmailCtrl.addListener(_refresh);
    _contactPersonCtrl.addListener(_refresh);
    _clientGstCtrl.addListener(_refresh);
    _serviceTypeCtrl.addListener(_refresh);
    _officeAddressCtrl.addListener(_refresh);
    _rgGstCtrl.addListener(_refresh);
    _employeesCtrl.addListener(_refresh);
    _notesCtrl.addListener(_refresh);
    _bankNameCtrl.addListener(_refresh);
    _accountNoCtrl.addListener(_refresh);
    _ifscCtrl.addListener(_refresh);
    _upiCtrl.addListener(_refresh);
    _perKmCtrl.addListener(_refresh);
    _advanceCtrl.addListener(_refresh);
    _gstCtrl.addListener(_refresh);
    _loadBillingDefaults();
    _loadVehicleAssignments();
    _loadBillingHistory();
  }

  @override
  void dispose() {
    _companyNameCtrl
      ..removeListener(_refresh)
      ..dispose();
    _companyAddressCtrl
      ..removeListener(_refresh)
      ..dispose();
    _companyEmailCtrl
      ..removeListener(_refresh)
      ..dispose();
    _contactPersonCtrl
      ..removeListener(_refresh)
      ..dispose();
    _clientGstCtrl
      ..removeListener(_refresh)
      ..dispose();
    _serviceTypeCtrl
      ..removeListener(_refresh)
      ..dispose();
    _officeAddressCtrl
      ..removeListener(_refresh)
      ..dispose();
    _rgGstCtrl
      ..removeListener(_refresh)
      ..dispose();
    _employeesCtrl
      ..removeListener(_refresh)
      ..dispose();
    _notesCtrl
      ..removeListener(_refresh)
      ..dispose();
    _bankNameCtrl
      ..removeListener(_refresh)
      ..dispose();
    _accountNoCtrl
      ..removeListener(_refresh)
      ..dispose();
    _ifscCtrl
      ..removeListener(_refresh)
      ..dispose();
    _upiCtrl
      ..removeListener(_refresh)
      ..dispose();
    _perKmCtrl
      ..removeListener(_refresh)
      ..dispose();
    _advanceCtrl
      ..removeListener(_refresh)
      ..dispose();
    _gstCtrl
      ..removeListener(_refresh)
      ..dispose();
    super.dispose();
  }

  void _refresh() {
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  void _safeSetState(VoidCallback fn) {
    if (!mounted) {
      return;
    }
    setState(fn);
  }

  double _parseAmount(String value) {
    return double.tryParse(value.trim()) ?? 0;
  }

  String _stringValue(dynamic value) {
    return (value ?? '').toString().trim();
  }

  void _setIfEmpty(TextEditingController controller, String value) {
    final normalized = value.trim();
    if (controller.text.trim().isEmpty && normalized.isNotEmpty) {
      controller.text = normalized;
    }
  }

  String? _yyyyMmDd(DateTime? value) {
    if (value == null) {
      return null;
    }
    return DateFormat('yyyy-MM-dd').format(value);
  }

  List<BillableTripSummary> get _selectedTrips {
    if (_mode == BillingMode.specificTrip) {
      if (_selectedTrip == null) {
        return const <BillableTripSummary>[];
      }
      return <BillableTripSummary>[_selectedTrip!];
    }
    return _availableTrips;
  }

  BillingDraft get _draft {
    return BillingDraft(
      assignment: _selectedAssignment,
      mode: _mode,
      fromDate: _fromDate,
      toDate: _toDate,
      trips: _selectedTrips,
      companyName: _companyNameCtrl.text.trim(),
      companyAddress: _companyAddressCtrl.text.trim(),
      companyEmail: _companyEmailCtrl.text.trim(),
      contactPerson: _contactPersonCtrl.text.trim(),
      clientGstNo: _clientGstCtrl.text.trim(),
      serviceType: _serviceTypeCtrl.text.trim(),
      officeAddress: _officeAddressCtrl.text.trim(),
      rgGstNo: _rgGstCtrl.text.trim(),
      totalEmployees: _employeesCtrl.text.trim(),
      notes: _notesCtrl.text.trim(),
      bankName: _bankNameCtrl.text.trim(),
      accountNumber: _accountNoCtrl.text.trim(),
      ifscCode: _ifscCtrl.text.trim(),
      upiId: _upiCtrl.text.trim(),
      perKmAmount: _parseAmount(_perKmCtrl.text),
      advancePaid: _parseAmount(_advanceCtrl.text),
      gstPercent: _parseAmount(_gstCtrl.text),
    );
  }

  Future<void> _loadBillingDefaults() async {
    _safeSetState(() {
      _loadingProfile = true;
      _profileLoadError = null;
    });

    try {
      final data = await AdminService.getBillingPrefill();
      final profile = (data['admin_profile'] is Map)
          ? (data['admin_profile'] as Map).cast<String, dynamic>()
          : <String, dynamic>{};
      final prefill = (data['prefill'] is Map)
          ? (data['prefill'] as Map).cast<String, dynamic>()
          : <String, dynamic>{};
      final companyName = _stringValue(prefill['company_name']).isNotEmpty
          ? _stringValue(prefill['company_name'])
          : (_stringValue(profile['office_name']).isNotEmpty
              ? _stringValue(profile['office_name'])
              : _stringValue(profile['name']));
      final companyAddress = _stringValue(prefill['company_address']).isNotEmpty
          ? _stringValue(prefill['company_address'])
          : (_stringValue(profile['office_address']).isNotEmpty
              ? _stringValue(profile['office_address'])
              : _stringValue(profile['office_location']));

      _safeSetState(() {
        _setIfEmpty(_companyNameCtrl, companyName);
        _setIfEmpty(_companyAddressCtrl, companyAddress);
        _setIfEmpty(_companyEmailCtrl, _stringValue(prefill['company_email']));
        _setIfEmpty(
            _contactPersonCtrl, _stringValue(prefill['contact_person']));
        _setIfEmpty(_clientGstCtrl, _stringValue(prefill['client_gst_no']));
        _setIfEmpty(
          _serviceTypeCtrl,
          _stringValue(prefill['service_type']).isNotEmpty
              ? _stringValue(prefill['service_type'])
              : 'Employee Transportation',
        );
        _setIfEmpty(
          _officeAddressCtrl,
          _stringValue(prefill['office_address']).isNotEmpty
              ? _stringValue(prefill['office_address'])
              : companyAddress,
        );
        _setIfEmpty(
          _rgGstCtrl,
          _stringValue(prefill['rg_gst_no']).isNotEmpty
              ? _stringValue(prefill['rg_gst_no'])
              : _defaultRgGst,
        );
        _setIfEmpty(_employeesCtrl, _stringValue(prefill['total_employees']));
        _setIfEmpty(_notesCtrl, _stringValue(prefill['notes']));
        _setIfEmpty(
          _bankNameCtrl,
          _stringValue(prefill['bank_name']).isNotEmpty
              ? _stringValue(prefill['bank_name'])
              : _defaultBankName,
        );
        _setIfEmpty(
          _accountNoCtrl,
          _stringValue(prefill['account_number']).isNotEmpty
              ? _stringValue(prefill['account_number'])
              : _defaultAccountNo,
        );
        _setIfEmpty(
          _ifscCtrl,
          _stringValue(prefill['ifsc_code']).isNotEmpty
              ? _stringValue(prefill['ifsc_code'])
              : _defaultIfsc,
        );
        _setIfEmpty(_upiCtrl, _stringValue(prefill['upi_id']));
      });
    } catch (e) {
      _safeSetState(() {
        _profileLoadError = 'Company profile auto-fill unavailable: $e';
        _setIfEmpty(_rgGstCtrl, _defaultRgGst);
        _setIfEmpty(_bankNameCtrl, _defaultBankName);
        _setIfEmpty(_accountNoCtrl, _defaultAccountNo);
        _setIfEmpty(_ifscCtrl, _defaultIfsc);
      });
    } finally {
      _safeSetState(() {
        _loadingProfile = false;
      });
    }
  }

  void _applyAssignmentDefaults(BillableVehicleAssignment? value) {
    if (value == null) {
      return;
    }
    _setIfEmpty(_contactPersonCtrl, value.driverName);
  }

  void _applyTripDefaults() {
    if (_selectedTrips.isEmpty) {
      return;
    }
    if (_employeesCtrl.text.trim().isEmpty) {
      _employeesCtrl.text = _draft.calculatedEmployees.toString();
    }
    if (_contactPersonCtrl.text.trim().isEmpty) {
      _contactPersonCtrl.text = _selectedTrips.first.driverName;
    }
  }

  Future<void> _loadVehicleAssignments() async {
    _safeSetState(() {
      _loadingVehicles = true;
      _vehicleLoadError = null;
    });

    try {
      final raw = await AdminService.getBillingVehicleAssignments();
      final assignments = raw
          .map(BillableVehicleAssignment.fromJson)
          .where(
            (item) =>
                item.driverId.trim().isNotEmpty &&
                item.vehicleNo.trim().isNotEmpty,
          )
          .toList();

      _safeSetState(() {
        _vehicleAssignments = assignments;
        if (_selectedAssignment != null) {
          BillableVehicleAssignment? match;
          for (final item in assignments) {
            if (item.driverId == _selectedAssignment!.driverId &&
                item.vehicleNo == _selectedAssignment!.vehicleNo) {
              match = item;
              break;
            }
          }
          _selectedAssignment = match;
        }
      });
    } catch (e) {
      _safeSetState(() {
        _vehicleLoadError = 'Vehicle list load failed: $e';
      });
    } finally {
      _safeSetState(() {
        _loadingVehicles = false;
      });
    }
  }

  Future<void> _loadBillingHistory() async {
    _safeSetState(() {
      _loadingHistory = true;
    });
    try {
      final history = await AdminService.getBillingRecords(limit: 5);
      _safeSetState(() {
        _billingHistory = history;
      });
    } catch (_) {
      _safeSetState(() {
        _billingHistory = <Map<String, dynamic>>[];
      });
    } finally {
      _safeSetState(() {
        _loadingHistory = false;
      });
    }
  }

  Future<void> _loadTrips() async {
    if (_selectedAssignment == null) {
      _safeSetState(() {
        _availableTrips = <BillableTripSummary>[];
        _selectedTrip = null;
        _tripLoadError = null;
        _excludedCancelledTrips = 0;
        _fetchedTotalKm = 0;
        _fetchedTotalTrips = 0;
      });
      return;
    }

    _safeSetState(() {
      _loadingTrips = true;
      _tripLoadError = null;
    });

    try {
      final data = await AdminService.getBillingTrips(
        driverId: _selectedAssignment!.driverId,
        vehicleNo: _selectedAssignment!.vehicleNo,
        fromDate: _yyyyMmDd(_fromDate),
        toDate: _yyyyMmDd(_toDate),
        tripId:
            _mode == BillingMode.specificTrip ? _selectedTrip?.tripId : null,
      );

      final trips = ((data['trips'] as List?) ?? const <dynamic>[])
          // Warning fix: make the map type explicit to satisfy strict raw-type rules.
          .whereType<Map<dynamic, dynamic>>()
          .map((item) =>
              BillableTripSummary.fromJson(item.cast<String, dynamic>()))
          .toList();
      final summary = (data['summary'] is Map<dynamic, dynamic>)
          ? (data['summary'] as Map<dynamic, dynamic>).cast<String, dynamic>()
          : <String, dynamic>{};

      BillableTripSummary? selectedTrip = _selectedTrip;
      if (_mode == BillingMode.specificTrip) {
        if (selectedTrip != null) {
          final matches =
              trips.where((trip) => trip.tripId == selectedTrip!.tripId);
          selectedTrip = matches.isEmpty ? null : matches.first;
        }
      } else {
        selectedTrip = null;
      }

      _safeSetState(() {
        _availableTrips = trips;
        _selectedTrip = selectedTrip;
        _excludedCancelledTrips = _toInt(summary['excluded_cancelled_trips']);
        _fetchedTotalKm = _toDouble(summary['total_km']);
        _fetchedTotalTrips = _toInt(summary['total_trips']);
      });
      _applyTripDefaults();
    } catch (e) {
      _safeSetState(() {
        _availableTrips = <BillableTripSummary>[];
        _selectedTrip = null;
        _tripLoadError = 'Trip data load failed: $e';
        _excludedCancelledTrips = 0;
        _fetchedTotalKm = 0;
        _fetchedTotalTrips = 0;
      });
    } finally {
      _safeSetState(() {
        _loadingTrips = false;
      });
    }
  }

  int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  double _toDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  Future<void> _pickDate({required bool isFrom}) async {
    final now = DateTime.now();
    final initialDate =
        isFrom ? (_fromDate ?? _toDate ?? now) : (_toDate ?? _fromDate ?? now);
    final picked = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 2),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context),
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
    if (picked == null) {
      return;
    }

    _safeSetState(() {
      if (isFrom) {
        _fromDate = picked;
        if (_toDate != null && _toDate!.isBefore(picked)) {
          _toDate = picked;
        }
      } else {
        _toDate = picked;
        if (_fromDate != null && _fromDate!.isAfter(picked)) {
          _fromDate = picked;
        }
      }
    });
    await _loadTrips();
  }

  Future<void> _selectAssignment(BillableVehicleAssignment? value) async {
    _safeSetState(() {
      _selectedAssignment = value;
      _selectedTrip = null;
    });
    _applyAssignmentDefaults(value);
    await _loadTrips();
  }

  Future<void> _changeMode(BillingMode value) async {
    _safeSetState(() {
      _mode = value;
      _selectedTrip = null;
    });
    await _loadTrips();
  }

  Future<void> _selectSpecificTrip(BillableTripSummary? value) async {
    _safeSetState(() {
      _selectedTrip = value;
    });
    if (value == null) {
      await _loadTrips();
    }
  }

  void _reset() {
    _safeSetState(() {
      _mode = BillingMode.dateRange;
      _fromDate = null;
      _toDate = null;
      _selectedAssignment = null;
      _selectedTrip = null;
      _availableTrips = <BillableTripSummary>[];
      _tripLoadError = null;
      _excludedCancelledTrips = 0;
      _fetchedTotalKm = 0;
      _fetchedTotalTrips = 0;
      _companyNameCtrl.clear();
      _companyAddressCtrl.clear();
      _companyEmailCtrl.clear();
      _contactPersonCtrl.clear();
      _clientGstCtrl.clear();
      _serviceTypeCtrl.text = 'Employee Transportation';
      _officeAddressCtrl.clear();
      _rgGstCtrl.text = _defaultRgGst;
      _employeesCtrl.clear();
      _notesCtrl.clear();
      _bankNameCtrl.text = _defaultBankName;
      _accountNoCtrl.text = _defaultAccountNo;
      _ifscCtrl.text = _defaultIfsc;
      _upiCtrl.text = 'rgtravelsolution@gmail.com';
      _perKmCtrl.text = '0';
      _advanceCtrl.text = '0';
      _gstCtrl.text = '18';
    });
    _loadBillingDefaults();
  }

  String _formatCurrency(double amount) {
    return NumberFormat.currency(
      locale: 'en_IN',
      symbol: 'Rs. ',
      decimalDigits: 2,
    ).format(amount);
  }

  String get _tripScopeHint {
    if (_selectedAssignment == null) {
      return 'Select vehicle and driver first.';
    }
    if (_loadingTrips) {
      return 'Loading billable trips...';
    }
    if (_tripLoadError != null) {
      return _tripLoadError!;
    }
    if (_mode == BillingMode.specificTrip && _availableTrips.isEmpty) {
      return 'No completed trips found for this vehicle-driver pair.';
    }
    if (_mode == BillingMode.specificTrip && _selectedTrip == null) {
      return 'Select one completed trip for individual billing.';
    }
    return 'Completed trips are included. Cancelled trips stay excluded automatically.';
  }

  bool get _canCreateBill {
    return !_creatingPdf &&
        _selectedAssignment != null &&
        _draft.includedTrips.isNotEmpty &&
        _draft.perKmAmount > 0;
  }

  Future<void> _createBillPdf() async {
    if (_selectedAssignment == null) {
      _showSnackBar('Select vehicle and driver first.');
      return;
    }
    if (_draft.includedTrips.isEmpty) {
      _showSnackBar('No completed trips available for billing.');
      return;
    }
    if (_draft.perKmAmount <= 0) {
      _showSnackBar('Per KM amount must be greater than zero.');
      return;
    }

    _safeSetState(() {
      _creatingPdf = true;
      _pdfStatusMessage = null;
    });

    try {
      final result = await AdminBillingPdfService.createAndSavePdf(
        draft: _draft,
      );
      try {
        await AdminService.updateBillingSettings(
          payload: <String, dynamic>{
            'service_type': _draft.serviceType,
            'rg_gst_no': _draft.rgGstNo,
            'bank_name': _draft.bankName,
            'account_number': _draft.accountNumber,
            'ifsc_code': _draft.ifscCode,
            'upi_id': _draft.upiId,
          },
        );
      } catch (_) {}
      await AdminService.createBillingRecord(
        payload: <String, dynamic>{
          'invoice_meta': <String, dynamic>{
            'company_name': _draft.companyName,
            'company_address': _draft.companyAddress,
            'company_email': _draft.companyEmail,
            'contact_person': _draft.contactPerson,
            'client_gst_no': _draft.clientGstNo,
            'service_type': _draft.serviceType,
            'office_address': _draft.officeAddress,
            'rg_gst_no': _draft.rgGstNo,
            'total_employees': _draft.totalEmployees,
            'notes': _draft.notes,
            'bank_name': _draft.bankName,
            'account_number': _draft.accountNumber,
            'ifsc_code': _draft.ifscCode,
            'upi_id': _draft.upiId,
          },
          'assignment': <String, dynamic>{
            'driver_id': _selectedAssignment!.driverId,
            'driver_name': _selectedAssignment!.driverName,
            'vehicle_no': _selectedAssignment!.vehicleNo,
            'vehicle_type': _selectedAssignment!.vehicleType,
          },
          'billing_mode': _draft.mode.name,
          'from_date': _yyyyMmDd(_fromDate),
          'to_date': _yyyyMmDd(_toDate),
          'selected_trip_id': _selectedTrip?.tripId,
          'trips': _draft.includedTrips
              .map(
                (trip) => <String, dynamic>{
                  'trip_id': trip.tripId,
                  'route_no': trip.routeNo,
                  'trip_date': trip.tripDate,
                  'schedule_time': trip.scheduleTime,
                  'driver_id': trip.driverId,
                  'driver_name': trip.driverName,
                  'vehicle_no': trip.vehicleNo,
                  'status': trip.status,
                  'total_km': trip.totalKm,
                },
              )
              .toList(),
          'total_trips': _draft.totalTrips,
          'excluded_cancelled_trips': _excludedCancelledTrips,
          'total_km': _draft.totalKm,
          'per_km_amount': _draft.perKmAmount,
          'advance_paid': _draft.advancePaid,
          'gst_percent': _draft.gstPercent,
          'calculation': <String, dynamic>{
            'subtotal': _draft.calculation.subtotal,
            'gst_amount': _draft.calculation.gstAmount,
            'grand_total': _draft.calculation.grandTotal,
            'payable_amount': _draft.calculation.payableAmount,
          },
          'pdf': <String, dynamic>{
            'file_name': result.fileName,
            'saved_path': result.savedPath,
          },
        },
      );
      await _loadBillingHistory();

      final message = result.savedToDownloads
          ? 'Billing PDF saved to Downloads: ${result.fileName}'
          : 'Billing PDF saved and history stored: ${result.savedPath ?? result.fileName}';
      _safeSetState(() {
        _pdfStatusMessage = message;
      });
      _showSnackBar(message);
    } catch (e) {
      final message = 'Billing PDF create failed: $e';
      _safeSetState(() {
        _pdfStatusMessage = message;
      });
      _showSnackBar(message);
    } finally {
      _safeSetState(() {
        _creatingPdf = false;
      });
    }
  }

  void _showSnackBar(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final calculation = _draft.calculation;
    final width = MediaQuery.of(context).size.width;
    final showSplitLayout = width >= 1080;
    final content = ListView(
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        _headerCard(),
        const SizedBox(height: AppSpacing.md),
        if (showSplitLayout)
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 7,
                child: Column(
                  children: [
                    _workspaceCard(),
                    const SizedBox(height: AppSpacing.md),
                    _tripPreviewCard(),
                  ],
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                flex: 5,
                child: Column(
                  children: [
                    _summaryCard(calculation),
                    const SizedBox(height: AppSpacing.md),
                    _historyCard(),
                  ],
                ),
              ),
            ],
          )
        else ...[
          _workspaceCard(),
          const SizedBox(height: AppSpacing.md),
          _summaryCard(calculation),
          const SizedBox(height: AppSpacing.md),
          _tripPreviewCard(),
          const SizedBox(height: AppSpacing.md),
          _historyCard(),
        ],
      ],
    );

    if (widget.embedded) {
      return Container(
        decoration: const BoxDecoration(
          gradient: AppGradients.backgroundGradient,
        ),
        child: content,
      );
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Billing'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: content,
    );
  }

  Widget _headerCard() {
    return _card(
      title: 'Billing Workspace',
      trailing: IconButton(
        onPressed: _loadingVehicles || _loadingTrips
            ? null
            : () async {
                await _loadVehicleAssignments();
                await _loadTrips();
                await _loadBillingHistory();
              },
        icon: const Icon(Icons.refresh, color: AppThemeColors.textPrimary),
        tooltip: 'Refresh',
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Create vehicle and driver bills in one continuous flow with live trip aggregation, GST calculation, PDF export, and saved history.',
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              _infoPill(
                icon: Icons.route_outlined,
                label: '${_fetchedTotalTrips} billable trips',
              ),
              _infoPill(
                icon: Icons.straighten_outlined,
                label: '${_draft.totalKm.toStringAsFixed(2)} KM selected',
              ),
              _infoPill(
                icon: Icons.block_outlined,
                label: 'Cancelled excluded: $_excludedCancelledTrips',
                color: AppThemeColors.warning,
              ),
              _infoPill(
                icon: Icons.picture_as_pdf_outlined,
                label: _creatingPdf ? 'Preparing PDF' : 'PDF export ready',
                color: AppThemeColors.success,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _workspaceCard() {
    return _card(
      title: 'Billing Details',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppSpacing.md,
            runSpacing: AppSpacing.md,
            alignment: WrapAlignment.spaceBetween,
            children: [
              _metricTile(
                'Payable',
                _formatCurrency(_draft.calculation.payableAmount),
                AppThemeColors.success,
              ),
              _metricTile(
                'Trips',
                _draft.totalTrips.toString(),
                AppThemeColors.primary,
              ),
              _metricTile(
                'GST',
                '${_parseAmount(_gstCtrl.text).toStringAsFixed(0)}%',
                AppThemeColors.info,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          _sectionLabel('Vehicle and driver'),
          DropdownButtonFormField<BillableVehicleAssignment>(
            // Warning fix: `value` is deprecated; `initialValue` preserves the same initial selection.
            initialValue: _selectedAssignment,
            isExpanded: true,
            items: _vehicleAssignments
                .map(
                  (assignment) => DropdownMenuItem<BillableVehicleAssignment>(
                    value: assignment,
                    child: Text(
                      assignment.label,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                )
                .toList(),
            onChanged: _loadingVehicles
                ? null
                : (value) {
                    _selectAssignment(value);
                  },
            decoration: _inputDecoration(
              _loadingVehicles
                  ? 'Loading vehicle-driver list'
                  : 'Select vehicle and driver',
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          if (_loadingVehicles) const LinearProgressIndicator(minHeight: 3),
          if (_vehicleLoadError != null)
            _messageText(_vehicleLoadError!, isError: true)
          else
            Text(
              _selectedAssignment?.label ??
                  (_vehicleAssignments.isEmpty
                      ? 'No billable vehicle-driver pairs available yet.'
                      : 'Select a mapped vehicle-driver pair to load billable trips.'),
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          const SizedBox(height: AppSpacing.lg),
          _sectionLabel('Invoice details'),
          _invoiceDetailsCard(),
          const SizedBox(height: AppSpacing.lg),
          _sectionLabel('Billing scope'),
          _billingRangeCard(),
          const SizedBox(height: AppSpacing.lg),
          _sectionLabel('Charges and export'),
          _pricingCard(),
          const SizedBox(height: AppSpacing.lg),
          _pdfCard(),
        ],
      ),
    );
  }

  Widget _billingRangeCard() {
    final isRange = _mode == BillingMode.dateRange;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: [
            ChoiceChip(
              label: const Text('Date range'),
              selected: isRange,
              onSelected: (_) {
                _changeMode(BillingMode.dateRange);
              },
            ),
            ChoiceChip(
              label: const Text('Specific trip'),
              selected: !isRange,
              onSelected: (_) {
                _changeMode(BillingMode.specificTrip);
              },
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pickDate(isFrom: true),
                icon: const Icon(Icons.date_range),
                label: Text(
                  _fromDate == null
                      ? 'From date'
                      : DateFormat('dd MMM yyyy').format(_fromDate!),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pickDate(isFrom: false),
                icon: const Icon(Icons.event),
                label: Text(
                  _toDate == null
                      ? 'To date'
                      : DateFormat('dd MMM yyyy').format(_toDate!),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpacing.md),
          decoration: BoxDecoration(
            color: AppThemeColors.cardGlass,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppThemeColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isRange
                    ? 'Range: ${_draft.rangeLabel}'
                    : 'Single completed trip billing mode is active.',
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textPrimary,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                _tripScopeHint,
                style: AppTypography.bodySmall.copyWith(
                  color: _tripLoadError != null
                      ? AppThemeColors.error
                      : AppThemeColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        if (!isRange) ...[
          const SizedBox(height: AppSpacing.md),
          DropdownButtonFormField<BillableTripSummary>(
            // Warning fix: `value` is deprecated; `initialValue` preserves the same initial selection.
            initialValue: _selectedTrip,
            isExpanded: true,
            items: _availableTrips
                .map(
                  (trip) => DropdownMenuItem<BillableTripSummary>(
                    value: trip,
                    child: Text(
                      '${trip.routeNo} | ${trip.tripDate} | ${trip.totalKm.toStringAsFixed(2)} KM',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                )
                .toList(),
            onChanged: _loadingTrips
                ? null
                : (value) {
                    _selectSpecificTrip(value);
                  },
            decoration: _inputDecoration('Select one completed trip'),
          ),
        ],
      ],
    );
  }

  Widget _invoiceDetailsCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _loadingProfile
                ? 'Loading company details from backend...'
                : (_profileLoadError ??
                    'Company, driver, and employee details are auto-filled from backend when available. You can still edit GST, bank, and invoice fields.'),
            style: AppTypography.bodySmall.copyWith(
              color: _profileLoadError != null
                  ? AppThemeColors.warning
                  : AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _companyNameCtrl,
                  decoration: _inputDecoration('Company / Client name'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextFormField(
                  controller: _companyEmailCtrl,
                  decoration: _inputDecoration('Company email'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextFormField(
                  controller: _contactPersonCtrl,
                  decoration: _inputDecoration('Contact person'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            controller: _companyAddressCtrl,
            maxLines: 2,
            decoration: _inputDecoration('Client address'),
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _clientGstCtrl,
                  decoration: _inputDecoration('Client GST No'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextFormField(
                  controller: _employeesCtrl,
                  keyboardType: TextInputType.number,
                  decoration: _inputDecoration('Total employees'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _serviceTypeCtrl,
                  decoration: _inputDecoration('Service type'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextFormField(
                  controller: _officeAddressCtrl,
                  decoration: _inputDecoration('RG office address'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _rgGstCtrl,
                  decoration: _inputDecoration('RG GST No'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextFormField(
                  controller: _upiCtrl,
                  decoration: _inputDecoration('UPI ID'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _bankNameCtrl,
                  decoration: _inputDecoration('Bank name'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _accountNoCtrl,
                  decoration: _inputDecoration('Account number'),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: TextFormField(
                  controller: _ifscCtrl,
                  decoration: _inputDecoration('IFSC code'),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            controller: _notesCtrl,
            maxLines: 3,
            decoration: _inputDecoration('Notes / remarks'),
          ),
        ],
      ),
    );
  }

  Widget _pricingCard() {
    return Column(
      children: [
        TextFormField(
          controller: _perKmCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: _inputDecoration('Per KM amount'),
        ),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          controller: _advanceCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: _inputDecoration('Advance paid'),
        ),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          controller: _gstCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: _inputDecoration('GST %'),
        ),
      ],
    );
  }

  Widget _tripPreviewCard() {
    return _card(
      title: 'Trip Preview',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_loadingTrips) const LinearProgressIndicator(minHeight: 3),
          if (_tripLoadError != null) ...[
            const SizedBox(height: AppSpacing.sm),
            _messageText(_tripLoadError!, isError: true),
          ],
          if (!_loadingTrips && _tripLoadError == null) ...[
            _summaryRow(
                'Fetched completed trips', _fetchedTotalTrips.toString()),
            _summaryRow(
              'Fetched completed KM',
              _fetchedTotalKm.toStringAsFixed(2),
            ),
            _summaryRow(
              'Excluded cancelled trips',
              _excludedCancelledTrips.toString(),
            ),
            const SizedBox(height: AppSpacing.sm),
            if (_selectedTrips.isEmpty)
              Text(
                'No trips selected for billing yet.',
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.textSecondary,
                ),
              )
            else
              ..._selectedTrips.take(6).map(_tripTile),
          ],
        ],
      ),
    );
  }

  Widget _pdfCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlassActive,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Create billing PDF and save it to device Downloads when available.',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _canCreateBill ? _createBillPdf : null,
              icon: _creatingPdf
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.picture_as_pdf),
              label: Text(_creatingPdf ? 'Creating PDF...' : 'Create Bill PDF'),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            _pdfStatusMessage ??
                'PDF file name will include vehicle number and timestamp.',
            style: AppTypography.bodySmall.copyWith(
              color: _pdfStatusMessage == null
                  ? AppThemeColors.textSecondary
                  : AppThemeColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _historyCard() {
    return _card(
      title: 'Recent Billing History',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_loadingHistory) const LinearProgressIndicator(minHeight: 3),
          if (!_loadingHistory && _billingHistory.isEmpty)
            Text(
              'No persisted billing records yet.',
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            )
          else
            ..._billingHistory.map(_historyTile),
        ],
      ),
    );
  }

  Widget _historyTile(Map<String, dynamic> item) {
    final createdAt = (item['created_at'] ?? '').toString();
    final vehicleNo = (item['vehicle_no'] ?? '').toString();
    final driverName = (item['driver_name'] ?? '').toString();
    final payableAmount = _toDouble(item['payable_amount']);
    final totalTrips = _toInt(item['total_trips']);
    final pdfFileName = (item['pdf_file_name'] ?? '').toString();

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '$vehicleNo | $driverName',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Text(
                _formatCurrency(payableAmount),
                style: AppTypography.bodySmall.copyWith(
                  color: AppThemeColors.success,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Trips: $totalTrips | PDF: $pdfFileName',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          if (createdAt.isNotEmpty)
            Text(
              'Created: $createdAt',
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
        ],
      ),
    );
  }

  Widget _tripTile(BillableTripSummary trip) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  trip.routeNo,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '${trip.tripDate} | ${trip.scheduleTime} | ${trip.vehicleNo}',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Text(
            '${trip.totalKm.toStringAsFixed(2)} KM',
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.success,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryCard(BillingCalculation calculation) {
    return _card(
      title: 'Billing Summary',
      trailing: Wrap(
        spacing: AppSpacing.sm,
        children: [
          OutlinedButton(
            onPressed: _reset,
            child: const Text('Reset'),
          ),
          FilledButton(
            onPressed: _canCreateBill ? _createBillPdf : null,
            child: const Text('Create Bill'),
          ),
        ],
      ),
      child: Column(
        children: [
          _summaryRow(
            'Billing mode',
            _draft.mode == BillingMode.dateRange
                ? 'Date range'
                : 'Specific trip',
          ),
          _summaryRow(
            'Vehicle-driver',
            _selectedAssignment?.label ?? 'Not selected',
          ),
          _summaryRow(
            'Client',
            _draft.companyName.isEmpty ? 'Not entered' : _draft.companyName,
          ),
          _summaryRow('Duration', _draft.rangeLabel),
          _summaryRow('Included trips', _draft.totalTrips.toString()),
          _summaryRow('Total KM', _draft.totalKm.toStringAsFixed(2)),
          _summaryRow('Subtotal', _formatCurrency(calculation.subtotal)),
          _summaryRow(
            'GST (${calculation.gstPercent.toStringAsFixed(2)}%)',
            _formatCurrency(calculation.gstAmount),
          ),
          _summaryRow('Grand total', _formatCurrency(calculation.grandTotal)),
          _summaryRow('Advance paid', _formatCurrency(calculation.advancePaid)),
          const Divider(color: AppThemeColors.border),
          _summaryRow(
            'Final payable',
            _formatCurrency(calculation.payableAmount),
            emphasize: true,
          ),
          const SizedBox(height: AppSpacing.sm),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Create Bill generates a PDF and saves it to Downloads when the device path is available.',
              style: AppTypography.bodySmall.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionLabel(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Text(
        title,
        style: AppTypography.bodyMedium.copyWith(
          color: AppThemeColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _infoPill({
    required IconData icon,
    required String label,
    Color color = AppThemeColors.primary,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppRadius.full),
        // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: AppSpacing.xs),
          Text(
            label,
            style: AppTypography.labelMedium.copyWith(color: color),
          ),
        ],
      ),
    );
  }

  Widget _metricTile(String label, String value, Color accent) {
    return Container(
      width: 170,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.md),
        // Warning fix: replace deprecated withOpacity with withValues without changing alpha.
        border: Border.all(color: accent.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: AppThemeColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            value,
            style: AppTypography.titleMedium.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value, {bool emphasize = false}) {
    final style = emphasize
        ? AppTypography.bodyMedium.copyWith(
            color: AppThemeColors.textPrimary,
            fontWeight: FontWeight.w800,
          )
        : AppTypography.bodySmall.copyWith(
            color: AppThemeColors.textSecondary,
          );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(child: Text(label, style: style)),
          const SizedBox(width: AppSpacing.sm),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: emphasize
                  ? AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.success,
                      fontWeight: FontWeight.w800,
                    )
                  : AppTypography.bodySmall.copyWith(
                      color: AppThemeColors.textPrimary,
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _messageText(String text, {required bool isError}) {
    return Text(
      text,
      style: AppTypography.bodySmall.copyWith(
        color: isError ? AppThemeColors.error : AppThemeColors.textSecondary,
      ),
    );
  }

  InputDecoration _inputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      filled: true,
      fillColor: AppThemeColors.cardGlass,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppThemeColors.border),
      ),
    );
  }

  Widget _card({
    required String title,
    Widget? trailing,
    required Widget child,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              if (trailing != null) trailing,
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          child,
        ],
      ),
    );
  }
}
