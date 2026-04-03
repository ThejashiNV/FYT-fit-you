import cv2
import mediapipe as mp
import numpy as np
import math
import os
import urllib.request


def _resolve_pose_class():
    """
    Resolve MediaPipe Pose class across packaging variants.
    Some builds expose `mediapipe.solutions`, others only
    `mediapipe.python.solutions`.
    """
    try:
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "pose"):
            return mp.solutions.pose.Pose
    except Exception:
        pass
    try:
        from mediapipe.python.solutions.pose import Pose  # type: ignore
        return Pose
    except Exception:
        return None


def _ensure_pose_task_model() -> str:
    """
    Ensure pose landmarker model exists locally for MediaPipe Tasks API.
    """
    model_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "pose_landmarker_full.task")
    if os.path.exists(model_path):
        return model_path

    model_url = (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
    )
    urllib.request.urlretrieve(model_url, model_path)
    return model_path


def _run_pose_tasks(img_rgb: np.ndarray):
    """
    Run MediaPipe Tasks pose detection for tasks-only mediapipe builds.
    Returns list of landmarks (x,y,visibility-like).
    """
    try:
        from mediapipe.tasks import python as mp_python  # type: ignore
        from mediapipe.tasks.python import vision  # type: ignore
    except Exception:
        return None

    try:
        model_path = _ensure_pose_task_model()
    except Exception as e:
        raise RuntimeError(
            "MediaPipe Tasks model download failed. Keep internet on once "
            "and retry scan so pose_landmarker_full.task can be cached locally."
        ) from e
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    with vision.PoseLandmarker.create_from_options(options) as detector:
        result = detector.detect(mp_image)
    if not result or not result.pose_landmarks:
        return None
    return result.pose_landmarks[0]


