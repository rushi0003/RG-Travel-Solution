import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/services/driver_service.dart';
import 'package:rg_travel_flutter/services/employee_service.dart';
import 'package:rg_travel_flutter/widgets/common/rg_card.dart';

class HelpDeskScreen extends StatefulWidget {
  final String userId;
  final String userType; // "driver" or "employee"

  const HelpDeskScreen({
    super.key,
    required this.userId,
    required this.userType,
  });

  @override
  State<HelpDeskScreen> createState() => _HelpDeskScreenState();
}

class _HelpDeskScreenState extends State<HelpDeskScreen> {
  final _formKey = GlobalKey<FormState>();

  final _subjectCtrl = TextEditingController();
  final _msgCtrl = TextEditingController();

  String _priority = "normal"; // low, normal, high
  bool _isLoading = false;

  @override
  void dispose() {
    _subjectCtrl.dispose();
    _msgCtrl.dispose();
    super.dispose();
  }

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      if (widget.userType == "driver") {
        await DriverService.createHelpdeskTicket(
          widget.userId,
          subject: _subjectCtrl.text.trim(),
          message: _msgCtrl.text.trim(),
          priority: _priority,
        );
      } else {
        final empId = int.tryParse(widget.userId);
        if (empId == null) {
          throw Exception("Invalid employee id");
        }
        await EmployeeService.createHelpdeskTicket(
          empId,
          subject: _subjectCtrl.text.trim(),
          message: _msgCtrl.text.trim(),
          priority: _priority,
        );
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Ticket submitted successfully! Admin will review it."),
        ),
      );
      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Error: ${e.toString().replaceAll('Exception: ', '')}"),
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
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
        child: SingleChildScrollView(
          padding: AppSpacing.pagePadding,
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 640),
              child: RGCard(
                title: "Support Request",
                subtitle: "Report an issue or request operational help.",
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: _priority,
                        decoration: const InputDecoration(
                          labelText: "Priority",
                          prefixIcon: Icon(Icons.priority_high_rounded),
                        ),
                        items: const [
                          DropdownMenuItem(value: "low", child: Text("Low")),
                          DropdownMenuItem(
                            value: "normal",
                            child: Text("Normal"),
                          ),
                          DropdownMenuItem(value: "high", child: Text("High")),
                        ],
                        onChanged: (v) => setState(() => _priority = v!),
                      ),
                      const SizedBox(height: AppSpacing.md),
                      TextFormField(
                        controller: _subjectCtrl,
                        decoration: const InputDecoration(
                          labelText: "Subject",
                          hintText: "Brief summary of the issue",
                          prefixIcon: Icon(Icons.subject_rounded),
                        ),
                        validator: (v) =>
                            (v == null || v.trim().isEmpty) ? "Required" : null,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      TextFormField(
                        controller: _msgCtrl,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: "Message",
                          hintText: "Describe your issue in detail...",
                          alignLabelWithHint: true,
                          prefixIcon: Icon(Icons.notes_rounded),
                        ),
                        validator: (v) =>
                            (v == null || v.trim().isEmpty) ? "Required" : null,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _isLoading ? null : _submit,
                          icon: _isLoading
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.send_rounded),
                          label: Text(
                            _isLoading ? "Submitting..." : "Submit Ticket",
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
