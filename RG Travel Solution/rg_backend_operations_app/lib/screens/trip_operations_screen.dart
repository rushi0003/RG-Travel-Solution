import 'package:flutter/material.dart';

import '../services/admin_service.dart';
import '../theme/ops_ui_tokens.dart';
import 'operations_ui.dart';

class TripOperationsScreen extends StatefulWidget {
  const TripOperationsScreen({super.key});

  @override
  State<TripOperationsScreen> createState() => _TripOperationsScreenState();
}

class _TripOperationsScreenState extends State<TripOperationsScreen> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _liveTrips = const [];
  List<Map<String, dynamic>> _swapRequests = const [];
  List<Map<String, dynamic>> _cancelRequests = const [];

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
        AdminService.fetchList('/api/admin/trips/live'),
        AdminService.fetchList('/api/admin/swap-requests'),
        AdminService.fetchList('/api/admin/trip-cancel-requests'),
      ]);
      if (!mounted) return;
      setState(() {
        _liveTrips = results[0];
        _swapRequests = results[1];
        _cancelRequests = results[2];
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
      title: 'Trip Operations',
      subtitle:
          'Monitor live movement, swap pressure, and cancellation signals that need backend intervention.',
      icon: Icons.alt_route_rounded,
      metrics: [
        OpsMetric(
          label: 'Live Trips',
          value: '${_liveTrips.length}',
          icon: Icons.timeline_rounded,
          tone: OpsUiTokens.info,
        ),
        OpsMetric(
          label: 'Swap Requests',
          value: '${_swapRequests.length}',
          icon: Icons.swap_horiz_rounded,
          tone: OpsUiTokens.warning,
        ),
        OpsMetric(
          label: 'Cancel Requests',
          value: '${_cancelRequests.length}',
          icon: Icons.cancel_schedule_send_rounded,
          tone: OpsUiTokens.danger,
        ),
      ],
      onRefresh: _load,
      child: _loading
          ? const OpsLoadingState(message: 'Loading trip operations...')
          : _error != null
              ? ErrorCard(message: _error!)
              : Column(
                  children: [
                    SectionCard(
                      title: 'Live Trips',
                      description:
                          'Trips that are actively running or currently visible to the backend operations layer.',
                      items: _liveTrips,
                      tone: OpsUiTokens.info,
                      subtitleBuilder: (item) =>
                          'Route: ${item['route_no'] ?? '-'} | Status: ${item['status'] ?? '-'}',
                    ),
                    const SizedBox(height: OpsSpacing.lg),
                    SectionCard(
                      title: 'Swap Requests',
                      description:
                          'Trip swap demand that may require approval or manual review by operations.',
                      items: _swapRequests,
                      tone: OpsUiTokens.warning,
                      subtitleBuilder: (item) =>
                          'Trip: ${item['trip_id'] ?? '-'} | Status: ${item['status'] ?? '-'}',
                    ),
                    const SizedBox(height: OpsSpacing.lg),
                    SectionCard(
                      title: 'Trip Cancel Requests',
                      description:
                          'Cancellation requests raised from the field with their current reason context.',
                      items: _cancelRequests,
                      tone: OpsUiTokens.danger,
                      subtitleBuilder: (item) =>
                          'Trip: ${item['trip_id'] ?? '-'} | Reason: ${item['reason'] ?? '-'}',
                    ),
                  ],
                ),
    );
  }
}
