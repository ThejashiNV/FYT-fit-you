"""
User preferences API endpoints.
"""

import json
from fastapi import APIRouter, HTTPException
from database import get_connection
from models.schemas import UserPreferenceResponse, UserPreferenceUpdate

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


@router.get("/{user_id}", response_model=UserPreferenceResponse)
async def get_preferences(user_id: int):
    """Get learned preferences for a user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return UserPreferenceResponse(user_id=user_id)

    return UserPreferenceResponse(
        user_id=row["user_id"],
        preferred_colors=json.loads(row["preferred_colors"] or "[]"),
        disliked_colors=json.loads(row["disliked_colors"] or "[]"),
        preferred_styles=json.loads(row["preferred_styles"] or "[]"),
        disliked_styles=json.loads(row["disliked_styles"] or "[]"),
        disliked_categories=json.loads(row["disliked_categories"] or "[]"),
        preferred_formality=row["preferred_formality"],
        comfort_priority=row["comfort_priority"],
        confidence_priority=row["confidence_priority"],
        temporary_constraints=json.loads(row["temporary_constraints"] or "{}"),
    )


@router.put("/{user_id}", response_model=UserPreferenceResponse)
async def update_preferences(user_id: int, update: UserPreferenceUpdate):
    """Manually update user preferences."""
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not row:
        # Create default preferences first
        cursor.execute("INSERT INTO user_preferences (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = cursor.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
        ).fetchone()

    updates = {}
    if update.preferred_colors is not None:
        updates["preferred_colors"] = json.dumps(update.preferred_colors)
    if update.disliked_colors is not None:
        updates["disliked_colors"] = json.dumps(update.disliked_colors)
    if update.preferred_styles is not None:
        updates["preferred_styles"] = json.dumps(update.preferred_styles)
    if update.disliked_styles is not None:
        updates["disliked_styles"] = json.dumps(update.disliked_styles)
    if update.disliked_categories is not None:
        updates["disliked_categories"] = json.dumps(update.disliked_categories)
    if update.preferred_formality is not None:
        updates["preferred_formality"] = update.preferred_formality
    if update.comfort_priority is not None:
        updates["comfort_priority"] = update.comfort_priority
    if update.confidence_priority is not None:
        updates["confidence_priority"] = update.confidence_priority
    if update.temporary_constraints is not None:
        updates["temporary_constraints"] = json.dumps(update.temporary_constraints)

    if updates:
        updates["updated_at"] = "CURRENT_TIMESTAMP"
        set_parts = []
        values = []
        for k, v in updates.items():
            if k == "updated_at":
                set_parts.append(f"{k} = CURRENT_TIMESTAMP")
            else:
                set_parts.append(f"{k} = ?")
                values.append(v)

        values.append(user_id)
        cursor.execute(
            f"UPDATE user_preferences SET {', '.join(set_parts)} WHERE user_id = ?",
            values,
        )
        conn.commit()

    row = cursor.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()

    return UserPreferenceResponse(
        user_id=row["user_id"],
        preferred_colors=json.loads(row["preferred_colors"] or "[]"),
        disliked_colors=json.loads(row["disliked_colors"] or "[]"),
        preferred_styles=json.loads(row["preferred_styles"] or "[]"),
        disliked_styles=json.loads(row["disliked_styles"] or "[]"),
        disliked_categories=json.loads(row["disliked_categories"] or "[]"),
        preferred_formality=row["preferred_formality"],
        comfort_priority=row["comfort_priority"],
        confidence_priority=row["confidence_priority"],
        temporary_constraints=json.loads(row["temporary_constraints"] or "{}"),
    )
