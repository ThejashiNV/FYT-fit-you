"""
Chat API endpoints with explainable AI.
"""

import json
from fastapi import APIRouter, HTTPException
from database import get_connection
from models.schemas import ChatMessage, ChatResponse, OutfitSuggestion, OutfitItem
from services.chatbot_engine import classify_intent, generate_response
from services.preference_learner import learn_from_message
from services.recommendation_engine import generate_recommendations
from services.nlp_constraints import parse_chat_constraints

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/{user_id}", response_model=ChatResponse)
async def send_message(user_id: int, chat: ChatMessage):
    """Send a message and get AI stylist response."""
    conn = get_connection()
    cursor = conn.cursor()

    # Verify user
    user = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")

    # Get body type for context
    body = cursor.execute(
        "SELECT body_type FROM body_profile WHERE user_id = ?", (user_id,)
    ).fetchone()
    body_type = body["body_type"] if body else None

    # Classify intent
    intent = classify_intent(chat.message)

    # Generate response
    current_outfit = chat.context  # Optional context from frontend
    response_text, suggestion_chips = generate_response(
        intent=intent,
        message=chat.message,
        current_outfit=current_outfit,
        body_type=body_type,
        user_name=user["name"],
    )

    # Learn preferences from message
    extracted = learn_from_message(user_id, chat.message, intent)
    updated_recommendation = None

    # If context has recommendation query, rerank/regenerate based on this chat message.
    ctx = chat.context or {}
    if isinstance(ctx, dict) and ctx.get("occasion"):
        wardrobe_rows = cursor.execute(
            "SELECT * FROM wardrobe_items WHERE user_id = ? AND COALESCE(active_flag,1)=1",
            (user_id,),
        ).fetchall()
        wardrobe = [dict(r) for r in wardrobe_rows]
        pref_row = cursor.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        prefs = {}
        if pref_row:
            prefs = {
                "preferred_colors": json.loads(pref_row["preferred_colors"] or "[]"),
                "disliked_colors": json.loads(pref_row["disliked_colors"] or "[]"),
                "preferred_styles": json.loads(pref_row["preferred_styles"] or "[]"),
                "disliked_styles": json.loads(pref_row["disliked_styles"] or "[]"),
                "disliked_categories": json.loads(pref_row["disliked_categories"] or "[]"),
                "preferred_formality": pref_row["preferred_formality"],
            }

        shown_signatures = set(ctx.get("shown_signatures", []))
        parsed = parse_chat_constraints(chat.message)
        results, _ = generate_recommendations(
            wardrobe=wardrobe,
            occasion=str(ctx.get("occasion")),
            mood=ctx.get("mood"),
            climate=ctx.get("climate"),
            preferences=prefs,
            top_n=1,
            additional_notes=ctx.get("additional_notes"),
            chat_message=chat.message,
            shown_signatures=shown_signatures if parsed.get("request_alternative") else set(),
        )
        if results:
            r = results[0]
            updated_recommendation = OutfitSuggestion(
                rank=r["rank"],
                items=[OutfitItem(**i) for i in r["items"]],
                scores=r["scores"],
                explanation=r["explanation"],
            )

    # Save chat logs
    cursor.execute("""
        INSERT INTO chat_logs (user_id, role, message, context_data, extracted_preferences)
        VALUES (?, 'user', ?, ?, ?)
    """, (user_id, chat.message,
          json.dumps(chat.context) if chat.context else None,
          json.dumps(extracted) if extracted else None))

    cursor.execute("""
        INSERT INTO chat_logs (user_id, role, message, context_data)
        VALUES (?, 'assistant', ?, ?)
    """, (user_id, response_text, json.dumps({"intent": intent})))

    conn.commit()
    conn.close()

    return ChatResponse(
        response=response_text,
        intent=intent,
        extracted_preferences=extracted,
        updated_recommendation=updated_recommendation,
        suggestions=suggestion_chips,
    )


@router.get("/{user_id}/history")
async def chat_history(user_id: int):
    """Get chat history for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chat_logs WHERE user_id = ? ORDER BY created_at ASC LIMIT 100",
        (user_id,)
    ).fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "role": r["role"],
            "message": r["message"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
