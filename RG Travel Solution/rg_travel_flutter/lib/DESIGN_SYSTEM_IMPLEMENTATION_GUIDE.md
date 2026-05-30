// flutter/lib/DESIGN_SYSTEM_IMPLEMENTATION_GUIDE.md
//
// ═══════════════════════════════════════════════════════════════════════════════
// RG TRAVEL SOLUTION — DESIGN SYSTEM IMPLEMENTATION GUIDE
// ═══════════════════════════════════════════════════════════════════════════════
//
// This document provides practical examples for implementing the new design system
// across all screens. Copy-paste code examples for common patterns.
//
// ═══════════════════════════════════════════════════════════════════════════════
// QUICK START EXAMPLES
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// 1. BASIC BUTTONS
// ═══════════════════════════════════════════════════════════════════════════════

// Primary action button (for creating, submitting)
ModernButton(
  label: 'Create Trip',
  onPressed: () => _createTrip(),
  variant: ModernButtonVariant.primary,
  size: ModernButtonSize.medium,
  leadingIcon: Icons.add,
  fullWidth: true,
);

// Secondary action (alternative action)
ModernButton(
  label: 'More Options',
  onPressed: () => _showMore(),
  variant: ModernButtonVariant.secondary,
  size: ModernButtonSize.medium,
);

// Outline button (e.g., Cancel)
ModernButton(
  label: 'Cancel',
  onPressed: () => Navigator.pop(context),
  variant: ModernButtonVariant.outline,
  size: ModernButtonSize.medium,
);

// Ghost button (minimal emphasis)
ModernButton(
  label: 'Learn More',
  onPressed: () => _openHelp(),
  variant: ModernButtonVariant.ghost,
  size: ModernButtonSize.small,
);

// Loading button
ModernButton(
  label: 'Save Changes',
  onPressed: isSaving ? null : () => _saveChanges(),
  isLoading: isSaving,
  variant: ModernButtonVariant.primary,
  fullWidth: true,
);

// Disabled button
ModernButton(
  label: 'Approve',
  onPressed: isSelected ? () => _approve() : null,
  isDisabled: !isSelected,
  variant: ModernButtonVariant.primary,
);

// ═══════════════════════════════════════════════════════════════════════════════
// 2. CARDS & CONTAINERS
// ═══════════════════════════════════════════════════════════════════════════════

// Full card with header and content
GlassmorphicCard(
  title: 'Active Trips',
  titleIcon: Icons.directions_car,
  subtitle: '3 ongoing deliveries',
  headerAction: IconButton(
    icon: Icon(Icons.more_vert),
    onPressed: () => _showMenu(),
  ),
  onTap: () => _viewAllTrips(),
  child: ListView(
    shrinkWrap: true,
    physics: NeverScrollableScrollPhysics(),
    children: trips.map((trip) => TripListItem(trip: trip)).toList(),
  ),
);

// Compact card (minimal padding)
CompactGlassmorphicCard(
  child: Row(
    children: [
      Icon(Icons.check_circle, color: AppThemeColors.success),
      SizedBox(width: AppSpacing.sm),
      Text('Trip completed', style: AppTypography.bodyMedium),
    ],
  ),
);

// Card with loading state
GlassmorphicCard(
  title: 'Loading Data',
  isLoading: true,
  child: const SizedBox.shrink(),
);

// Card with custom border and background
GlassmorphicCard(
  title: 'Featured',
  child: Text('Custom styled card'),
  borderColor: AppThemeColors.success,
  backgroundColor: AppThemeColors.success.withOpacity(0.1),
);

// ═══════════════════════════════════════════════════════════════════════════════
// 3. FORM FIELDS
// ═══════════════════════════════════════════════════════════════════════════════

// Basic text field
ModernTextField(
  label: 'Full Name',
  hint: 'John Doe',
  leadingIcon: Icons.person,
  helperText: 'Enter your full name',
  onChanged: (value) => setState(() => name = value),
  clearable: true,
);

// Text field with validation
ModernTextField(
  label: 'Email',
  hint: 'name@example.com',
  leadingIcon: Icons.email,
  errorText: email.isEmpty ? null : !isValidEmail(email) ? 'Invalid email' : null,
  keyboardType: TextInputType.emailAddress,
  onChanged: (value) => setState(() => email = value),
);

