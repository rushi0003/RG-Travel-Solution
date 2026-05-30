import 'package:flutter/material.dart';

import '../services/admin_service.dart';
import '../theme/ops_ui_tokens.dart';
import 'operations_ui.dart';

class RequestQueueScreen extends StatefulWidget {
  const RequestQueueScreen({super.key});

  @override
  State<RequestQueueScreen> createState() => _RequestQueueScreenState();
}

class _RequestQueueScreenState extends State<RequestQueueScreen> {
  bool _loading = true;
  String? _error;
  Map<String, List<Map<String, dynamic>>> _sections = const {};

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
        AdminService.fetchList('/api/admin/driver-requests'),
        AdminService.fetchList('/api/admin/employee-requests'),
        AdminService.fetchList('/api/admin/driver-change-requests'),
        AdminService.fetchList('/api/admin/employee-change-requests'),
        AdminService.fetchList('/api/admin/absence-requests'),
      ]);
      if (!mounted) return;
      setState(() {
        _sections = {
          'Driver Requests': results[0],
          'Employee Requests': results[1],
          'Driver Changes': results[2],
          'Employee Changes': results[3],
          'Absence Requests': results[4],
        };
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
    final totalPending = _sections.values.fold<int>(
      0,
      (sum, items) => sum + items.length,
    );

    return OpsScaffold(
      title: 'Request Queue',
      subtitle:
          'Track approval-heavy backend workflows across driver, employee, change, and absence requests.',
      icon: Icons.inventory_2_rounded,
      metrics: [
        OpsMetric(
          label: 'Total Pending',
          value: '$totalPending',
          icon: Icons.rule_rounded,
          tone: OpsUiTokens.warning,
        ),
        OpsMetric(
          label: 'Driver Side',
          value:
              '${(_sections['Driver Requests']?.length ?? 0) + (_sections['Driver Changes']?.length ?? 0)}',
          icon: Icons.badge_rounded,
          tone: OpsUiTokens.blue,
        ),
        OpsMetric(
          label: 'Employee Side',
          value:
              '${(_sections['Employee Requests']?.length ?? 0) + (_sections['Employee Changes']?.length ?? 0)}',
          icon: Icons.people_alt_rounded,
          tone: OpsUiTokens.secondary,
        ),
        OpsMetric(
          label: 'Absence Queue',
          value: '${_sections['Absence Requests']?.length ?? 0}',
          icon: Icons.event_busy_rounded,
          tone: OpsUiTokens.danger,
        ),
      ],
      onRefresh: _load,
      child: _loading
          ? const OpsLoadingState(message: 'Loading approval queues...')
          : _error != null
              ? ErrorCard(message: _error!)
              : Column(
                  children: _sections.entries.map((entry) {
                    final tone = switch (entry.key) {
                      'Driver Requests' => OpsUiTokens.blue,
                      'Employee Requests' => OpsUiTokens.secondary,
                      'Driver Changes' => OpsUiTokens.warning,
                      'Employee Changes' => OpsUiTokens.purple,
                      _ => OpsUiTokens.danger,
                    };
                    return Padding(
                      padding: const EdgeInsets.only(bottom: OpsSpacing.lg),
                      child: SectionCard(
                        title: entry.key,
                        description:
                            'Operational items waiting for backend action or approval review.',
                        items: entry.value,
                        tone: tone,
                        subtitleBuilder: (item) =>
                            'Status: ${item['status'] ?? '-'}',
                      ),
                    );
                  }).toList(),
                ),
    );
  }
}
