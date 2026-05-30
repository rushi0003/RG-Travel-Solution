import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/services/admin_service.dart';

class AdminHelpDeskScreen extends StatefulWidget {
  const AdminHelpDeskScreen({super.key});

  @override
  State<AdminHelpDeskScreen> createState() => _AdminHelpDeskScreenState();
}

class _AdminHelpDeskScreenState extends State<AdminHelpDeskScreen> {
  bool _isLoading = false;
  List<Map<String, dynamic>> _tickets = [];
  final _dateFormat = DateFormat("yyyy-MM-dd HH:mm");

  @override
  void initState() {
    super.initState();
    _loadTickets();
  }

  Future<void> _loadTickets() async {
    setState(() => _isLoading = true);
    try {
      final data = await AdminService.getHelpdeskTickets();
      setState(() => _tickets = data);
    } catch (e) {
      if (mounted) {
         ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showResolveDialog(Map<String, dynamic> ticket) {
    if (ticket["status"] == "resolved") return;

    final noteCtrl = TextEditingController();
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppThemeColors.surface,
        title: Text("Resolve Ticket", style: AppTypography.titleMedium.copyWith(color: AppThemeColors.textPrimary)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Subject: ${ticket['subject']}", style: AppTypography.bodyMedium.copyWith(color: AppThemeColors.textSecondary)),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: noteCtrl,
              style: AppTypography.bodyMedium.copyWith(color: AppThemeColors.textPrimary),
              decoration: InputDecoration(
                labelText: "Resolution Note",
                labelStyle: AppTypography.labelMedium.copyWith(color: AppThemeColors.textSecondary),
                filled: true,
                fillColor: AppThemeColors.surfaceLight,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.sm), borderSide: const BorderSide(color: AppThemeColors.border)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.sm), borderSide: const BorderSide(color: AppThemeColors.border)),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.sm), borderSide: const BorderSide(color: AppThemeColors.primary)),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text("Cancel", style: AppTypography.labelLarge.copyWith(color: AppThemeColors.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final ticketId = ticket['id'] as int? ?? 0;
              _resolveTicket(ticketId, noteCtrl.text.trim());
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppThemeColors.primary,
              foregroundColor: AppThemeColors.textPrimary,
            ),
            child: const Text("Resolve"),
          ),
        ],
      ),
    );
  }

  Future<void> _resolveTicket(int ticketId, String note) async {
    setState(() => _isLoading = true);
    try {
      await AdminService.resolveHelpdeskTicket(ticketId, note: note);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Ticket resolved.")));
      _loadTickets();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: Text("Help Desk Tickets", style: AppTypography.headlineMedium.copyWith(color: AppThemeColors.textPrimary)),
        backgroundColor: AppThemeColors.background,
        elevation: 0,
        iconTheme: const IconThemeData(color: AppThemeColors.textPrimary),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadTickets),
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: AppThemeColors.primary))
        : _tickets.isEmpty 
          ? Center(child: Text("No tickets found.", style: AppTypography.bodyLarge.copyWith(color: AppThemeColors.textSecondary)))
          : ListView.separated(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: _tickets.length,
              separatorBuilder: (_,__) => const SizedBox(height: AppSpacing.md),
              itemBuilder: (ctx, i) => _buildTicketCard(_tickets[i]),
            ),
    );
  }

  Widget _buildTicketCard(Map<String, dynamic> ticket) {
    final status = ticket["status"] ?? "open";
    final statusStr = (status as String?) ?? "open";
    final isOpen = statusStr == "open";
    final priority = ticket["priority"] ?? "normal";
    final dateStr = ticket["created_at"] as String?;
    
    // safe date parse
    String displayDate = dateStr ?? "No date"; 
    try {
        if (dateStr != null) {
            displayDate = _dateFormat.format(DateTime.parse(dateStr));
        }
    } catch (_) {}

    return Container(
      decoration: BoxDecoration(
        color: AppThemeColors.cardGlass.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppThemeColors.border),
      ),
      child: InkWell(
        onTap: () => _showResolveDialog(ticket),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                   Container(
                     padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                     decoration: BoxDecoration(
                       color: isOpen ? AppThemeColors.warning.withValues(alpha: 0.2) : AppThemeColors.success.withValues(alpha: 0.2),
                       borderRadius: BorderRadius.circular(AppRadius.xs),
                       border: Border.all(color: isOpen ? AppThemeColors.warning.withValues(alpha: 0.5) : AppThemeColors.success.withValues(alpha: 0.5)),
                     ),
                     child: Text(statusStr.toUpperCase(), 
                       style: AppTypography.labelSmall.copyWith(
                         fontWeight: FontWeight.bold, 
                         color: isOpen ? AppThemeColors.warning : AppThemeColors.success
                       )
                     ),
                   ),
                   Text(displayDate, style: AppTypography.labelSmall.copyWith(color: AppThemeColors.textSecondary)),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              Text((ticket['subject'] as String?) ?? '', style: AppTypography.titleSmall.copyWith(color: AppThemeColors.textPrimary, fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text((ticket['message'] as String?) ?? '', style: AppTypography.bodyMedium.copyWith(color: AppThemeColors.textSecondary)),
              const SizedBox(height: AppSpacing.md),
              const Divider(color: AppThemeColors.border, height: 1),
              const SizedBox(height: AppSpacing.sm),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text("User: ${(ticket['user_name'] as String?) ?? 'Unknown'} (${(ticket['user_type'] as String?) ?? 'N/A'})", style: AppTypography.labelSmall.copyWith(color: AppThemeColors.textTertiary)),
                  Text("Priority: $priority", 
                    style: AppTypography.labelSmall.copyWith(
                      color: priority == 'high' ? AppThemeColors.error : AppThemeColors.textSecondary,
                      fontWeight: priority == 'high' ? FontWeight.bold : FontWeight.normal, 
                    )
                  ),
                ],
              ),
              if (!isOpen && ticket['admin_notes'] != null) ...[
                 const SizedBox(height: AppSpacing.sm),
                 Container(
                   padding: const EdgeInsets.all(AppSpacing.sm),
                   decoration: BoxDecoration(color: AppThemeColors.surfaceLight, borderRadius: BorderRadius.circular(AppRadius.sm)),
                   child: Text("Admin Note: ${ticket['admin_notes']}", style: AppTypography.bodySmall.copyWith(color: AppThemeColors.textSecondary, fontStyle: FontStyle.italic)),
                 )
              ]
            ],
          ),
        ),
      ),
    );
  }
}
