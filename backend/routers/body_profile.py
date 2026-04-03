import json
from typing import Any

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from body_metric_module import analyze_body_from_image
from database import get_connection
from models.schemas import BodyProfileCreate, BodyScanPersistRequest

router = APIRouter()


def _bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Healthy"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _to_response(row: Any) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "height_cm": float(row["height_cm"] or 0),
        "weight_kg": float(row["weight_kg"] or 0),
        "shoulder_cm": float(row["shoulder_cm"] or 0),
        "chest_cm": float(row["chest_cm"] or 0),
        "waist_cm": float(row["waist_cm"] or 0),
        "hip_cm": float(row["hip_cm"] or 0),
        "inseam_cm": float(row["inseam_cm"] or 0),
        "body_type": row["body_type"] or "Unknown",
        "bmi": float(row["bmi"] or 0),
        "bmi_category": row["bmi_category"] or "Unknown",
        "shoulder_to_hip_ratio": float(row["shoulder_to_hip_ratio"] or 0),
        "waist_to_hip_ratio": float(row["waist_to_hip_ratio"] or 0),
        "leg_to_height_ratio": float(row["leg_to_height_ratio"] or 0),
        "proportion_summary": row["proportion_summary"] or "",
        "styling_suggestions": json.loads(row["styling_suggestions"] or "[]"),
    }


def _upsert_profile(
    user_id: int,
    *,
    height_cm: float,
    weight_kg: float,
    shoulder_cm: float,
    chest_cm: float,
    waist_cm: float,
    hip_cm: float,
    inseam_cm: float,
    body_type: str,
    proportion_summary: str,
    styling_suggestions: list[str],
) -> dict:
    bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 2) if height_cm > 0 else 0.0
    shoulder_to_hip_ratio = round(shoulder_cm / hip_cm, 2) if hip_cm > 0 else 0.0
    waist_to_hip_ratio = round(waist_cm / hip_cm, 2) if hip_cm > 0 else 0.0
    leg_to_height_ratio = round(inseam_cm / height_cm, 2) if height_cm > 0 else 0.0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO body_profile (
            user_id, height_cm, weight_kg, shoulder_cm, chest_cm, waist_cm, hip_cm, inseam_cm,
            body_type, bmi, bmi_category, shoulder_to_hip_ratio, waist_to_hip_ratio,
            leg_to_height_ratio, proportion_summary, styling_suggestions, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            height_cm=excluded.height_cm,
            weight_kg=excluded.weight_kg,
            shoulder_cm=excluded.shoulder_cm,
            chest_cm=excluded.chest_cm,
            waist_cm=excluded.waist_cm,
            hip_cm=excluded.hip_cm,
            inseam_cm=excluded.inseam_cm,
            body_type=excluded.body_type,
            bmi=excluded.bmi,
            bmi_category=excluded.bmi_category,
            shoulder_to_hip_ratio=excluded.shoulder_to_hip_ratio,
            waist_to_hip_ratio=excluded.waist_to_hip_ratio,
            leg_to_height_ratio=excluded.leg_to_height_ratio,
            proportion_summary=excluded.proportion_summary,
            styling_suggestions=excluded.styling_suggestions,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            user_id,
            height_cm,
            weight_kg,
            shoulder_cm,
            chest_cm,
            waist_cm,
            hip_cm,
            inseam_cm,
            body_type,
            bmi,
            _bmi_category(bmi),
            shoulder_to_hip_ratio,
            waist_to_hip_ratio,
            leg_to_height_ratio,
            proportion_summary,
            json.dumps(styling_suggestions),
        ),
    )
    conn.commit()
    row = cur.execute("SELECT * FROM body_profile WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return _to_response(row)


@router.post("/{user_id}/scan")
async def scan_body(user_id: str, file: UploadFile = File(...)):
    print(f"Received scan request for user: {user_id}")
    print(f"File: {file.filename}, type: {file.content_type}")

    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file", "message": "Please upload an image file (JPG or PNG)"},
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        return JSONResponse(
            status_code=400,
            content={"error": "Empty file", "message": "The uploaded file is empty."},
        )

    result = analyze_body_from_image(image_bytes)
    if "error" in result and "success" not in result:
        return JSONResponse(status_code=422, content=result)
    return JSONResponse(status_code=200, content=result)


@router.post("/{user_id}")
async def save_body_profile(user_id: int, payload: BodyProfileCreate):
    profile = _upsert_profile(
        user_id,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        shoulder_cm=payload.shoulder_cm,
        chest_cm=payload.chest_cm,
        waist_cm=payload.waist_cm,
        hip_cm=payload.hip_cm,
        inseam_cm=payload.inseam_cm,
        body_type="Manual",
        proportion_summary="Profile saved from manual measurements.",
        styling_suggestions=["Keep proportions balanced with structured silhouettes."],
    )
    return JSONResponse(status_code=200, content=profile)


@router.post("/{user_id}/scan-save")
async def save_scan_profile(user_id: int, payload: BodyScanPersistRequest):
    metrics = payload.metrics or {}
    measurements = metrics.get("measurements", metrics) if isinstance(metrics, dict) else {}
    ratios = metrics.get("ratios", {}) if isinstance(metrics, dict) else {}

    shoulder_cm = float(measurements.get("shoulder_width_cm", measurements.get("shoulder_cm", 42.0)))
    hip_cm = float(measurements.get("hip_width_cm", measurements.get("hip_cm", max(shoulder_cm, 38.0))))
    waist_cm = float(measurements.get("waist_cm", max(hip_cm * 0.8, 35.0)))
    inseam_cm = float(measurements.get("leg_length_cm", measurements.get("inseam_cm", 78.0)))
    height_cm = float(measurements.get("estimated_height_cm", payload.estimated_height_cm))
    weight_kg = float(payload.estimated_weight_kg)
    chest_cm = float(measurements.get("chest_cm", round(shoulder_cm * 2.1, 1)))

    summary = (
        f"{payload.body_type} profile from camera scan. "
        f"Shoulder/Hip ratio {ratios.get('shoulder_to_hip', round(shoulder_cm / hip_cm, 2) if hip_cm else 0)}."
    )

    profile = _upsert_profile(
        user_id,
        height_cm=height_cm,
        weight_kg=weight_kg,
        shoulder_cm=shoulder_cm,
        chest_cm=chest_cm,
        waist_cm=waist_cm,
        hip_cm=hip_cm,
        inseam_cm=inseam_cm,
        body_type=payload.body_type,
        proportion_summary=summary,
        styling_suggestions=["Based on scan, choose balanced silhouettes and fit-aware layering."],
    )
    return JSONResponse(status_code=200, content=profile)


@router.get("/{user_id}")
async def get_body_profile(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM body_profile WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return JSONResponse(status_code=404, content={"message": "Body profile not found"})
    return JSONResponse(status_code=200, content=_to_response(row))
