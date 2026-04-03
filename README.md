# FYT - Fit You (AI Personal Styling Application)

FYT is an AI-powered personal styling mobile application that provides personalized fashion recommendations based on body metrics, user preferences, wardrobe items, and occasions using advanced computer vision and machine learning techniques.

## Features

- **AI Body Analysis**: Use MediaPipe to analyze body measurements from photos
- **Smart Wardrobe Management**: Digital closet organization and tracking
- **Personalized Recommendations**: AI-powered outfit suggestions
- **AI Stylist Chat**: Conversational fashion advice
- **Body Type Classification**: Automatic body type detection with styling tips

## Running Body Metric Module

### Prerequisites

- Flutter SDK
- Python 3.8+
- Android Studio/VS Code
- Android device or emulator

### Start the Backend Server

First, navigate to the backend directory and install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

Start the FastAPI server:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`

### Backend Configuration

The backend uses the following technologies:
- **FastAPI**: Web framework
- **MediaPipe**: Body pose detection
- **OpenCV**: Image processing
- **SQLite**: Database (compatible with MySQL)

### API Endpoints

- `POST /api/body-profile/{user_id}/scan` - Analyze body image
- `GET /api/body-profile/{user_id}` - Get saved body profile
- `GET /healthz` - Health check

### Flutter App Configuration

#### For Android Emulator:
- The app is pre-configured to use `http://10.0.2.2:8000` (emulator host loopback)
- Run: `flutter run`

#### For Physical Android Device:
1. Find your PC's IP address:
   ```bash
   # On Windows
   ipconfig
   # Look for "IPv4 Address" under your WiFi adapter (e.g. 192.168.1.X)
   ```
2. Update `lib/config/api_config.dart`:
   ```dart
   static const String baseUrl = 'http://YOUR_PC_IP:8000';
   ```
3. Ensure your phone and PC are on the same WiFi network
4. Run: `flutter run`

### Testing the Body Analysis

1. Start the backend server first
2. Run the Flutter app
3. Navigate to **Body Blueprint** → **Body Scan**
4. Take a photo or upload from gallery
5. Tap **Analyze Body**
6. View results with:
   - Body type classification
   - Body measurements (shoulder, hip, torso, leg, arm length, height)
   - Shoulder-hip ratio
   - Personalized styling tips
   - Detection confidence

### Android Permissions

The app requires these permissions (already configured in `android/app/src/main/AndroidManifest.xml`):
- `android.permission.INTERNET` - Network access
- `android.permission.CAMERA` - Camera access for body photos
- `android.permission.READ_EXTERNAL_STORAGE` - Gallery access
- `android.permission.READ_MEDIA_IMAGES` - Modern image access
- `android:usesCleartextTraffic="true"` - Allow HTTP for local backend

### Troubleshooting

#### Backend Issues:
```bash
# Test backend directly
curl -X POST http://localhost:8000/api/body-profile/test/scan -F "file=@/path/to/photo.jpg"
```

#### Connection Issues:
- Ensure backend is running on port 8000
- Check firewall settings
- Verify IP configuration for physical devices
- Make sure device and PC are on same network

#### MediaPipe Issues:
- Install required packages: `pip install mediapipe opencv-python`
- Use clear, full-body photos with good lighting
- Ensure person is standing straight facing the camera

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── body_metric_module.py   # MediaPipe body analysis
│   ├── routers/
│   │   └── body_profile.py     # API endpoints
│   └── requirements.txt        # Python dependencies
├── lib/
│   ├── config/
│   │   └── api_config.dart      # Backend URL configuration
│   ├── screens/body_blueprint/
│   │   ├── body_scan_screen.dart        # Photo capture & upload
│   │   └── body_profile_result_screen.dart # Results display
│   ├── services/api_service.dart         # HTTP client
│   └── providers/body_metric_provider.dart # State management
└── android/app/src/main/AndroidManifest.xml # Permissions
```

## Technology Stack

**Backend (Python)**:
- FastAPI + Uvicorn
- MediaPipe (pose detection)
- OpenCV (image processing)
- SQLite/SQLAlchemy (database)

**Frontend (Flutter)**:
- Dart & Flutter
- Provider (state management)
- Image Picker (camera/gallery)
- HTTP (API communication)

## Development

To modify the body analysis logic:
1. Edit `backend/body_metric_module.py`
2. Update measurement calculations or body type classification
3. Restart the backend server

To modify the UI:
1. Edit `lib/screens/body_blueprint/body_scan_screen.dart` (capture flow)
2. Edit `lib/screens/body_blueprint/body_profile_result_screen.dart` (results display)

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.