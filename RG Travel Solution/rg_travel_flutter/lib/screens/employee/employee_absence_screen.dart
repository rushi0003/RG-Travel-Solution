import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../services/employee_service.dart';
import '../../widgets/common/rg_button.dart';
import '../../widgets/common/rg_card.dart';

class EmployeeAbsenceScreen extends StatefulWidget {
  final String employeeId;
  const EmployeeAbsenceScreen({super.key, required this.employeeId});

  @override
  State<EmployeeAbsenceScreen> createState() => _EmployeeAbsenceScreenState();
}

class _EmployeeAbsenceScreenState extends State<EmployeeAbsenceScreen> {
  DateTimeRange? _selectedRange;
  final _reasonCtrl = TextEditingController();
  bool _loading = false;
  List<Map<String, dynamic>> _history = [];
  bool _historyLoading = true;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  @override
  void dispose() {
    _reasonCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadHistory() async {
    try {
      final id = int.tryParse(widget.employeeId) ?? 0;
      final data = await EmployeeService.getAbsenceRequests(id);
      if (mounted) {
        setState(() {
          _history = data;
          _historyLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _historyLoading = false);
    }
  }

  Future<void> _submitRequest() async {
    if (_selectedRange == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select absence dates')),
      );
      return;
    }

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    if (!_selectedRange!.start.isAfter(today) ||
        !_selectedRange!.end.isAfter(today)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Absence must be for tomorrow or later')),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      final id = int.tryParse(widget.employeeId) ?? 0;
      await EmployeeService.requestAbsent(
        id,
        fromDate: DateFormat('yyyy-MM-dd').format(_selectedRange!.start),
        toDate: DateFormat('yyyy-MM-dd').format(_selectedRange!.end),
        reason: _reasonCtrl.text.trim(),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Absence request submitted')),
        );
        _reasonCtrl.clear();
        setState(() => _selectedRange = null);
        _loadHistory();
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

  Future<void> _pickDateRange() async {
    final now = DateTime.now();
    final firstDate = now.add(const Duration(days: 1));
    final picked = await showDateRangePicker(
      context: context,
      initialDateRange:
          _selectedRange ?? DateTimeRange(start: firstDate, end: firstDate),
      firstDate: firstDate,
      lastDate: now.add(const Duration(days: 60)),
      builder: (context, child) {
        final theme = Theme.of(context);
        return Theme(
          data: theme.copyWith(
            colorScheme: theme.colorScheme.copyWith(
              primary: AppThemeColors.primary,
              onPrimary: AppThemeColors.background,
              surface: AppThemeColors.surface,
              onSurface: AppThemeColors.textPrimary,
            ),
          ),
          child: child!,
        );
      },
    );
    if (picked != null) {
      setState(() => _selectedRange = picked);
    }
  }

  Future<void> _requestCancel(Map<String, dynamic> item) async {
    final id = int.tryParse(widget.employeeId) ?? 0;
    final dates = ((item['dates'] as List?) ?? const <dynamic>[])
        .map((e) => e.toString())
        .where((e) => e.isNotEmpty)
        .toList();
    if (dates.isEmpty) return;

    setState(() => _loading = true);
    try {
      await EmployeeService.requestAbsenceCancellation(
        id,
        dates: dates,
        reason: 'Need to cancel approved absence request',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cancellation request sent to admin')),
      );
      await _loadHistory();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _formatRangeLabel() {
    if (_selectedRange == null) {
      return 'Select absence range (tomorrow or later)';
    }
    final start = DateFormat('EEE, d MMM yyyy').format(_selectedRange!.start);
    final end = DateFormat('EEE, d MMM yyyy').format(_selectedRange!.end);
    final dayCount = _selectedRange!.duration.inDays + 1;
    return dayCount <= 1 ? start : '$start -> $end ($dayCount days)';
  }

  String _historyDateLabel(Map<String, dynamic> item) {
    final fromDate =
        (item['from_date'] ?? item['absent_date'] ?? '').toString();
    final toDate = (item['to_date'] ?? item['absent_date'] ?? '').toString();
    final totalDays = int.tryParse((item['total_days'] ?? '').toString()) ?? 1;
    if (fromDate.isEmpty) return '-';
    if (fromDate == toDate || totalDays <= 1) return fromDate;
    return '$fromDate -> $toDate ($totalDays days)';
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'approved':
        return AppThemeColors.success;
      case 'rejected':
        return AppThemeColors.error;
      default:
        return AppThemeColors.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text('Request Absence'),
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

              return Padding(
                padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
                child: Column(
                  children: [
                    const SizedBox(height: AppSpacing.md),
                    RGCard(
                      title: 'New Request',
                      subtitle: 'Plan absence for tomorrow or later.',
                      child: Column(
                        children: [
                          InkWell(
                            onTap: _pickDateRange,
                            borderRadius: BorderRadius.circular(AppRadius.sm),
                            child: Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(
                                horizontal: AppSpacing.md,
                                vertical: 14,
                              ),
                              decoration: BoxDecoration(
                                color: AppThemeColors.cardGlass,
                                borderRadius:
                                    BorderRadius.circular(AppRadius.sm),
                                border: Border.all(
                                  color: AppThemeColors.borderLight
                                      .withValues(alpha: 0.45),
                                ),
                              ),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.calendar_today_outlined,
                                    color: AppThemeColors.primary,
                                    size: 20,
                                  ),
                                  const SizedBox(width: AppSpacing.sm),
                                  Expanded(
                                    child: Text(
                                      _formatRangeLabel(),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: AppTypography.bodyMedium.copyWith(
                                        color: _selectedRange == null
                                            ? AppThemeColors.textTertiary
                                            : AppThemeColors.textPrimary,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            controller: _reasonCtrl,
                            maxLines: 2,
                            decoration: const InputDecoration(
                              hintText: 'Reason (optional)',
                              prefixIcon: Icon(Icons.notes_rounded, size: 20),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          RGButton(
                            text: 'Submit Request',
                            icon: Icons.send_rounded,
                            isLoading: _loading,
                            onPressed: _loading ? null : _submitRequest,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Request History',
                        style: AppTypography.titleSmall.copyWith(
                          color: AppThemeColors.textSecondary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Expanded(
                      child: _historyLoading
                          ? const Center(child: CircularProgressIndicator())
                          : _history.isEmpty
                              ? const _EmptyState(
                                  icon: Icons.event_available_outlined,
                                  message: 'No absence requests found',
                                )
                              : ListView.builder(
                                  padding: const EdgeInsets.only(
                                    bottom: AppSpacing.lg,
                                  ),
                                  itemCount: _history.length,
                                  itemBuilder: (context, index) {
                                    final item = _history[index];
                                    final status = (item['status'] ?? 'pending')
                                        .toString()
                                        .toLowerCase();
                                    final requestKind =
                                        (item['request_kind'] ?? 'absence')
                                            .toString()
                                            .toLowerCase();
                                    final statusColor = _statusColor(status);
                                    final canRequestCancel =
                                        item['can_request_cancel'] == true &&
                                            requestKind == 'absence' &&
                                            status == 'approved';
                                    final reason =
                                        (item['reason'] ?? '').toString();

                                    return RGCard(
                                      margin: const EdgeInsets.only(
                                        bottom: AppSpacing.sm,
                                      ),
                                      padding: const EdgeInsets.all(
                                        AppSpacing.md,
                                      ),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  _historyDateLabel(item),
                                                  style: AppTypography
                                                      .titleSmall
                                                      .copyWith(
                                                    color: AppThemeColors
                                                        .textPrimary,
                                                    fontWeight: FontWeight.w800,
                                                  ),
                                                ),
                                              ),
                                              const SizedBox(
                                                width: AppSpacing.sm,
                                              ),
                                              _StatusBadge(
                                                label: status.toUpperCase(),
                                                color: statusColor,
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: AppSpacing.xs),
                                          Text(
                                            requestKind == 'cancel'
                                                ? 'Cancel request'
                                                : 'Absence request',
                                            style: AppTypography.bodySmall
                                                .copyWith(
                                              color:
                                                  AppThemeColors.textSecondary,
                                            ),
                                          ),
                                          if (reason.isNotEmpty) ...[
                                            const SizedBox(
                                              height: AppSpacing.xs,
                                            ),
                                            Text(
                                              reason,
                                              style: AppTypography.bodySmall
                                                  .copyWith(
                                                color:
                                                    AppThemeColors.textTertiary,
                                              ),
                                            ),
                                          ],
                                          if (canRequestCancel) ...[
                                            const SizedBox(
                                              height: AppSpacing.sm,
                                            ),
                                            Align(
                                              alignment: Alignment.centerRight,
                                              child: TextButton.icon(
                                                onPressed: _loading
                                                    ? null
                                                    : () =>
                                                        _requestCancel(item),
                                                icon: const Icon(
                                                  Icons.undo_rounded,
                                                  size: 18,
                                                ),
                                                label: const Text(
                                                  'Request Cancel',
                                                ),
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    );
                                  },
                                ),
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

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(AppRadius.xs),
        border: Border.all(color: color.withValues(alpha: 0.38)),
      ),
      child: Text(
        label,
        style: AppTypography.bodySmall.copyWith(
          color: color,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({
    required this.icon,
    required this.message,
  });

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: RGCard(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: AppThemeColors.textTertiary, size: 32),
            const SizedBox(height: AppSpacing.sm),
            Text(
              message,
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
