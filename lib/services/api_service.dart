import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/api_models.dart';

/// Centralized API service for all backend communication.
class ApiService {
  static const String _prefCustomBaseUrl = 'api_custom_base_url';
  static String? _runtimeBaseUrl;

  static Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _runtimeBaseUrl = prefs.getString(_prefCustomBaseUrl);
  }

  static Future<void> setCustomBaseUrl(String? value) async {
    final prefs = await SharedPreferences.getInstance();
    final normalized = _normalizeUrl(value);
    _runtimeBaseUrl = normalized;
    if (normalized == null) {
      await prefs.remove(_prefCustomBaseUrl);
    } else {
      await prefs.setString(_prefCustomBaseUrl, normalized);
    }
  }

  static String? get customBaseUrl => _runtimeBaseUrl;

  static String? _normalizeUrl(String? value) {
    if (value == null) return null;
    final trimmed = value.trim();
    if (trimmed.isEmpty) return null;
    final hasScheme =
        trimmed.startsWith('http://') || trimmed.startsWith('https://');
    final isLocalLike = trimmed.startsWith('localhost') ||
        trimmed.startsWith('127.') ||
        trimmed.startsWith('10.') ||
        trimmed.startsWith('192.168.') ||
        RegExp(r'^172\.(1[6-9]|2\d|3[0-1])\.').hasMatch(trimmed);
    final withScheme =
        hasScheme ? trimmed : '${isLocalLike ? 'http' : 'https'}://$trimmed';
    final parsed = Uri.tryParse(withScheme);
    if (parsed == null || parsed.host.isEmpty) {
      return null;
    }
    // Keep only API root origin. This avoids bad values like /healthz in Settings.
    final origin = Uri(
      scheme: parsed.scheme,
      host: parsed.host,
      port: parsed.hasPort ? parsed.port : null,
    ).toString();
    return origin.endsWith('/')
        ? origin.substring(0, origin.length - 1)
        : origin;
  }

  static String get baseUrl {
    const envUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    // Runtime value from Settings must win so users can switch tunnel URLs
    // without rebuilding the app.
    if (_runtimeBaseUrl != null && _runtimeBaseUrl!.isNotEmpty) {
      return _runtimeBaseUrl!;
    }
    if (envUrl.isNotEmpty) {
      return envUrl;
    }
    if (Platform.isAndroid) {
      // Android emulator host loopback to local machine.
      return 'http://10.0.2.2:8000';
    }
    // iOS simulator local backend.
    return 'http://127.0.0.1:8000';
  }

  static String _extractError(http.Response response, String fallback) {
    try {
      final body = jsonDecode(response.body);
      if (body is Map<String, dynamic> && body['detail'] != null) {
        return body['detail'].toString();
      }
    } catch (_) {
      // Non-JSON error body
    }
    final raw = response.body.trimLeft();
    if (raw.startsWith('<html') || raw.startsWith('<!DOCTYPE html')) {
      return 'Backend returned HTML, not JSON. In Settings use only the root URL (e.g. https://<tunnel>.trycloudflare.com), not /healthz.';
    }
    return fallback;
  }

  static dynamic _decodeJsonOrThrow(http.Response response, String fallback) {
    if (response.statusCode != 200) {
      throw Exception(_extractError(response, fallback));
    }
    try {
      return jsonDecode(response.body);
    } on FormatException {
      final raw = response.body.trimLeft();
      if (raw.startsWith('<html') || raw.startsWith('<!DOCTYPE html')) {
        throw Exception(
          'Backend URL is incorrect. Use only root URL in Settings: https://<tunnel>.trycloudflare.com (no /healthz).',
        );
      }
      throw Exception(
          'Invalid server response. Please verify backend URL in Settings.');
    }
  }

  // ─── Users ───────────────────────────────────────────────

  static Future<User> register({
    required String name,
    required String email,
    required String password,
    String stylePreference = 'Minimal',
    String climateRegion = 'Tropical',
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/users/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'name': name,
            'email': email,
            'password': password,
            'style_preference': stylePreference,
            'climate_region': climateRegion,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Registration failed');
    return User.fromJson(body as Map<String, dynamic>);
  }

  static Future<User> login({
    required String email,
    required String password,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/users/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'email': email, 'password': password}),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Login failed');
    return User.fromJson(body as Map<String, dynamic>);
  }

  static Future<User> getUser(int userId) async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/users/$userId'))
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'User not found');
    return User.fromJson(body as Map<String, dynamic>);
  }

  static Future<User> updateUser({
    required int userId,
    String? name,
    String? stylePreference,
    String? climateRegion,
  }) async {
    final payload = <String, dynamic>{};
    if (name != null) payload['name'] = name;
    if (stylePreference != null) payload['style_preference'] = stylePreference;
    if (climateRegion != null) payload['climate_region'] = climateRegion;

    final response = await http
        .put(
          Uri.parse('$baseUrl/api/users/$userId'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to update profile');
    return User.fromJson(body as Map<String, dynamic>);
  }

  // ─── Body Profile ───────────────────────────────────────

  static Future<BodyProfile> saveBodyProfile({
    required int userId,
    required double heightCm,
    required double weightKg,
    required double shoulderCm,
    required double chestCm,
    required double waistCm,
    required double hipCm,
    required double inseamCm,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/body-profile/$userId'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'height_cm': heightCm,
            'weight_kg': weightKg,
            'shoulder_cm': shoulderCm,
            'chest_cm': chestCm,
            'waist_cm': waistCm,
            'hip_cm': hipCm,
            'inseam_cm': inseamCm,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Analysis failed');
    return BodyProfile.fromJson(body as Map<String, dynamic>);
  }

  static Future<BodyProfile?> getBodyProfile(int userId) async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/body-profile/$userId'))
        .timeout(const Duration(seconds: 20));
    if (response.statusCode == 404) return null;
    final body = _decodeJsonOrThrow(response, 'Failed to get profile');
    return BodyProfile.fromJson(body as Map<String, dynamic>);
  }

  static Future<Map<String, dynamic>> scanBody({
    required int userId,
    required File imageFile,
  }) async {
    final uri = Uri.parse('$baseUrl/api/body-profile/$userId/scan');
    final request = http.MultipartRequest('POST', uri);
    request.files
        .add(await http.MultipartFile.fromPath('file', imageFile.path));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    final body = _decodeJsonOrThrow(response, 'Scan failed');
    return body as Map<String, dynamic>;
  }

  static Future<BodyProfile> saveBodyProfileFromScan({
    required int userId,
    required Map<String, dynamic> scanResult,
    double estimatedHeightCm = 170.0,
    double estimatedWeightKg = 68.0,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/body-profile/$userId/scan-save'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'metrics': {
              'measurements': scanResult['measurements'] ?? scanResult['metrics'] ?? {},
              'ratios': scanResult['ratios'] ?? {},
            },
            'body_type': scanResult['body_type'] ?? 'rectangle',
            'symmetry': scanResult['symmetry'] ?? 0.0,
            'posture_angle': scanResult['posture_angle'] ?? 0.0,
            'estimated_height_cm': (scanResult['measurements']?['estimated_height_cm'] ?? estimatedHeightCm),
            'estimated_weight_kg': estimatedWeightKg,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to save scanned profile');
    return BodyProfile.fromJson(body as Map<String, dynamic>);
  }

  // ─── Wardrobe ────────────────────────────────────────────

  static Future<WardrobeItem> addWardrobeItem({
    required int userId,
    required String category,
    required String color,
    required String formality,
    String? name,
    String? fabric,
    File? imageFile,
  }) async {
    final uri = Uri.parse('$baseUrl/api/wardrobe/$userId');
    final request = http.MultipartRequest('POST', uri);

    request.fields['category'] = category;
    request.fields['color'] = color;
    request.fields['formality'] = formality;
    if (name != null) request.fields['name'] = name;
    if (fabric != null) request.fields['fabric'] = fabric;

    if (imageFile != null) {
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    final body = _decodeJsonOrThrow(response, 'Failed to add item');
    return WardrobeItem.fromJson(body as Map<String, dynamic>);
  }

  static Future<List<WardrobeItem>> getWardrobe(int userId) async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/wardrobe/$userId'))
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to get wardrobe');
    final list = body as List;
    return list.map((j) => WardrobeItem.fromJson(j)).toList();
  }

  static Future<WardrobeStatsModel> getWardrobeStats(int userId) async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/wardrobe/$userId/stats'))
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to fetch wardrobe stats');
    return WardrobeStatsModel.fromJson(body as Map<String, dynamic>);
  }

  static Future<void> deleteWardrobeItem(int itemId) async {
    final response = await http
        .delete(Uri.parse('$baseUrl/api/wardrobe/item/$itemId'))
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) {
      throw Exception(_extractError(response, 'Failed to delete item'));
    }
  }

  static Future<WardrobeItem> updateWardrobeItem({
    required int itemId,
    String? name,
    required String category,
    required String color,
    String? fabric,
    required String formality,
  }) async {
    final response = await http
        .put(
          Uri.parse('$baseUrl/api/wardrobe/item/$itemId'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'name': name,
            'category': category,
            'color': color,
            'fabric': fabric,
            'formality': formality,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to update item');
    return WardrobeItem.fromJson(body as Map<String, dynamic>);
  }

  // ─── Recommendations ────────────────────────────────────

  static Future<RecommendationResponse> getRecommendations({
    required int userId,
    required String occasion,
    String? mood,
    String? climate,
    String? additionalNotes,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/recommendations/$userId'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'occasion': occasion,
            'mood': mood,
            'climate': climate,
            'additional_notes': additionalNotes,
          }),
        )
        .timeout(const Duration(seconds: 30));
    final body = _decodeJsonOrThrow(response, 'Recommendation failed');
    return RecommendationResponse.fromJson(body as Map<String, dynamic>);
  }

  // ─── Chat ───────────────────────────────────────────────

  static Future<ChatApiResponse> sendChatMessage({
    required int userId,
    required String message,
    Map<String, dynamic>? context,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/chat/$userId'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'message': message,
            'context': context,
          }),
        )
        .timeout(const Duration(seconds: 30));
    final body = _decodeJsonOrThrow(response, 'Chat failed');
    return ChatApiResponse.fromJson(body as Map<String, dynamic>);
  }

  static Future<List<Map<String, dynamic>>> getChatHistory(int userId) async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/chat/$userId/history'))
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to get history');
    return List<Map<String, dynamic>>.from(body);
  }

  // ─── Preferences ─────────────────────────────────────────

  static Future<UserPreferences> getPreferences(int userId) async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/preferences/$userId'))
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to fetch preferences');
    return UserPreferences.fromJson(body as Map<String, dynamic>);
  }

  static Future<UserPreferences> updatePreferences({
    required int userId,
    List<String>? preferredColors,
    List<String>? dislikedColors,
    List<String>? preferredStyles,
    String? preferredFormality,
    double? comfortPriority,
    double? confidencePriority,
  }) async {
    final payload = <String, dynamic>{};
    if (preferredColors != null) payload['preferred_colors'] = preferredColors;
    if (dislikedColors != null) payload['disliked_colors'] = dislikedColors;
    if (preferredStyles != null) payload['preferred_styles'] = preferredStyles;
    if (preferredFormality != null) {
      payload['preferred_formality'] = preferredFormality;
    }
    if (comfortPriority != null) payload['comfort_priority'] = comfortPriority;
    if (confidencePriority != null) {
      payload['confidence_priority'] = confidencePriority;
    }

    final response = await http
        .put(
          Uri.parse('$baseUrl/api/preferences/$userId'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decodeJsonOrThrow(response, 'Failed to update preferences');
    return UserPreferences.fromJson(body as Map<String, dynamic>);
  }

  // ─── Connectivity ────────────────────────────────────────

  static Future<Map<String, dynamic>> checkBackendHealth() async {
    final response = await http
        .get(Uri.parse('$baseUrl/healthz'))
        .timeout(const Duration(seconds: 8));
    final body = _decodeJsonOrThrow(response, 'Backend health check failed');
    return body as Map<String, dynamic>;
  }
}
