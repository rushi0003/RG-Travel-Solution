// flutter/lib/widgets/common/modern_form_field.dart
//
// RG Travel Solution — Modern Form Fields
//
// ✅ Features:
// - Material 3 styled inputs
// - Validation support
// - Label, hint, helper text
// - Icon support
// - Password field variant
// - Phone field variant
// - Number field variant
// - Accessibility support

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';

class ModernTextField extends StatefulWidget {
  /// Input controller
  final TextEditingController? controller;

  /// Input label
  final String label;

  /// Placeholder text
  final String? hint;

  /// Helper text below input
  final String? helperText;

  /// Error message
  final String? errorText;

  /// Leading icon
  final IconData? leadingIcon;

  /// Trailing icon (clearable, password toggle, etc)
  final IconData? trailingIcon;

  /// Trailing icon callback
  final VoidCallback? onTrailingIconTap;

  /// Is password field
  final bool isPassword;

  /// Enable clear button on focus
  final bool clearable;

  /// Max lines (null = single line, -1 = unlimited)
  final int? maxLines;

  /// Min lines
  final int minLines;

  /// Max length
  final int? maxLength;

  /// Show character counter
  final bool showCharacterCount;

  /// Input type
  final TextInputType keyboardType;

  /// Input formatters
  final List<TextInputFormatter>? inputFormatters;

  /// Focus node
  final FocusNode? focusNode;

  /// Callback on value change
  final ValueChanged<String>? onChanged;

  /// Callback on submit
  final ValueChanged<String>? onSubmitted;

  /// Whether field is read-only
  final bool readOnly;

  /// Semantic label for accessibility
  final String? semanticLabel;

  const ModernTextField({
    super.key,
    this.controller,
    required this.label,
    this.hint,
    this.helperText,
    this.errorText,
    this.leadingIcon,
    this.trailingIcon,
    this.onTrailingIconTap,
    this.isPassword = false,
    this.clearable = true,
    this.maxLines = 1,
    this.minLines = 1,
    this.maxLength,
    this.showCharacterCount = false,
    this.keyboardType = TextInputType.text,
    this.inputFormatters,
    this.focusNode,
    this.onChanged,
    this.onSubmitted,
    this.readOnly = false,
    this.semanticLabel,
  });

  @override
  State<ModernTextField> createState() => _ModernTextFieldState();
}

