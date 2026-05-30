// flutter/lib/widgets/common/rg_search_field.dart
//
// RG Travel Solution — NLP-like Search Field
//
// ✅ Features:
// - Debounced search input
// - Clear button
// - Optional filter chips
// - Glassmorphism styling
// - Accessibility support

import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Modern search field with debounce, clear button, and optional filter chips.
///
/// Usage:
/// ```dart
/// RGSearchField(
///   hint: 'Search drivers...',
///   onChanged: (query) => _filterList(query),
/// )
/// ```
class RGSearchField extends StatefulWidget {
  final String hint;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final TextEditingController? controller;
  final Duration debounceDuration;
  final List<RGFilterChip>? filterChips;
  final bool autofocus;
  final Widget? prefixIcon;

  const RGSearchField({
    super.key,
    this.hint = 'Search...',
    this.onChanged,
    this.onSubmitted,
    this.controller,
    this.debounceDuration = const Duration(milliseconds: 350),
    this.filterChips,
    this.autofocus = false,
    this.prefixIcon,
  });

  @override
  State<RGSearchField> createState() => _RGSearchFieldState();
}

class _RGSearchFieldState extends State<RGSearchField> {
  late TextEditingController _controller;
  Timer? _debounceTimer;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? TextEditingController();
    _hasText = _controller.text.isNotEmpty;
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    if (widget.controller == null) {
      _controller.dispose();
    } else {
      _controller.removeListener(_onTextChanged);
    }
    super.dispose();
  }

  void _onTextChanged() {
    final hasText = _controller.text.isNotEmpty;
    if (hasText != _hasText) {
      setState(() => _hasText = hasText);
    }

    _debounceTimer?.cancel();
    _debounceTimer = Timer(widget.debounceDuration, () {
      widget.onChanged?.call(_controller.text);
    });
  }

  void _clear() {
    _controller.clear();
    widget.onChanged?.call('');
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          decoration: BoxDecoration(
            color: AppThemeColors.surfaceLight,
            borderRadius: BorderRadius.circular(AppRadius.sm),
            border: Border.all(color: AppThemeColors.border),
          ),
          child: Row(
            children: [
              Padding(
                padding: const EdgeInsets.only(left: AppSpacing.md),
                child: widget.prefixIcon ??
                    const Icon(
                      Icons.search_rounded,
                      size: AppIconSizes.md,
                      color: AppThemeColors.textTertiary,
                    ),
              ),
              Expanded(
                child: TextField(
                  controller: _controller,
                  autofocus: widget.autofocus,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppThemeColors.textPrimary,
                  ),
                  decoration: InputDecoration(
                    hintText: widget.hint,
                    hintStyle: AppTypography.bodyMedium.copyWith(
                      color: AppThemeColors.textTertiary,
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.md,
                    ),
                  ),
                  onSubmitted: widget.onSubmitted,
                ),
              ),
              if (_hasText)
                IconButton(
                  onPressed: _clear,
                  icon: const Icon(
                    Icons.close_rounded,
                    size: AppIconSizes.sm,
                    color: AppThemeColors.textSecondary,
                  ),
                  tooltip: 'Clear search',
                  splashRadius: 18,
                ),
            ],
          ),
        ),
        // Filter chips
        if (widget.filterChips != null && widget.filterChips!.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.xs,
            children: widget.filterChips!,
          ),
        ],
      ],
    );
  }
}

/// Filter chip for use with [RGSearchField].
class RGFilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback? onTap;

  const RGFilterChip({
    super.key,
    required this.label,
    this.selected = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: AppAnimations.fast,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs + 2,
        ),
        decoration: BoxDecoration(
          color: selected
              ? AppThemeColors.primary.withValues(alpha: 0.15)
              : AppThemeColors.surfaceLight,
          borderRadius: BorderRadius.circular(AppRadius.full),
          border: Border.all(
            color: selected
                ? AppThemeColors.primary.withValues(alpha: 0.4)
                : AppThemeColors.border,
          ),
        ),
        child: Text(
          label,
          style: AppTypography.labelMedium.copyWith(
            color: selected
                ? AppThemeColors.primary
                : AppThemeColors.textSecondary,
          ),
        ),
      ),
    );
  }
}

