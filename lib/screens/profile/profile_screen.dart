import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:my_flutter_app/design/app_spacing.dart';
import 'package:my_flutter_app/design/app_typography.dart';
import 'package:my_flutter_app/design/app_colors.dart';
import 'package:my_flutter_app/models/api_models.dart';
import 'package:my_flutter_app/providers/body_metric_provider.dart';
import 'package:my_flutter_app/providers/user_provider.dart';
import 'package:my_flutter_app/providers/wardrobe_provider.dart';
import 'package:my_flutter_app/routing/app_router.dart';
import 'package:my_flutter_app/services/api_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  UserPreferences? _preferences;
  WardrobeStatsModel? _wardrobeStats;
  bool _loadingExtras = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  Future<void> _loadData() async {
    final user = context.read<UserProvider>().user;
    if (user == null) return;

    setState(() => _loadingExtras = true);

    await context.read<UserProvider>().refreshUser();
    await context.read<WardrobeProvider>().loadWardrobe(user.id);
    await context.read<BodyMetricProvider>().loadProfile(user.id);

    try {
      final results = await Future.wait([
        ApiService.getPreferences(user.id),
        ApiService.getWardrobeStats(user.id),
      ]);
      if (!mounted) return;
      setState(() {
        _preferences = results[0] as UserPreferences;
        _wardrobeStats = results[1] as WardrobeStatsModel;
      });
    } catch (_) {
      // Keep screen usable even if extra data fails.
    }

    if (mounted) {
      setState(() => _loadingExtras = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<UserProvider>().user;
    final bodyProfile = context.watch<BodyMetricProvider>().profile;
    final wardrobeItems = context.watch<WardrobeProvider>().items;

    final initials = (user?.name.isNotEmpty ?? false)
        ? user!.name.trim().substring(0, 1).toUpperCase()
        : 'U';

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadData,
          child: Padding(
            padding: AppSpacing.screenPadding,
            child: ListView(
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    radius: 24,
                    backgroundColor: AppColors.accentLavender,
                    child: Text(initials,
                        style: AppTypography.subheading(context)),
                  ),
                  title: Text(user?.name ?? 'User',
                      style: AppTypography.subheading(context)),
                  subtitle: Text(
                    user == null
                        ? 'Not signed in'
                        : '${user.stylePreference} • ${user.climateRegion} climate',
                    style: AppTypography.body(context),
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),
                Text('Body Blueprint', style: AppTypography.label(context)),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  bodyProfile == null
                      ? 'Not yet scanned'
                      : '${bodyProfile.bodyType} • BMI ${bodyProfile.bmi.toStringAsFixed(1)} (${bodyProfile.bmiCategory})',
                  style: AppTypography.body(context),
                ),
                if (bodyProfile != null) ...[
                  const SizedBox(height: 4),
                  Text(bodyProfile.proportionSummary,
                      style: AppTypography.label(context)),
                  const SizedBox(height: 4),
                  Text(
                    'H ${bodyProfile.heightCm.toStringAsFixed(1)} cm • '
                    'Shoulder ${bodyProfile.shoulderCm.toStringAsFixed(1)} cm • '
                    'Waist ${bodyProfile.waistCm.toStringAsFixed(1)} cm • '
                    'Hip ${bodyProfile.hipCm.toStringAsFixed(1)} cm',
                    style: AppTypography.label(context),
                  ),
                ],
                const SizedBox(height: AppSpacing.lg),
                Text('Wardrobe Efficiency',
                    style: AppTypography.label(context)),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _wardrobeStats == null
                      ? '${wardrobeItems.length} items in your closet'
                      : '${_wardrobeStats!.totalItems} items • ${_wardrobeStats!.categoryBreakdown.length} categories',
                  style: AppTypography.body(context),
                ),
                const SizedBox(height: AppSpacing.lg),
                Text('Saved Outfits', style: AppTypography.label(context)),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Recommendations update dynamically from your latest closet data.',
                  style: AppTypography.body(context),
                ),
                const SizedBox(height: AppSpacing.lg),
                Text('Preferences', style: AppTypography.label(context)),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _preferences == null
                      ? 'Preferences are learned from chat and feedback.'
                      : 'Preferred colors: ${_preferences!.preferredColors.isEmpty ? 'Not set' : _preferences!.preferredColors.join(', ')}',
                  style: AppTypography.body(context),
                ),
                if (_preferences != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Comfort ${_preferences!.comfortPriority.toStringAsFixed(2)} • Confidence ${_preferences!.confidencePriority.toStringAsFixed(2)}',
                    style: AppTypography.label(context),
                  ),
                ],
                const SizedBox(height: AppSpacing.xl),
                Text('Settings', style: AppTypography.label(context)),
                const SizedBox(height: AppSpacing.sm),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('Account & Backend',
                      style: AppTypography.body(context)),
                  trailing: _loadingExtras
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.chevron_right_rounded),
                  onTap: () => Navigator.pushNamed(context, AppRoutes.settings),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('Re-run Body Scan',
                      style: AppTypography.body(context)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => Navigator.pushNamed(context, AppRoutes.bodyScan),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
