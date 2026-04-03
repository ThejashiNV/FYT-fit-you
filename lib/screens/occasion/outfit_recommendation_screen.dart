import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../widgets/fyt_button.dart';
import '../../design/app_colors.dart';
import '../../design/app_spacing.dart';
import '../../design/app_typography.dart';
import '../../routing/app_router.dart';
import '../../providers/recommendation_provider.dart';
import '../../models/api_models.dart';

class OutfitRecommendationScreen extends StatefulWidget {
  const OutfitRecommendationScreen({super.key});

  @override
  State<OutfitRecommendationScreen> createState() =>
      _OutfitRecommendationScreenState();
}

class _OutfitRecommendationScreenState
    extends State<OutfitRecommendationScreen> {
  int _currentOutfitIndex = 0;

  double? _readScore(Map<String, dynamic> scores, List<String> keys) {
    for (final key in keys) {
      final v = scores[key];
      if (v is num) return v.toDouble();
      if (v is String) {
        final parsed = double.tryParse(v);
        if (parsed != null) return parsed;
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final recProvider = context.watch<RecommendationProvider>();
    final rec = recProvider.recommendation;

    if (rec == null || rec.outfits.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Outfit')),
        body: Center(
          child: Padding(
            padding: AppSpacing.screenPadding,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.warning_amber_rounded,
                    size: 64, color: AppColors.textSub),
                const SizedBox(height: AppSpacing.md),
                Text('No outfits could be generated.',
                    style: AppTypography.subheading(context)),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'Add more items to your wardrobe for better recommendations.',
                  style: AppTypography.body(context),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.xl),
                FytButton(
                  label: 'Go to Smart Closet',
                  onPressed: () =>
                      Navigator.pushNamed(context, AppRoutes.smartCloset),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final outfit = rec.outfits[_currentOutfitIndex];

    return Scaffold(
      appBar: AppBar(
        title: Text('${rec.occasion} Look'),
        actions: [
          if (rec.outfits.length > 1)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  '${_currentOutfitIndex + 1}/${rec.outfits.length}',
                  style: AppTypography.label(context),
                ),
              ),
            ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: AppSpacing.screenPadding,
          child: ListView(
            children: [
              // Outfit items display
              Container(
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.bgSecondary,
                  borderRadius:
                      BorderRadius.circular(AppSpacing.cornerRadiusCard),
                ),
                child: Column(
                  children: [
                    Text('Outfit #${outfit.rank}',
                        style: AppTypography.subheading(context)),
                    const SizedBox(height: AppSpacing.md),
                    ...outfit.items.map((item) => _outfitItemRow(context, item)),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // Scores
              Row(
                children: [
                  _ScoreBadge(
                    label: 'Suitability',
                    value: (() {
                      final s = _readScore(outfit.scores, const [
                        'suitability_score',
                        'appropriateness',
                        'keyword_relevance',
                      ]);
                      return s == null ? '—' : '${s.toStringAsFixed(0)}%';
                    })(),
                    color: AppColors.successSoft,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  _ScoreBadge(
                    label: 'Confidence',
                    value: (() {
                      final s = _readScore(outfit.scores, const [
                        'confidence',
                        'confidence_score',
                        'preference_alignment',
                      ]);
                      return s == null ? '—' : '${s.toStringAsFixed(0)}%';
                    })(),
                    color: AppColors.accentLavender.withOpacity(0.3),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  _ScoreBadge(
                    label: 'Comfort',
                    value: (() {
                      final s = _readScore(outfit.scores, const [
                        'comfort',
                        'formality_match',
                        'color_compatibility',
                      ]);
                      return s == null ? '—' : '${s.toStringAsFixed(0)}%';
                    })(),
                    color: AppColors.warningSoft,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.lg),

              // Why it works
              Text('Why it works', style: AppTypography.subheading(context)),
              const SizedBox(height: AppSpacing.sm),
              ...outfit.explanation
                  .map((e) => _bullet(context, e)),
              const SizedBox(height: AppSpacing.xl),

              // Actions
              FytButton(
                label: 'Ask Stylist',
                onPressed: () =>
                    Navigator.pushNamed(context, AppRoutes.aiChat),
              ),
              const SizedBox(height: AppSpacing.sm),
              if (rec.outfits.length > 1)
                FytButton(
                  label: 'Try Alternative',
                  primary: false,
                  onPressed: () {
                    setState(() {
                      _currentOutfitIndex =
                          (_currentOutfitIndex + 1) % rec.outfits.length;
                    });
                  },
                ),
              const SizedBox(height: AppSpacing.sm),
              FytButton(
                label: 'Back to Home',
                primary: false,
                onPressed: () => Navigator.popUntil(
                  context,
                  ModalRoute.withName(AppRoutes.home),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _outfitItemRow(BuildContext context, OutfitItem item) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.accentLavender.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              item.category == 'Top'
                  ? Icons.dry_cleaning_rounded
                  : item.category == 'Bottom'
                      ? Icons.straighten_rounded
                      : item.category == 'Outerwear'
                          ? Icons.layers_rounded
                          : Icons.checkroom_rounded,
              size: 20,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name ?? item.category,
                    style: AppTypography.body(context)
                        .copyWith(fontWeight: FontWeight.w500)),
                Text('${item.color} • ${item.formality}',
                    style: AppTypography.label(context)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _bullet(BuildContext context, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('•  '),
          Expanded(child: Text(text, style: AppTypography.body(context))),
        ],
      ),
    );
  }
}

class _ScoreBadge extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _ScoreBadge({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: AppSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          children: [
            Text(label, style: AppTypography.label(context)),
            const SizedBox(height: 4),
            Text(value, style: AppTypography.subheading(context)),
          ],
        ),
      ),
    );
  }
}