// Password field
PasswordTextField(
  label: 'Password',
  helperText: 'At least 8 characters',
  errorText: password.length < 8 ? 'Too short' : null,
  onChanged: (value) => setState(() => password = value),
);

// Phone field
PhoneTextField(
  label: 'Mobile Number',
  helperText: '10 digit number',
  errorText: phone.length != 10 ? 'Invalid phone' : null,
  onChanged: (value) => setState(() => phone = value),
);

// Email field
EmailTextField(
  label: 'Email Address',
  onChanged: (value) => setState(() => email = value),
);

// ═══════════════════════════════════════════════════════════════════════════════
// 4. RESPONSIVE LAYOUTS
// ═══════════════════════════════════════════════════════════════════════════════

// Responsive container (constrains max width on desktop)
ResponsiveContainer(
  desktopMaxWidth: 1280,
  child: Center(
    child: Column(
      children: [
        Text('This is centered and max 1280px wide on desktop'),
      ],
    ),
  ),
);

// Adaptive layout builder
AdaptiveLayout(
  mobileBuilder: (context) => Column(
    children: [
      Card1(),
      Card2(),
      Card3(),
    ],
  ),
  tabletBuilder: (context) => Row(
    children: [
      Expanded(child: Card1()),
      Expanded(child: Card2()),
      Expanded(child: Card3()),
    ],
  ),
  desktopBuilder: (context) => Row(
    children: [
      Expanded(flex: 2, child: Card1()),
      Expanded(flex: 1, child: Card2()),
      Expanded(flex: 1, child: Card3()),
    ],
  ),
);

// Check device type
if (context.isMobile) {
  // Single column layout
} else if (context.isTablet) {
  // Two-column layout
} else if (context.isDesktop) {
  // Multi-column layout
}

// ═══════════════════════════════════════════════════════════════════════════════
// 5. SPACING & LAYOUT PATTERNS
// ═══════════════════════════════════════════════════════════════════════════════

// Simple vertical spacing
Column(
  children: [
    Widget1(),
    SizedBox(height: AppSpacing.md),  // 16px
    Widget2(),
    SizedBox(height: AppSpacing.lg),  // 24px
    Widget3(),
  ],
);

// Padded container
Container(
  padding: AppSpacing.pagePadding,  // 16px all sides
  child: child,
);

// Horizontal spacing
Row(
  children: [
    Icon1(),
    SizedBox(width: AppSpacing.sm),  // 8px
    Text('Label'),
  ],
);

// Responsive padding
ResponsivePadding(
  mobilePadding: const EdgeInsets.all(12),
  tabletPadding: const EdgeInsets.all(16),
  desktopPadding: const EdgeInsets.all(24),
  child: child,
);

// ═══════════════════════════════════════════════════════════════════════════════
// 6. COMPLETE SCREEN EXAMPLE (Login Screen)
// ═══════════════════════════════════════════════════════════════════════════════

import 'package:flutter/material.dart';
import 'package:rg_travel_flutter/core/theme/app_theme.dart';
import 'package:rg_travel_flutter/core/theme/responsive.dart';
import 'package:rg_travel_flutter/widgets/common/glassmorphic_card.dart';
import 'package:rg_travel_flutter/widgets/common/modern_button.dart';
import 'package:rg_travel_flutter/widgets/common/modern_form_field.dart';

class ModernLoginScreen extends StatefulWidget {
  const ModernLoginScreen({super.key});

  @override
  State<ModernLoginScreen> createState() => _ModernLoginScreenState();
}

