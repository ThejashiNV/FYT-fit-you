"""
Recommendation API endpoints.
Dynamic generation from wardrobe with NLP+ML hybrid ranking.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from database import get_connection
from models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    OutfitSuggestion,
    OutfitItem,
    SavedRecommendation,
    RecommendationFeedback,
)
from services.recommendation_engine import generate_recommendations
from services.ranking_model import update_weights_online

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


def _load_preferences(cursor, user_id: int) -> dict:
    row = cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {}
    return {
        "preferred_colors": json.loads(row["preferred_colors"] or "[]"),
        "disliked_colors": json.loads(row["disliked_colors"] or "[]"),
        "preferred_styles": json.loads(row["preferred_styles"] or "[]"),
        "disliked_styles": json.loads(row["disliked_styles"] or "[]"),
        "disliked_categories": json.loads(row["disliked_categories"] or "[]"),
        "preferred_formality": row["preferred_formality"],
        "temporary_constraints": json.loads(row["temporary_constraints"] or "{}"),
    }


def _load_session(cursor, user_id: int, session_id: Optional[int]):
    if session_id:
        row = cursor.execute(
            "SELECT * FROM recommendation_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if row:
            return row
    return None


def _create_session(cursor, user_id: int, req: RecommendationRequest, constraints: dict) -> int:
    cursor.execute(
        """
        INSERT INTO recommendation_sessions (
            user_id, occasion_input, mood, climate, base_constraints, shown_signatures
        ) VALUES (?, ?, ?, ?, ?, '[]')
        """,
        (user_id, req.occasion, req.mood, req.climate, json.dumps(constraints)),
    )
    return cursor.lastrowid


@router.post("/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(user_id: int, req: RecommendationRequest):
    conn = get_connection()
    cursor = conn.cursor()

    user = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")

    body = cursor.execute("SELECT * FROM body_profile WHERE user_id = ?", (user_id,)).fetchone()
    body_type = body["body_type"] if body else None

    wardrobe_rows = cursor.execute(
        "SELECT * FROM wardrobe_items WHERE user_id = ? AND COALESCE(active_flag,1)=1",
        (user_id,),
    ).fetchall()
    wardrobe = [dict(r) for r in wardrobe_rows]
    if not wardrobe:
        conn.close()
        raise HTTPException(status_code=400, detail="No wardrobe items found. Please add items first.")

    preferences = _load_preferences(cursor, user_id)

    session = _load_session(cursor, user_id, req.session_id)
    shown_signatures: set[str] = set()
    if session:
        shown_signatures = set(json.loads(session["shown_signatures"] or "[]"))

    climate = req.climate or user["climate_region"]
    results, constraints = generate_recommendations(
        wardrobe=wardrobe,
        occasion=req.occasion,
        mood=req.mood,
        climate=climate,
        preferences=preferences,
        additional_notes=req.additional_notes,
        chat_message=req.chat_message,
        top_n=req.top_n,
        shown_signatures=shown_signatures,
    )

    if not results:
        conn.close()
        raise HTTPException(status_code=400, detail="No valid outfits found for this request.")

    if session:
        session_id = int(session["id"])
    else:
        session_id = _create_session(cursor, user_id, req, constraints)

    # persist shown signatures queue state
    for r in results:
        shown_signatures.add(r["signature"])
    cursor.execute(
        """
        UPDATE recommendation_sessions
        SET shown_signatures = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(sorted(shown_signatures)), session_id),
    )

    # store generated recommendations as history only
    for r in results:
        cursor.execute(
            """
            INSERT INTO recommendations (user_id, occasion, mood, climate, outfit_items, scores, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                req.occasion,
                req.mood,
                climate,
                json.dumps(r["items"]),
                json.dumps(r["scores"]),
                json.dumps(r["explanation"]),
            ),
        )

    conn.commit()
    conn.close()

    outfits = [
        OutfitSuggestion(
            rank=r["rank"],
            items=[OutfitItem(**i) for i in r["items"]],
            scores=r["scores"],
            explanation=r["explanation"],
        )
        for r in results
    ]
    return RecommendationResponse(
        occasion=req.occasion,
        mood=req.mood,
        climate=climate,
        outfits=outfits,
        body_type=body_type,
        session_id=session_id,
        applied_constraints=constraints,
    )


@router.post("/{user_id}/next", response_model=RecommendationResponse)
async def next_recommendations(user_id: int, req: RecommendationRequest):
    """Return next best outfits from existing session (queue behavior)."""
    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id is required for next recommendations.")
    return await get_recommendations(user_id, req)


@router.post("/{user_id}/{rec_id}/feedback")
async def feedback_recommendation(user_id: int, rec_id: int, payload: RecommendationFeedback):
    conn = get_connection()
    cursor = conn.cursor()
    rec = cursor.execute("SELECT * FROM recommendations WHERE id = ? AND user_id = ?", (rec_id, user_id)).fetchone()
    if not rec:
        conn.close()
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    label = payload.label.lower().strip()
    if label not in {"like", "dislike", "skip", "wore"}:
        conn.close()
        raise HTTPException(status_code=400, detail="label must be one of: like, dislike, skip, wore")

    cursor.execute(
        "INSERT INTO recommendation_feedback (recommendation_id, user_id, label) VALUES (?, ?, ?)",
        (rec_id, user_id, label),
    )

    # online weight update using stored feature vector
    features = {}
    try:
        sc = json.loads(rec["scores"] or "{}")
        features = sc.get("feature_vector", {})
    except Exception:
        features = {}
    if features:
        y = 1.0 if label in {"like", "wore"} else 0.0
        update_weights_online([features], [y])

    conn.commit()
    conn.close()
    return {"message": "Feedback recorded."}


@router.get("/{user_id}/history", response_model=list[SavedRecommendation])
async def recommendation_history(user_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        SavedRecommendation(
            id=r["id"],
            occasion=r["occasion"],
            outfit_items=json.loads(r["outfit_items"]),
            scores=json.loads(r["scores"]),
            explanation=(
                ("\n".join(parsed) if isinstance((parsed := json.loads(r["explanation"])), list) else str(parsed))
                if r["explanation"]
                else None
            ),
            saved=bool(r["saved"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.put("/{rec_id}/save")
async def toggle_save(rec_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    rec = cursor.execute("SELECT * FROM recommendations WHERE id = ?", (rec_id,)).fetchone()
    if not rec:
        conn.close()
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    new_saved = 0 if rec["saved"] else 1
    cursor.execute("UPDATE recommendations SET saved = ? WHERE id = ?", (new_saved, rec_id))
    conn.commit()
    conn.close()
    return {"message": "Saved" if new_saved else "Unsaved", "saved": bool(new_saved)}
