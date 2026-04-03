class ApiConfig {
  // Cloudflare tunnel URL for testing on physical devices
  static const String baseUrl = 'https://exhibitions-commercial-states-advisory.trycloudflare.com';
  
  // For local testing (if tunnel is not available):
  // static const String baseUrl = 'http://192.168.119.220:8000';
  // For emulator: static const String baseUrl = 'http://10.0.2.2:8000';
  
  static const String bodyProfileScan = 
    '$baseUrl/api/body-profile';
}
