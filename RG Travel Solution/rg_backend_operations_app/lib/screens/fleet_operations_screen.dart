import 'package:flutter/material.dart';

import '../services/admin_service.dart';
import '../theme/ops_ui_tokens.dart';
import 'operations_ui.dart';

class FleetOperationsScreen extends StatefulWidget {
  const FleetOperationsScreen({super.key});

  @override
  State<FleetOperationsScreen> createState() => _FleetOperationsScreenState();
}

class _FleetOperationsScreenState extends State<FleetOperationsScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _drivers = const [];
  List<Map<String, dynamic>> _employees = const [];
  List<Map<String, dynamic>> _onlineDrivers = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait<List<Map<String, dynamic>>>([
        AdminService.fetchList('/api/admin/drivers'),
        AdminService.fetchList('/api/admin/employees'),
        AdminService.fetchList('/api/admin/drivers/online'),
      ]);
      if (!mounted) return;
      setState(() {
        _drivers = results[0];
        _employees = results[1];
        _onlineDrivers = results[2];
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

  @override
  Widget build(BuildContext context) {
    return OpsScaffold(
      title: 'Fleet and Drivers',
      subtitle:
          'Watch active driver availability, total fleet manpower, and employee coverage from one backend operations view.',
      icon: Icons.local_taxi_rounded,
      metrics: [
        OpsMetric(
          label: 'Online Drivers',
          value: '${_onlineDrivers.length}',
          icon: Icons.location_searching_rounded,
          tone: OpsUiTokens.info,
        ),
        OpsMetric(
          label: 'All Drivers',
          value: '${_drivers.length}',
          icon: Icons.badge_rounded,
          tone: OpsUiTokens.blue,
        ),
        OpsMetric(
          label: 'Employees',
          value: '${_employees.length}',
          icon: Icons.groups_rounded,
          tone: OpsUiTokens.secondary,
        ),
      ],
      onRefresh: _load,
      child: _loading
          ? const OpsLoadingState(message: 'Loading fleet visibility...')
          : _error != null
              ? ErrorCard(message: _error!)
              : Column(
                  children: [
                    SectionCard(
                      title: 'Online Drivers',
                      description:
                          'Drivers currently visible as active or online from the backend operations side.',
                      items: _onlineDrivers,
                      tone: OpsUiTokens.info,
                      subtitleBuilder: (item) =>
                          'Mobile: ${item['mobile'] ?? '-'} | Vehicle: ${item['vehicle_no'] ?? item['cab_no'] ?? '-'}',
                    ),
                    const SizedBox(height: OpsSpacing.lg),
                    SectionCard(
                      title: 'All Drivers',
                      description:
                          'Full driver master list with current mobile and vehicle type information.',
                      items: _drivers,
                      tone: OpsUiTokens.blue,
                      subtitleBuilder: (item) =>
                          'Mobile: ${item['mobile'] ?? '-'} | Vehicle Type: ${item['vehicle_type'] ?? '-'}',
                    ),
                    const SizedBox(height: OpsSpacing.lg),
                    SectionCard(
                      title: 'Employees',
                      description:
                          'Employee roster currently available to the backend operations dashboard.',
                      items: _employees,
                      tone: OpsUiTokens.secondary,
                      subtitleBuilder: (item) =>
                          'Code: ${item['employee_code'] ?? '-'} | Mobile: ${item['mobile'] ?? '-'}',
                    ),
                  ],
                ),
    );
  }
}
