import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:provider/provider.dart';
import '../../config/api_config.dart';
import '../../providers/user_provider.dart';
import '../../routing/app_router.dart';

class BodyScanScreen extends StatefulWidget {
  const BodyScanScreen({super.key});

  @override
  State<BodyScanScreen> createState() => _BodyScanScreenState();
}

class _BodyScanScreenState extends State<BodyScanScreen> {
  XFile? _selectedImage;
  bool _isAnalyzing = false;
  Map<String, dynamic>? _results;
  String? _errorMessage;
  final ImagePicker _picker = ImagePicker();

  Future<void> _pickFromCamera() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
        preferredCameraDevice: CameraDevice.rear,
      );
      if (image != null) {
        setState(() {
          _selectedImage = image;
          _results = null;
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = 
        'Camera error: ${e.toString()}');
    }
  }

  Future<void> _pickFromGallery() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 85,
      );
      if (image != null) {
        setState(() {
          _selectedImage = image;
          _results = null;
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = 
        'Gallery error: ${e.toString()}');
    }
  }

  Future<void> _analyzeBody() async {
    if (_selectedImage == null) return;
    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
      _results = null;
    });

    try {
      final userProvider = context.read<UserProvider>();
      final userId = userProvider.isLoggedIn ? userProvider.userId.toString() : 'demo';
      
      final uri = Uri.parse('${ApiConfig.bodyProfileScan}/$userId/scan');
      
      final request = http.MultipartRequest('POST', uri);
      
      if (kIsWeb) {
        final bytes = await _selectedImage!.readAsBytes();
        request.files.add(http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: 'body_scan.jpg',
          contentType: MediaType('image', 'jpeg'),
        ));
      } else {
        request.files.add(await http.MultipartFile.fromPath(
          'file',
          _selectedImage!.path,
          contentType: MediaType('image', 'jpeg'),
        ));
      }

      final streamed = await request.send()
        .timeout(const Duration(seconds: 45));
      final response = 
        await http.Response.fromStream(streamed);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && 
          data['success'] == true) {
        setState(() {
          _results = data;
          _isAnalyzing = false;
        });
      } else {
        setState(() {
          _errorMessage = data['message'] ?? 
            data['error'] ?? 'Analysis failed';
          _isAnalyzing = false;
        });
      }
    } on SocketException {
      setState(() {
        _isAnalyzing = false;
        _errorMessage = 
          'Cannot connect to server.\n'
          'Make sure to update IP address in api_config.dart for physical devices.\n'
          'Ensure backend is running on port 8000.';
      });
    } catch (e) {
      setState(() {
        _isAnalyzing = false;
        _errorMessage = 'Error: ${e.toString()}';
      });
    }
  }

  Widget _buildImagePreview() {
    if (_selectedImage == null) {
      return Container(
        height: 280,
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.person_outline, 
              size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text('No image selected',
              style: TextStyle(color: Colors.grey.shade500)),
            const SizedBox(height: 4),
            Text(
              'Use a full-body photo for best results',
              style: TextStyle(
                color: Colors.grey.shade400, fontSize: 12),
            ),
          ],
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: SizedBox(
        height: 280,
        width: double.infinity,
        child: kIsWeb
          ? Image.network(
              _selectedImage!.path,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) =>
                const Icon(Icons.broken_image, size: 64),
            )
          : Image.file(
              File(_selectedImage!.path),
              fit: BoxFit.cover,
            ),
      ),
    );
  }

  Widget _buildResults() {
    if (_results == null) return const SizedBox.shrink();

    final measurements = 
      _results!['measurements'] as Map<String, dynamic>;
    final bodyType = _results!['body_type'] ?? 'Unknown';
    final description = _results!['body_description'] ?? '';
    final tips = List<String>.from(
      _results!['styling_tips'] ?? []);
    final confidence = _results!['confidence'] ?? 0;
    final ratio = _results!['shoulder_hip_ratio'] ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 24),
        
        // Body Type Card
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.black,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              Text('Your Body Type',
                style: TextStyle(
                  color: Colors.white70, fontSize: 13)),
              const SizedBox(height: 8),
              Text(bodyType,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Text(description,
                style: TextStyle(
                  color: Colors.white60, fontSize: 13)),
              const SizedBox(height: 8),
              Text('Confidence: $confidence%',
                style: TextStyle(
                  color: Colors.white38, fontSize: 11)),
            ],
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Measurements Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.grey.shade50,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.grey.shade200),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Measurements',
                style: TextStyle(
                  fontWeight: FontWeight.bold, fontSize: 16)),
              const SizedBox(height: 12),
              _measurementRow('Shoulder Width', 
                '${measurements['shoulder_width_cm']} cm'),
              _measurementRow('Hip Width', 
                '${measurements['hip_width_cm']} cm'),
              _measurementRow('Torso Length', 
                '${measurements['torso_length_cm']} cm'),
              _measurementRow('Leg Length', 
                '${measurements['leg_length_cm']} cm'),
              _measurementRow('Arm Length', 
                '${measurements['arm_length_cm']} cm'),
              _measurementRow('Est. Height', 
                '${measurements['estimated_height_cm']} cm'),
              _measurementRow('Shoulder/Hip Ratio', 
                ratio.toString()),
            ],
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Styling Tips Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.amber.shade50,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.amber.shade200),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(Icons.auto_awesome, 
                  color: Colors.amber.shade700, size: 18),
                const SizedBox(width: 8),
                const Text('Styling Tips',
                  style: TextStyle(
                    fontWeight: FontWeight.bold, 
                    fontSize: 16)),
              ]),
              const SizedBox(height: 12),
              ...tips.map((tip) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• ', 
                      style: TextStyle(fontSize: 14)),
                    Flexible(child: Text(tip,
                      style: const TextStyle(fontSize: 13))),
                  ],
                ),
              )),
            ],
          ),
        ),
        
        const SizedBox(height: 20),
        
        // Save button
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: _saveToProfile,
            icon: const Icon(Icons.save_outlined),
            label: const Text('Save to Profile'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.black,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
        
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _measurementRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, 
            style: TextStyle(color: Colors.grey.shade600,
              fontSize: 13)),
          Text(value,
            style: const TextStyle(
              fontWeight: FontWeight.w600, fontSize: 13)),
        ],
      ),
    );
  }

  Future<void> _saveToProfile() async {
    if (_results == null) return;
    // Save results to SharedPreferences or your local DB
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Body profile saved! '),
        backgroundColor: Colors.green,
      ),
    );
    Navigator.pop(context, _results);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Body Scan'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Instructions
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, 
                    color: Colors.blue.shade700, size: 18),
                  const SizedBox(width: 8),
                  const Flexible(
                    child: Text(
                      'Stand straight, facing camera, '
                      'full body visible in frame.',
                      style: TextStyle(fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Image preview
            _buildImagePreview(),
            
            const SizedBox(height: 16),
            
            // Pick image buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isAnalyzing 
                      ? null : _pickFromCamera,
                    icon: const Icon(Icons.camera_alt_outlined),
                    label: const Text('Take Photo'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isAnalyzing 
                      ? null : _pickFromGallery,
                    icon: const Icon(Icons.photo_library_outlined),
                    label: const Text('Gallery'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Analyze button
            if (_selectedImage != null)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isAnalyzing ? null : _analyzeBody,
                  icon: _isAnalyzing
                    ? const SizedBox(
                        width:16, height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white))
                    : const Icon(Icons.analytics_outlined),
                  label: Text(_isAnalyzing 
                    ? 'Analyzing...' : 'Analyze Body'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.black,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            
            // Error message
            if (_errorMessage != null)
              Container(
                margin: const EdgeInsets.only(top: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: Colors.red.shade200),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.error_outline, 
                      color: Colors.red.shade700, size: 18),
                    const SizedBox(width: 8),
                    Flexible(child: Text(_errorMessage!,
                      style: TextStyle(
                        color: Colors.red.shade700,
                        fontSize: 13))),
                  ],
                ),
              ),
            
            // Results
            _buildResults(),
          ],
        ),
      ),
    );
  }
}
