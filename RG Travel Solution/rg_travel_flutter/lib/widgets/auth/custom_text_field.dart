// lib/widgets/auth/custom_text_field.dart
//
// RG Travel Solution — Custom Text Field
//
// Reusable text field with dark futuristic styling and inline error display

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme/app_theme.dart';

class CustomTextField extends StatefulWidget {
  const CustomTextField({
    super.key,
    required this.controller,
    required this.label,
    required this.hint,
    required this.icon,
    this.errorText,
    this.obscureText = false,
    this.keyboardType,
    this.inputFormatters,
    this.onChanged,
    this.maxLength,
  });

  final TextEditingController controller;
  final String label;
  final String hint;
  final IconData icon;
  final String? errorText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final ValueChanged<String>? onChanged;
  final int? maxLength;

  @override
  State<CustomTextField> createState() => _CustomTextFieldState();
}

class _CustomTextFieldState extends State<CustomTextField> {
  bool _obscured = true;

  @override
  void initState() {
    super.initState();
    _obscured = widget.obscureText;
  }

  @override
  Widget build(BuildContext context) {
    final hasError = widget.errorText != null && widget.errorText!.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: widget.controller,
          obscureText: widget.obscureText && _obscured,
          keyboardType: widget.keyboardType,
          inputFormatters: widget.inputFormatters,
          onChanged: widget.onChanged,
          maxLength: widget.maxLength,
          style: AppTypography.bodyMedium.copyWith(
            color: AppThemeColors.textPrimary,
            fontWeight: FontWeight.w500,
          ),
          decoration: InputDecoration(
            labelText: widget.label,
            hintText: widget.hint,
            counterText: '', // Hide character counter
            labelStyle: AppTypography.labelSmall.copyWith(
              color: hasError
                  ? AppThemeColors.error.withValues(alpha: 0.85)
                  : AppThemeColors.textSecondary,
            ),
            hintStyle: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textTertiary,
            ),
            prefixIcon: Icon(
              widget.icon,
              color: hasError
                  ? AppThemeColors.error.withValues(alpha: 0.75)
                  : AppThemeColors.textSecondary,
              size: AppIconSizes.md,
            ),
            suffixIcon: widget.obscureText
                ? IconButton(
                    icon: Icon(
                      _obscured ? Icons.visibility_off : Icons.visibility,
                      color: AppThemeColors.textSecondary,
                      size: AppIconSizes.sm,
                    ),
                    onPressed: () {
                      setState(() {
                        _obscured = !_obscured;
                      });
                    },
                  )
                : null,
            filled: true,
            fillColor: hasError
                ? AppThemeColors.error.withValues(alpha: 0.05)
                : AppThemeColors.cardGlass,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: BorderSide(
                color: hasError
                    ? AppThemeColors.error.withValues(alpha: 0.4)
                    : AppThemeColors.border,
                width: 1,
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: BorderSide(
                color: hasError
                    ? AppThemeColors.error.withValues(alpha: 0.4)
                    : AppThemeColors.border,
                width: 1,
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
              borderSide: BorderSide(
                color: hasError
                    ? AppThemeColors.error.withValues(alpha: 0.7)
                    : AppThemeColors.primary.withValues(alpha: 0.6),
                width: 1.5,
              ),
            ),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.md,
            ),
          ),
        ),
        if (hasError) ...[
          const SizedBox(height: 6),
          Padding(
            padding: const EdgeInsets.only(left: AppSpacing.md),
            child: Row(
              children: [
                Icon(
                  Icons.error_outline,
                  color: AppThemeColors.error.withValues(alpha: 0.85),
                  size: AppIconSizes.xs,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    widget.errorText!,
                    style: AppTypography.labelSmall.copyWith(
                      color: AppThemeColors.error.withValues(alpha: 0.85),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