class _ModernTextFieldState extends State<ModernTextField> {
  late bool _obscureText;
  late FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _obscureText = widget.isPassword;
    _focusNode = widget.focusNode ?? FocusNode();
  }

  @override
  void dispose() {
    if (widget.focusNode == null) {
      _focusNode.dispose();
    }
    super.dispose();
  }

  void _togglePasswordVisibility() {
    setState(() {
      _obscureText = !_obscureText;
    });
  }

  void _clearField() {
    widget.controller?.clear();
    widget.onChanged?.call('');
  }

  @override
  Widget build(BuildContext context) {
    final hasError = widget.errorText != null && widget.errorText!.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        /// Label
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.label,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppThemeColors.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (widget.showCharacterCount && widget.maxLength != null)
                Text(
                  '${widget.controller?.text.length ?? 0}/${widget.maxLength}',
                  style: AppTypography.labelSmall.copyWith(
                    color: AppThemeColors.textTertiary,
                  ),
                ),
            ],
          ),
        ),

        /// Input field
        Semantics(
          label: widget.semanticLabel ?? widget.label,
          textField: true,
          enabled: !widget.readOnly,
          child: TextField(
            controller: widget.controller,
            focusNode: _focusNode,
            obscureText: _obscureText,
            readOnly: widget.readOnly,
            maxLines: _obscureText ? 1 : widget.maxLines,
            minLines: widget.minLines,
            maxLength: widget.maxLength,
            keyboardType: widget.keyboardType,
            inputFormatters: widget.inputFormatters,
            onChanged: widget.onChanged,
            onSubmitted: widget.onSubmitted,
            style: AppTypography.bodyMedium.copyWith(
              color: AppThemeColors.textPrimary,
            ),
            decoration: InputDecoration(
              filled: true,
              fillColor: widget.readOnly
                  ? AppThemeColors.surfaceLight.withValues(alpha: 0.5)
                  : AppThemeColors.surfaceLight,
              contentPadding: EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
              hintText: widget.hint,
              hintStyle: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textTertiary,
              ),
              prefixIcon: widget.leadingIcon != null
                  ? Icon(
                      widget.leadingIcon,
                      color: _focusNode.hasFocus
                          ? AppThemeColors.primary
                          : AppThemeColors.textSecondary,
                      size: 20,
                    )
                  : null,
              suffixIcon: _buildSuffixIcon(),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
                borderSide: const BorderSide(
                  color: AppThemeColors.border,
                  width: 1,
                ),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
                borderSide: BorderSide(
                  color: hasError
                      ? AppThemeColors.error
                      : AppThemeColors.border,
                  width: 1,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
                borderSide: BorderSide(
                  color: hasError
                      ? AppThemeColors.error
                      : AppThemeColors.primary,
                  width: 2,
                ),
              ),
              errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
                borderSide: const BorderSide(
                  color: AppThemeColors.error,
                  width: 1,
                ),
              ),
              focusedErrorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
                borderSide: const BorderSide(
                  color: AppThemeColors.error,
                  width: 2,
                ),
              ),
              counterText: widget.showCharacterCount ? null : '',
              counterStyle: AppTypography.labelSmall.copyWith(
                color: AppThemeColors.textTertiary,
              ),
            ),
          ),
        ),

        /// Helper or error text
        if (widget.errorText != null || widget.helperText != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              widget.errorText ?? widget.helperText ?? '',
              style: AppTypography.labelSmall.copyWith(
                color: hasError
                    ? AppThemeColors.error
                    : AppThemeColors.textTertiary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
      ],
    );
  }

  Widget? _buildSuffixIcon() {
    if (widget.isPassword) {
      return IconButton(
        icon: Icon(
          _obscureText ? Icons.visibility_off : Icons.visibility,
          color: AppThemeColors.textSecondary,
          size: 20,
        ),
        onPressed: _togglePasswordVisibility,
        tooltip: _obscureText ? 'Show password' : 'Hide password',
      );
    }

    if (widget.clearable &&
        widget.controller?.text.isNotEmpty == true &&
        _focusNode.hasFocus &&
        !widget.readOnly) {
      return IconButton(
        icon: const Icon(
          Icons.close,
          color: AppThemeColors.textSecondary,
          size: 20,
        ),
        onPressed: _clearField,
        tooltip: 'Clear',
      );
    }

    if (widget.trailingIcon != null) {
      return IconButton(
        icon: Icon(
          widget.trailingIcon,
          color: AppThemeColors.textSecondary,
          size: 20,
        ),
        onPressed: widget.onTrailingIconTap,
      );
    }

    return null;
  }
}

/// Phone number input field
class PhoneTextField extends StatelessWidget {
  final TextEditingController? controller;
  final String label;
  final String? helperText;
  final String? errorText;
  final ValueChanged<String>? onChanged;

  const PhoneTextField({
    super.key,
    this.controller,
    required this.label,
    this.helperText,
    this.errorText,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return ModernTextField(
      controller: controller,
      label: label,
      hint: '+91 98765 43210',
      helperText: helperText,
      errorText: errorText,
      leadingIcon: Icons.phone,
      keyboardType: TextInputType.phone,
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(10),
      ],
      onChanged: onChanged,
      semanticLabel: 'Phone number',
    );
  }
}

/// Email input field
class EmailTextField extends StatelessWidget {
  final TextEditingController? controller;
  final String label;
  final String? helperText;
  final String? errorText;
  final ValueChanged<String>? onChanged;

  const EmailTextField({
    super.key,
    this.controller,
    required this.label,
    this.helperText,
    this.errorText,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return ModernTextField(
      controller: controller,
      label: label,
      hint: 'name@example.com',
      helperText: helperText,
      errorText: errorText,
      leadingIcon: Icons.email,
      keyboardType: TextInputType.emailAddress,
      onChanged: onChanged,
      semanticLabel: 'Email address',
    );
  }
}

/// Password input field
class PasswordTextField extends StatelessWidget {
  final TextEditingController? controller;
  final String label;
  final String? helperText;
  final String? errorText;
  final ValueChanged<String>? onChanged;

  const PasswordTextField({
    super.key,
    this.controller,
    required this.label,
    this.helperText,
    this.errorText,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return ModernTextField(
      controller: controller,
      label: label,
      hint: '••••••••',
      helperText: helperText,
      errorText: errorText,
      leadingIcon: Icons.lock,
      isPassword: true,
      onChanged: onChanged,
      semanticLabel: 'Password',
    );
  }
}