def analyze_body_from_image(image_bytes: bytes) -> dict:
    """
    Analyze body metrics from image bytes using MediaPipe Pose.
    Returns detailed measurements and body type classification.
    """
    try:
        print("Decoding image...")
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {
                "error": "Could not decode image",
                "message": "Please try a different image format (JPG or PNG)."
            }

        img_height, img_width = img.shape[:2]
        print(f"Image size: {img_width}x{img_height}")
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        print("Running MediaPipe Pose detection...")

        PoseClass = _resolve_pose_class()
        lm = None
        if PoseClass is not None:
            with PoseClass(
                static_image_mode=True,
                model_complexity=2,
                enable_segmentation=False,
                min_detection_confidence=0.5
            ) as pose:
                results = pose.process(img_rgb)
                if results and results.pose_landmarks:
                    lm = results.pose_landmarks.landmark
        else:
            print("MediaPipe Solutions API not found, trying Tasks API fallback...")
            lm = _run_pose_tasks(img_rgb)

        if not lm:
            print("No pose landmarks detected.")
            return {
                "error": "No person detected",
                "message": (
                    "Could not detect a person in the image. "
                    "Please use a clear full-body photo with: "
                    "good lighting, plain background, "
                    "standing straight facing the camera, "
                    "full body visible from head to toe."
                )
            }

        print("Pose landmarks detected successfully!")

        def get_point(idx):
            l = lm[idx]
            return np.array([l.x * img_width, l.y * img_height])

        def dist(p1, p2):
            return math.sqrt(
                (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
            )

        # MediaPipe Pose landmark indices
        # 0=nose, 11=left_shoulder, 12=right_shoulder
        # 13=left_elbow, 14=right_elbow
        # 15=left_wrist, 16=right_wrist
        # 23=left_hip, 24=right_hip
        # 25=left_knee, 26=right_knee
        # 27=left_ankle, 28=right_ankle
        # 31=left_foot_index, 32=right_foot_index

        nose           = get_point(0)
        left_shoulder  = get_point(11)
        right_shoulder = get_point(12)
        left_elbow     = get_point(13)
        right_elbow    = get_point(14)
        left_wrist     = get_point(15)
        right_wrist    = get_point(16)
        left_hip       = get_point(23)
        right_hip      = get_point(24)
        left_knee      = get_point(25)
        right_knee     = get_point(26)
        left_ankle     = get_point(27)
        right_ankle    = get_point(28)

        # Midpoints
        mid_shoulder = (left_shoulder + right_shoulder) / 2
        mid_hip      = (left_hip + right_hip) / 2
        mid_ankle    = (left_ankle + right_ankle) / 2
        mid_knee     = (left_knee + right_knee) / 2

        # Pixel distances
        shoulder_px  = dist(left_shoulder, right_shoulder)
        hip_px       = dist(left_hip, right_hip)
        torso_px     = dist(mid_shoulder, mid_hip)
        left_leg_px  = dist(left_hip, left_ankle)
        right_leg_px = dist(right_hip, right_ankle)
        leg_px       = (left_leg_px + right_leg_px) / 2
        left_arm_px  = dist(left_shoulder, left_wrist)
        right_arm_px = dist(right_shoulder, right_wrist)
        arm_px       = (left_arm_px + right_arm_px) / 2
        thigh_px     = dist(mid_hip, mid_knee)
        height_px    = dist(nose, mid_ankle)

        # Scale to cm
        # Reference: average adult shoulder width = 42cm
        if shoulder_px > 0:
            scale = 42.0 / shoulder_px
        else:
            scale = 1.0

        shoulder_cm = round(shoulder_px * scale, 1)
        hip_cm      = round(hip_px * scale, 1)
        torso_cm    = round(torso_px * scale, 1)
        leg_cm      = round(leg_px * scale, 1)
        arm_cm      = round(arm_px * scale, 1)
        thigh_cm    = round(thigh_px * scale, 1)
        height_cm   = round(height_px * scale, 1)

        # Waist estimated as 80% of hip (approximation)
        waist_cm    = round(hip_cm * 0.80, 1)

        # Ratios for body type classification
        shoulder_hip_ratio = round(
            shoulder_cm / hip_cm if hip_cm > 0 else 1, 2)
        waist_hip_ratio = round(
            waist_cm / hip_cm if hip_cm > 0 else 1, 2)

        # Visibility/confidence score
        key_landmarks = [11, 12, 23, 24, 27, 28]
        confidence = round(
            min(float(getattr(lm[i], "visibility", 1.0)) for i in key_landmarks) * 100,
            1
        )

        print(f"Shoulder: {shoulder_cm}cm, Hip: {hip_cm}cm")
        print(f"Ratio: {shoulder_hip_ratio}, Height: {height_cm}cm")

        # ─── BODY TYPE CLASSIFICATION ───
        if shoulder_hip_ratio > 1.15:
            body_type = "Inverted Triangle"
            body_description = (
                "Your shoulders are broader than your hips, "
                "giving you a strong, athletic silhouette."
            )
            styling_tips = [
                "Balance proportions with A-line or flared skirts",
                "Wide-leg or bootcut pants work great",
                "Avoid shoulder pads or boat necklines",
                "Draw attention downward with bold bottom pieces",
                "V-necks and scoop necks elongate your frame",
                "Light or bright colours on bottoms, dark on top"
            ]
            recommended_styles = [
                "A-line dresses", "Bootcut jeans",
                "Peplum tops", "Wrap skirts"
            ]

        elif shoulder_hip_ratio < 0.88:
            body_type = "Pear"
            body_description = (
                "Your hips are wider than your shoulders, "
                "giving you a classic feminine silhouette."
            )
            styling_tips = [
                "Draw attention upward with bright or detailed tops",
                "Off-shoulder and wide necklines balance your frame",
                "A-line skirts skim over hips beautifully",
                "Avoid clingy fabrics or tight fits on hips",
                "Structured blazers add shoulder width",
                "Dark bottoms, bright or patterned tops"
            ]
            recommended_styles = [
                "A-line skirts", "Flowy tops",
                "Off-shoulder blouses", "Wide-leg pants"
            ]

        elif 0.88 <= shoulder_hip_ratio <= 1.15:
            if torso_cm < leg_cm * 0.55:
                body_type = "Apple"
                body_description = (
                    "You carry weight in midsection with "
                    "balanced shoulders and hips."
                )
                styling_tips = [
                    "Empire waist styles are very flattering",
                    "Wrap dresses define and elongate",
                    "Avoid tight waistbands or cropped tops",
                    "V-necks create a longer neckline",
                    "Flowy fabrics drape beautifully",
                    "Monochromatic outfits create a slimming effect"
                ]
                recommended_styles = [
                    "Wrap dresses", "Empire waist tops",
                    "Flowy tunics", "Bootcut pants"
                ]

            elif (0.93 <= shoulder_hip_ratio <= 1.07 and
                  waist_hip_ratio < 0.75):
                body_type = "Hourglass"
                body_description = (
                    "Your shoulders and hips are balanced with "
                    "a defined waist — a classic hourglass figure."
                )
                styling_tips = [
                    "Fitted and tailored styles showcase your shape",
                    "Wrap dresses are perfect for your figure",
                    "Belted outfits highlight your waist",
                    "High-waisted bottoms with tucked-in tops",
                    "Most necklines work beautifully for you",
                    "Avoid boxy or shapeless silhouettes"
                ]
                recommended_styles = [
                    "Wrap dresses", "Fitted blazers",
                    "High-waist jeans", "Bodycon dresses"
                ]

            else:
                body_type = "Rectangle"
                body_description = (
                    "Your shoulders, waist and hips are "
                    "well-balanced — a straight, athletic build."
                )
                styling_tips = [
                    "Create curves with ruffles, frills or peplum",
                    "Belt your outfits to define your waist",
                    "Layering adds visual dimension",
                    "High-waisted bottoms with tucked tops",
                    "Structured shoulders add definition",
                    "Most styles work well — experiment freely!"
                ]
                recommended_styles = [
                    "Peplum tops", "Belted dresses",
                    "Layered outfits", "Ruffled blouses"
                ]
        else:
            body_type = "Rectangle"
            body_description = "Well-balanced proportions."
            styling_tips = ["Most styles work great for you!"]
            recommended_styles = ["Experiment freely!"]

        print(f"Body type classified as: {body_type}")

        return {
            "success": True,
            "body_type": body_type,
            "body_description": body_description,
            "measurements": {
                "shoulder_width_cm": shoulder_cm,
                "hip_width_cm":      hip_cm,
                "waist_cm":          waist_cm,
                "torso_length_cm":   torso_cm,
                "leg_length_cm":     leg_cm,
                "arm_length_cm":     arm_cm,
                "thigh_length_cm":   thigh_cm,
                "estimated_height_cm": height_cm,
            },
            "ratios": {
                "shoulder_to_hip":  shoulder_hip_ratio,
                "waist_to_hip":     waist_hip_ratio,
            },
            "styling_tips":       styling_tips,
            "recommended_styles": recommended_styles,
            "confidence_percent": confidence,
            "landmarks_detected": True,
        }

    except RuntimeError as e:
        print(f"Runtime error: {e}")
        return {
            "error": str(e),
            "message": str(e),
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "message": "An unexpected error occurred during analysis."
        }
