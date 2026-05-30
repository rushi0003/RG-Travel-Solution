import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../services/employee_service.dart';
import '../../widgets/common/rg_card.dart';

class HelpDeskScreen extends StatefulWidget {
  final String employeeId;
  const HelpDeskScreen({super.key, required this.employeeId});

  @override
  State<HelpDeskScreen> createState() => _HelpDeskScreenState();
}

class _HelpDeskScreenState extends State<HelpDeskScreen> {
  final _messageCtrl = TextEditingController();
  String _issueType = "Cab Issue"; // Default subject
  String _priority = "normal";
  bool _loading = false;

  final List<String> _issueTypes = [
    "Cab Issue",
    "Driver Behavior",
    "Route Issue",
    "App Issue",
    "Other",
  ];

  @override
  void dispose() {
    _messageCtrl.dispose();
    super.dispose();
  }

  Future<void> _submitTicket() async {
    final msg = _messageCtrl.text.trim();
    if (msg.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please describe your issue")),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      final id = int.tryParse(widget.employeeId) ?? 0;
      await EmployeeService.createHelpdeskTicket(
        id,
        subject: _issueType,
        message: msg,
        priority: _priority,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Ticket Submitted Successfully")),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error: $e")),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: const Text("Help Desk"),
      ),
      body: Container(
        decoration:
            const BoxDecoration(gradient: AppGradients.backgroundGradient),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: AppSpacing.pagePadding,
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 640),
                child: RGCard(
                  title: "Create Support Ticket",
                  subtitle: "Share the issue details with the operations team.",
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: _issueType,
                        decoration: const InputDecoration(
                          labelText: "Issue Type",
                          prefixIcon: Icon(Icons.category_rounded),
                        ),
                        items: _issueTypes
                            .map(
                              (t) => DropdownMenuItem(value: t, child: Text(t)),
                            )
                            .toList(),
                        onChanged: (v) => setState(() => _issueType = v!),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      DropdownButtonFormField<String>(
                        initialValue: _priority,
                        decoration: const InputDecoration(
                          labelText: "Priority",
                          prefixIcon: Icon(Icons.priority_high_rounded),
                        ),
                        items: ["low", "normal", "high"]
                            .map(
                              (p) => DropdownMenuItem(
                                value: p,
                                child: Text(p.toUpperCase()),
                              ),
                            )
                            .toList(),
                        onChanged: (v) => setState(() => _priority = v!),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      TextField(
                        controller: _messageCtrl,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: "Description",
                          hintText: "Describe your issue in detail...",
                          alignLabelWithHint: true,
                          prefixIcon: Icon(Icons.notes_rounded),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xl),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _loading ? null : _submitTicket,
                          icon: _loading
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.send_rounded),
                          label: Text(
                            _loading ? "Sending..." : "Submit Ticket",
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
