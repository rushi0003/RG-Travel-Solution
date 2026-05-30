import 'package:flutter/material.dart';

import '../services/admin_service.dart';
import '../services/ops_auth_service.dart';
import '../services/ops_session_store.dart';
import '../theme/ops_ui_tokens.dart';
import 'backend_operations_dashboard.dart';

class OpsLoginScreen extends StatefulWidget {
  const OpsLoginScreen({super.key});

  @override
  State<OpsLoginScreen> createState() => _OpsLoginScreenState();
}

class _OpsLoginScreenState extends State<OpsLoginScreen> {
  final _mobileController = TextEditingController();
  final _passwordController = TextEditingController();
  final _baseUrlController = TextEditingController(text: AdminService.baseUrl);
  bool _loading = false;
  bool _obscurePassword = true;
  String? _error;

  @override
  void dispose() {
    _mobileController.dispose();
    _passwordController.dispose();
    _baseUrlController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      AdminService.setBaseUrl(_baseUrlController.text);
      await OpsSessionStore.setBaseUrl(AdminService.baseUrl);
      final result = await OpsAuthService.login(
        mobile: _mobileController.text,
        password: _passwordController.text,
      );
      await OpsSessionStore.saveSession(
        token: result.token,
        mobile: result.mobile,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const BackendOperationsDashboard()),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
      return;
    }
    if (!mounted) return;
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: OpsUiTokens.loginBackgroundGradient,
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1240),
              child: Padding(
                padding: context.opsPagePadding,
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth >= 980;
                    if (isWide) {
                      return Row(
                        children: [
                          Expanded(child: _buildIntroPanel(theme)),
                          const SizedBox(width: OpsSpacing.xxl),
                          SizedBox(width: 460, child: _buildLoginPanel(theme)),
                        ],
                      );
                    }
                    return SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _buildIntroPanel(theme),
                          const SizedBox(height: OpsSpacing.xl),
                          _buildLoginPanel(theme),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildIntroPanel(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(OpsSpacing.xxxl),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(OpsRadius.xxl),
        gradient: const LinearGradient(
          colors: OpsUiTokens.heroGradient,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: OpsUiTokens.outlineStrong),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(OpsSpacing.lg),
            decoration: BoxDecoration(
              color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(OpsRadius.lg),
            ),
            child: const Icon(
              Icons.hub_rounded,
              size: 34,
              color: OpsUiTokens.primarySoft,
            ),
          ),
          const SizedBox(height: OpsSpacing.xxl),
          Text(
            'RG Backend Operations Login',
            style: theme.textTheme.displaySmall?.copyWith(
              fontWeight: FontWeight.w700,
              height: 1.05,
            ),
          ),
          const SizedBox(height: OpsSpacing.md),
          const Text(
            'Dedicated control surface for admin access, trip interventions, request handling, fleet visibility, and support monitoring.',
            style: OpsTypography.subtitle,
          ),
          const SizedBox(height: OpsSpacing.xxl),
          const Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _FeatureChip(
                icon: Icons.admin_panel_settings_rounded,
                label: 'Admin access control',
              ),
              _FeatureChip(
                icon: Icons.alt_route_rounded,
                label: 'Live ops visibility',
              ),
              _FeatureChip(
                icon: Icons.support_agent_rounded,
                label: 'Support response queue',
              ),
            ],
          ),
          const SizedBox(height: OpsSpacing.xxl),
          const _InfoTile(
            icon: Icons.shield_outlined,
            title: 'Restricted access',
            description:
                'Use credentials issued from the backend admin table. This panel is separate from the main travel app sign-in.',
          ),
          const SizedBox(height: OpsSpacing.md),
          const _InfoTile(
            icon: Icons.storage_rounded,
            title: 'Direct backend connection',
            description:
                'The base URL below points this app straight to the Flask backend used by operations.',
          ),
          const SizedBox(height: OpsSpacing.md),
          const _InfoTile(
            icon: Icons.sync_lock_rounded,
            title: 'Session persistence',
            description:
                'Successful login keeps the session locally so the ops dashboard can reopen without manual reconnect every time.',
          ),
        ],
      ),
    );
  }

  Widget _buildLoginPanel(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(OpsSpacing.xxl),
      decoration: OpsDecorations.panel(
        radius: OpsRadius.xxl,
        elevated: true,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Sign In',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: OpsSpacing.sm),
          const Text(
            'Use backend operations credentials to enter the admin console.',
            style: OpsTypography.body,
          ),
          const SizedBox(height: OpsSpacing.xl),
          _buildSectionLabel('Connection'),
          const SizedBox(height: OpsSpacing.md),
          TextField(
            controller: _baseUrlController,
            decoration: const InputDecoration(
              labelText: 'Backend Base URL',
              hintText: 'http://127.0.0.1:5000',
              prefixIcon: Icon(Icons.link_rounded),
            ),
          ),
          const SizedBox(height: OpsSpacing.lg),
          _buildSectionLabel('Credentials'),
          const SizedBox(height: OpsSpacing.md),
          TextField(
            controller: _mobileController,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Mobile',
              prefixIcon: Icon(Icons.phone_iphone_rounded),
            ),
          ),
          const SizedBox(height: OpsSpacing.md),
          TextField(
            controller: _passwordController,
            obscureText: _obscurePassword,
            decoration: InputDecoration(
              labelText: 'Password',
              prefixIcon: const Icon(Icons.lock_outline_rounded),
              suffixIcon: IconButton(
                onPressed: () {
                  setState(() => _obscurePassword = !_obscurePassword);
                },
                icon: Icon(
                  _obscurePassword
                      ? Icons.visibility_off_rounded
                      : Icons.visibility_rounded,
                ),
              ),
            ),
            onSubmitted: (_) {
              if (!_loading) {
                _login();
              }
            },
          ),
          if (_error != null) ...[
            const SizedBox(height: OpsSpacing.lg),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(OpsSpacing.lg),
              decoration: BoxDecoration(
                color: OpsUiTokens.errorSurface,
                borderRadius: BorderRadius.circular(OpsRadius.lg),
                border: Border.all(color: OpsUiTokens.errorBorder),
              ),
              child: Text(
                _error!,
                style: OpsTypography.body.copyWith(
                  color: OpsUiTokens.textPrimary,
                ),
              ),
            ),
          ],
          const SizedBox(height: OpsSpacing.xl),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _loading ? null : _login,
              icon: _loading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.login_rounded),
              label: Text(_loading ? 'Signing In...' : 'Enter Ops Console'),
            ),
          ),
          const SizedBox(height: OpsSpacing.lg),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(OpsSpacing.lg),
            decoration: BoxDecoration(
              color: OpsUiTokens.panelInfo,
              borderRadius: BorderRadius.circular(OpsRadius.lg),
              border: Border.all(color: OpsUiTokens.panelInfoBorder),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.info_outline_rounded,
                  size: 18,
                  color: OpsUiTokens.primarySoft,
                ),
                SizedBox(width: OpsSpacing.md),
                Expanded(
                  child: Text(
                    'If login fails, first verify the backend base URL and confirm the admin account exists in backend admin access management.',
                    style: OpsTypography.body,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionLabel(String label) {
    return Text(
      label.toUpperCase(),
      style: OpsTypography.caption.copyWith(
        color: OpsUiTokens.primarySoft,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _FeatureChip extends StatelessWidget {
  const _FeatureChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: OpsSpacing.lg,
        vertical: OpsSpacing.md,
      ),
      decoration: BoxDecoration(
        color: OpsUiTokens.textPrimary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: OpsUiTokens.primarySoft),
          const SizedBox(width: OpsSpacing.sm),
          Text(label),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: OpsSpacing.cardCompact,
      decoration: BoxDecoration(
        color: OpsUiTokens.textPrimary.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(OpsRadius.lg),
        border: Border.all(
          color: OpsUiTokens.textPrimary.withValues(alpha: 0.08),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(OpsSpacing.md),
            decoration: BoxDecoration(
              color: OpsUiTokens.panelIcon,
              borderRadius: BorderRadius.circular(OpsRadius.md),
            ),
            child: Icon(icon, color: OpsUiTokens.primarySoft, size: 18),
          ),
          const SizedBox(width: OpsSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: OpsTypography.subtitle.copyWith(
                    color: OpsUiTokens.textPrimary,
                  ),
                ),
                const SizedBox(height: OpsSpacing.xs),
                Text(
                  description,
                  style: OpsTypography.body,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
