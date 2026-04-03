import 'package:flutter/material.dart';
import '../../design/app_spacing.dart';
import '../../design/app_typography.dart';
import '../../routing/app_router.dart';

class BodyProfileResultScreen extends StatelessWidget {
  const BodyProfileResultScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments;
    
    // Handle new API response format
    if (args is Map<String, dynamic>) {
      return _buildNewResults(context, args);
    }
    
    // Fallback to old format if needed
    return _buildFallbackResults(context);
  }

  Widget _buildNewResults(BuildContext context, Map<String, dynamic> data) {
    final bodyType = data['body_type'] ?? 'Unknown';
    final bodyDescription = data['body_description'] ?? '';
    final measurements = data['measurements'] as Map<String, dynamic>? ?? {};
    final shoulderHipRatio = data['shoulder_hip_ratio']?.toString() ?? '0';
    final stylingTips = (data['styling_tips'] as List<dynamic>?) ?? [];
    final confidence = data['confidence']?.toString() ?? '0';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Your Body Analysis'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: AppSpacing.screenPadding,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Body Type - Large and prominent
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Colors.blue.shade400, Colors.purple.shade400],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    const Text(
                      'Your Body Type',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      bodyType,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      bodyDescription,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 14,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Measurements Table
              Text(
                'Body Measurements',
                style: AppTypography.subheading(context),
              ),
              const SizedBox(height: AppSpacing.sm),
              
              Container(
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  children: [
                    _buildMeasurementRow('Shoulder Width', '${measurements['shoulder_width_cm'] ?? 0} cm'),
                    _buildDivider(),
                    _buildMeasurementRow('Hip Width', '${measurements['hip_width_cm'] ?? 0} cm'),
                    _buildDivider(),
                    _buildMeasurementRow('Torso Length', '${measurements['torso_length_cm'] ?? 0} cm'),
                    _buildDivider(),
                    _buildMeasurementRow('Leg Length', '${measurements['leg_length_cm'] ?? 0} cm'),
                    _buildDivider(),
                    _buildMeasurementRow('Arm Length', '${measurements['arm_length_cm'] ?? 0} cm'),
                    _buildDivider(),
                    _buildMeasurementRow('Est. Height', '${measurements['estimated_height_cm'] ?? 0} cm'),
                  ],
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Ratios
              Text(
                'Body Proportions',
                style: AppTypography.subheading(context),
              ),
              const SizedBox(height: AppSpacing.sm),
              
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Shoulder-Hip Ratio',
                      style: TextStyle(fontWeight: FontWeight.w500),
                    ),
                    Text(
                      shoulderHipRatio,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Styling Tips
              Text(
                'Personalized Styling Tips',
                style: AppTypography.subheading(context),
              ),
              const SizedBox(height: AppSpacing.sm),
              
              Container(
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: stylingTips.map<Widget>((tip) => Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: Colors.green.shade400,
                            shape: BoxShape.circle,
                          ),
                          margin: const EdgeInsets.only(top: 6),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            tip.toString(),
                            style: const TextStyle(fontSize: 14),
                          ),
                        ),
                      ],
                    ),
                  )).toList(),
                ),
              ),
              
              const SizedBox(height: AppSpacing.lg),
              
              // Detection Confidence
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.orange.shade600),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Detection Confidence: ${confidence}%',
                        style: TextStyle(
                          color: Colors.orange.shade800,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: AppSpacing.xl),
              
              // Action Buttons
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pushNamed(context, AppRoutes.smartCloset);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: const Text('Save to Profile'),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () {
                        Navigator.popUntil(context, (route) => route.settings.name == AppRoutes.bodyScan);
                      },
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.blue,
                        side: const BorderSide(color: Colors.blue),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: const Text('Retake Photo'),
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: AppSpacing.lg),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMeasurementRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDivider() {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 16),
      child: Divider(height: 1),
    );
  }

  Widget _buildFallbackResults(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Body Analysis')),
      body: const Center(
        child: Text('No analysis results available'),
      ),
    );
  }
}
