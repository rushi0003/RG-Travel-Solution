import 'package:flutter/material.dart';

import '../services/admin_service.dart';
import '../theme/ops_ui_tokens.dart';
import 'operations_ui.dart';

class SupportOperationsScreen extends StatefulWidget {
  const SupportOperationsScreen({super.key});

  @override
  State<SupportOperationsScreen> createState() =>
      _SupportOperationsScreenState();
}

class _SupportOperationsScreenState extends State<SupportOperationsScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _sos = const [];
  List<Map<String, dynamic>> _helpdesk = const [];

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
        AdminService.fetchList('/api/admin/sos-alerts'),
        AdminService.fetchList('/api/admin/helpdesk'),
      ]);
      if (!mounted) return;
      setState(() {
        _sos = results[0];
        _helpdesk = results[1];
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
      title: 'Safety and Support',
      subtitle:
          'Review emergency escalation signals and helpdesk demand from the same backend response workspace.',
      icon: Icons.support_agent_rounded,
      metrics: [
        OpsMetric(
          label: 'SOS Alerts',
          value: '${_sos.length}',
          icon: Icons.warning_amber_rounded,
          tone: OpsUiTokens.danger,
        ),
        OpsMetric(
          label: 'Helpdesk Tickets',
          value: '${_helpdesk.length}',
          icon: Icons.support_agent_rounded,
          tone: OpsUiTokens.secondary,
        ),
      ],
      onRefresh: _load,
      child: _loading
          ? const OpsLoadingState(message: 'Loading safety and support...')
          : _error != null
              ? ErrorCard(message: _error!)
              : Column(
                  children: [
                    SectionCard(
                      title: 'SOS Alerts',
                      description:
                          'Emergency or distress alerts raised from trips that may need immediate attention.',
                      items: _sos,
                      tone: OpsUiTokens.danger,
                      subtitleBuilder: (item) =>
                          'Trip: ${item['trip_id'] ?? '-'} | Employee: ${item['employee_name'] ?? '-'}',
                    ),
                    const SizedBox(height: OpsSpacing.lg),
                    SectionCard(
                      title: 'Helpdesk Tickets',
                      description:
                          'Support tickets currently visible to the backend helpdesk and operations teams.',
                      items: _helpdesk,
                      tone: OpsUiTokens.secondary,
                      subtitleBuilder: (item) =>
                          'Status: ${item['status'] ?? '-'} | Subject: ${item['subject'] ?? '-'}',
                    ),
                  ],
                ),
    );
  }
}