class _ModernLoginScreenState extends State<ModernLoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    setState(() => _isLoading = true);
    try {
      // Call your login API
      await _login();
      if (mounted) {
        Navigator.of(context).pushReplacementNamed('/dashboard');
      }
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _login() async {
    // TODO: Implement actual API call
    await Future.delayed(Duration(seconds: 2));
    throw 'Invalid credentials';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      body: ResponsiveContainer(
        child: Center(
          child: SingleChildScrollView(
            child: ResponsivePadding(
              child: SizedBox(
                width: context.isDesktop ? 400 : double.infinity,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    // Logo/Header
                    Text(
                      'RG Travel',
                      style: AppTypography.displayMedium.copyWith(
                        color: AppThemeColors.primary,
                      ),
                    ),
                    SizedBox(height: AppSpacing.sm),
                    Text(
                      'Commute Management System',
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppThemeColors.textSecondary,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: AppSpacing.xxl),

                    // Card with login form
                    GlassmorphicCard(
                      title: 'Sign In',
                      child: Column(
                        children: [
                          // Error message
                          if (_errorMessage != null)
                            Container(
                              padding: EdgeInsets.all(AppSpacing.sm),
                              decoration: BoxDecoration(
                                color: AppThemeColors.error.withOpacity(0.1),
                                border: Border.all(
                                  color: AppThemeColors.error,
                                ),
                                borderRadius: BorderRadius.circular(AppRadius.sm),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.error_outline,
                                    color: AppThemeColors.error,
                                  ),
                                  SizedBox(width: AppSpacing.sm),
                                  Expanded(
                                    child: Text(
                                      _errorMessage!,
                                      style: AppTypography.bodySmall.copyWith(
                                        color: AppThemeColors.error,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          if (_errorMessage != null)
                            SizedBox(height: AppSpacing.md),

                          // Email field
                          EmailTextField(
                            label: 'Email Address',
                            controller: _emailController,
                            helperText: 'Enter your registered email',
                            onChanged: (_) => setState(() => _errorMessage = null),
                          ),
                          SizedBox(height: AppSpacing.md),

                          // Password field
                          PasswordTextField(
                            label: 'Password',
                            controller: _passwordController,
                            helperText: 'Enter your password',
                            onChanged: (_) => setState(() => _errorMessage = null),
                          ),
                          SizedBox(height: AppSpacing.lg),

                          // Login button
                          PrimaryButton(
                            label: 'Sign In',
                            onPressed: _handleLogin,
                            isLoading: _isLoading,
                            fullWidth: true,
                          ),
                          SizedBox(height: AppSpacing.md),

                          // Forgot password link
                          TextButton(
                            onPressed: () => _showForgotPassword(),
                            child: Text(
                              'Forgot Password?',
                              style: AppTypography.bodySmall.copyWith(
                                color: AppThemeColors.primary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    SizedBox(height: AppSpacing.xxl),

                    // Footer text
                    Text(
                      'Don\'t have an account?',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppThemeColors.textSecondary,
                      ),
                    ),
                    SizedBox(height: AppSpacing.xs),
                    TextButton(
                      onPressed: () => _showSignUp(),
                      child: Text(
                        'Contact Administrator',
                        style: AppTypography.labelMedium.copyWith(
                          color: AppThemeColors.primary,
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
    );
  }

  void _showForgotPassword() {
    // TODO: Implement forgot password flow
  }

  void _showSignUp() {
    // TODO: Show sign up or contact info
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 7. COMPLETE SCREEN EXAMPLE (Dashboard)
// ═══════════════════════════════════════════════════════════════════════════════

class ModernDashboardScreen extends StatefulWidget {
  const ModernDashboardScreen({super.key});

  @override
  State<ModernDashboardScreen> createState() => _ModernDashboardScreenState();
}

class _ModernDashboardScreenState extends State<ModernDashboardScreen> {
  List<Trip> trips = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTrips();
  }

  Future<void> _loadTrips() async {
    // TODO: Call API to fetch trips
    await Future.delayed(Duration(seconds: 2));
    setState(() {
      trips = [
        // Trip data from API
      ];
      isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppThemeColors.background,
      appBar: AppBar(
        title: Text('Dashboard'),
      ),
      body: isLoading
          ? Center(
              child: CircularProgressIndicator(
                color: AppThemeColors.primary,
              ),
            )
          : ResponsiveContainer(
              child: RefreshIndicator(
                onRefresh: _loadTrips,
                color: AppThemeColors.primary,
                child: SingleChildScrollView(
                  physics: AlwaysScrollableScrollPhysics(),
                  padding: EdgeInsets.only(
                    top: AppSpacing.lg,
                    bottom: AppSpacing.lg,
                  ),
                  child: AdaptiveLayout(
                    mobileBuilder: (context) => _buildMobileLayout(),
                    tabletBuilder: (context) => _buildTabletLayout(),
                    desktopBuilder: (context) => _buildDesktopLayout(),
                  ),
                ),
              ),
            ),
    );
  }

  Widget _buildMobileLayout() {
    return Column(
      children: [
        GlassmorphicCard(
          title: 'Statistics',
          child: _buildStatsContent(),
        ),
        SizedBox(height: AppSpacing.lg),
        GlassmorphicCard(
          title: 'Recent Trips',
          child: _buildTripsContent(),
        ),
      ],
    );
  }

  Widget _buildTabletLayout() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: GlassmorphicCard(
                title: 'Statistics',
                child: _buildStatsContent(),
              ),
            ),
            SizedBox(width: AppSpacing.lg),
            Expanded(
              child: GlassmorphicCard(
                title: 'Quick Actions',
                child: _buildActionsContent(),
              ),
            ),
          ],
        ),
        SizedBox(height: AppSpacing.lg),
        GlassmorphicCard(
          title: 'Recent Trips',
          child: _buildTripsContent(),
        ),
      ],
    );
  }

  Widget _buildDesktopLayout() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 2,
          child: Column(
            children: [
              GlassmorphicCard(
                title: 'Recent Trips',
                child: _buildTripsContent(),
              ),
            ],
          ),
        ),
        SizedBox(width: AppSpacing.lg),
        Expanded(
          child: Column(
            children: [
              GlassmorphicCard(
                title: 'Statistics',
                child: _buildStatsContent(),
              ),
              SizedBox(height: AppSpacing.lg),
              GlassmorphicCard(
                title: 'Quick Actions',
                child: _buildActionsContent(),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStatsContent() {
    return Column(
      children: [
        _StatItem(label: 'Active Trips', value: '12'),
        _StatItem(label: 'Completed', value: '186'),
        _StatItem(label: 'Pending', value: '3'),
      ],
    );
  }

  Widget _buildTripsContent() {
    return trips.isEmpty
        ? Center(
            child: Text(
              'No trips available',
              style: AppTypography.bodyMedium.copyWith(
                color: AppThemeColors.textSecondary,
              ),
            ),
          )
        : ListView.separated(
            shrinkWrap: true,
            physics: NeverScrollableScrollPhysics(),
            itemCount: trips.length,
            separatorBuilder: (_, __) => Divider(
              color: AppThemeColors.border.withOpacity(0.3),
              height: AppSpacing.md,
            ),
            itemBuilder: (_, index) => _TripListItem(trip: trips[index]),
          );
  }

  Widget _buildActionsContent() {
    return Column(
      children: [
        PrimaryButton(
          label: 'New Trip',
          onPressed: () {},
          leadingIcon: Icons.add,
        ),
        SizedBox(height: AppSpacing.sm),
        SecondaryButton(
          label: 'View Reports',
          onPressed: () {},
        ),
      ],
    );
  }
}

// Reusable stat item
class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: AppTypography.bodyMedium),
          Text(
            value,
            style: AppTypography.headlineMedium.copyWith(
              color: AppThemeColors.primary,
            ),
          ),
        ],
      ),
    );
  }
}

// Reusable trip list item
class _TripListItem extends StatelessWidget {
  final Trip trip;

  const _TripListItem({required this.trip});

  @override
  Widget build(BuildContext context) {
    return CompactGlassmorphicCard(
      onTap: () {},
      child: Row(
        children: [
          Icon(Icons.trip_origin, color: AppThemeColors.primary),
          SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  trip.route,
                  style: AppTypography.bodyMedium.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  trip.status,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppThemeColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Icon(Icons.arrow_forward_ios, size: 16),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 8. KEY MIGRATION CHECKLIST
// ═══════════════════════════════════════════════════════════════════════════════
//
// When upgrading existing screens:
//
// ☐ Replace `RGButton` with `ModernButton`
// ☐ Replace `RGCard` with `GlassmorphicCard`
// ☐ Replace custom TextField with `ModernTextField`
// ☐ Replace hardcoded padding with `AppSpacing.*` constants
// ☐ Replace hardcoded colors with `AppThemeColors.*` constants
// ☐ Replace hardcoded font sizes with `AppTypography.*` styles
// ☐ Replace hardcoded radius with `AppRadius.*` constants
// ☐ Replace manual responsive checks with `context.isMobile`, etc.
// ☐ Use `ResponsivePadding` for adaptive spacing
// ☐ Add `AdaptiveLayout` builders for multi-device support
// ☐ Test on mobile (small), tablet (medium), and desktop (large)
// ☐ Verify all colors meet WCAG AA contrast requirements
// ☐ Add loading states for all API calls
// ☐ Add error handling and retry logic
// ☐ Remove all demo/hardcoded data - use real API data only
//
// ═══════════════════════════════════════════════════════════════════════════════
