"""
chatbot_engine.py
=================
Explainable AI chatbot with intent classification, template responses,
and preference extraction.
"""

from __future__ import annotations
import re
from typing import Optional, Dict, List, Tuple


ALL_COLORS = [
    "black", "white", "grey", "gray", "cream", "beige", "khaki", "charcoal",
    "navy", "blue", "light blue", "teal", "purple", "lavender",
    "maroon", "red", "rust", "orange", "mustard", "brown", "tan",
    "olive", "green", "burgundy", "camel", "terracotta",
    "pink", "peach", "mint", "sky blue", "lilac", "yellow",
    "gold", "silver", "neon", "coral", "mauve",
]


def classify_intent(message: str) -> str:
    """Classify user message into an intent category."""
    msg = message.lower().strip()

    if any(re.search(pattern, msg) for pattern in [r"\bhi\b", r"\bhello\b", r"\bhey\b"]):
        if len(msg.split()) <= 4:
            return "greeting"

    if any(w in msg for w in ["why", "explain", "how does", "reason", "tell me why"]):
        return "why_this_outfit"

    if any(w in msg for w in ["casual", "relaxed", "comfortable", "chill", "laid back"]):
        if any(w in msg for w in ["more", "make", "want", "prefer", "too formal"]):
            return "make_more_casual"

    if any(w in msg for w in ["formal", "professional", "dressy", "elegant", "polished"]):
        if any(w in msg for w in ["more", "make", "want", "prefer", "too casual"]):
            return "make_more_formal"

    if any(w in msg for w in ["don't like", "dont like", "hate", "dislike", "not a fan", "remove"]):
        for color in ALL_COLORS:
            if color in msg:
                return "dislike_color"

    if any(w in msg for w in ["prefer", "love", "like", "want more", "favorite"]):
        for color in ALL_COLORS:
            if color in msg:
                return "prefer_color"

    if any(w in msg for w in ["alternative", "another", "different", "other", "else", "change", "swap"]):
        return "try_alternative"

    if any(w in msg for w in ["without", "not this", "exclude", "no dress", "without skirt", "without skirts"]):
        return "refine_constraints"

    if any(w in msg for w in ["show me", "something in", "in black", "in blue", "semi formal", "semi-formal"]):
        return "refine_constraints"

    if any(w in msg for w in ["what should", "suggest", "recommend", "advice", "tip", "style"]):
        return "general_style_qa"

    return "general_style_qa"


def extract_colors_from_message(message: str) -> List[str]:
    """Extract color names mentioned in a message."""
    msg = message.lower()
    found = []
    for color in sorted(ALL_COLORS, key=len, reverse=True):
        if color in msg:
            found.append(color.title())
            msg = msg.replace(color, "")
    return found


def extract_sentiment(message: str) -> str:
    """Detect positive/negative sentiment."""
    msg = message.lower()
    negative = ["don't", "dont", "hate", "dislike", "not", "never", "remove", "no", "awful", "ugly"]
    positive = ["love", "like", "prefer", "want", "great", "amazing", "perfect", "beautiful"]

    neg_count = sum(1 for w in negative if w in msg)
    pos_count = sum(1 for w in positive if w in msg)

    if neg_count > pos_count:
        return "negative"
    elif pos_count > neg_count:
        return "positive"
    return "neutral"


def _pick(text: str, variants: List[str]) -> str:
    idx = abs(hash(text)) % len(variants)
    return variants[idx]


def _extract_context_points(current_outfit: Optional[dict]) -> List[str]:
    if not current_outfit:
        return []
    explanation = current_outfit.get("explanation")
    if isinstance(explanation, list):
        return [str(x) for x in explanation[:2]]
    if isinstance(explanation, str) and explanation.strip():
        return [explanation.strip()]
    return []


def generate_response(
    intent: str,
    message: str,
    current_outfit: Optional[dict] = None,
    body_type: Optional[str] = None,
    user_name: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """
    Generate a chatbot response and suggestion chips.

    Returns (response_text, suggestion_chips)
    """
    suggestions = ["Why this outfit?", "Make it casual", "Try alternative"]
    msg = message.strip()
    context_points = _extract_context_points(current_outfit)

    if intent == "greeting":
        name = user_name or "there"
        response = _pick(
            msg,
            [
                f"Hi {name}! I can explain your current look, tune formality, and learn your style preferences in real time.",
                f"Welcome back, {name}. Ask me to refine your outfit by occasion, mood, color, or comfort.",
            ],
        )
        suggestions = ["Why this outfit?", "Make it casual", "Try alternative"]

    elif intent == "why_this_outfit":
        if context_points:
            response = "Here is why this recommendation was chosen:\n\n"
            for point in context_points:
                response += f"- {point}\n"
            if body_type:
                response += f"\nI also tuned this for your {body_type} profile."
        else:
            response = _pick(
                msg,
                [
                    "This look is ranked using occasion-fit, confidence match, comfort, and your saved style signals.",
                    "I chose this based on context suitability, body-profile compatibility, and your preference history.",
                ],
            )
        suggestions = ["Try alternative", "Make it casual", "Make it formal"]

    elif intent == "make_more_casual":
        response = _pick(
            msg,
            [
                "Done. I will bias your next look toward relaxed silhouettes, lighter fabrics, and lower formality pieces.",
                "Got it. I will reduce structure and switch toward casual combinations from your current wardrobe.",
            ],
        )
        suggestions = ["Try alternative", "Why this outfit?", "Avoid black"]

    elif intent == "make_more_formal":
        response = _pick(
            msg,
            [
                "Understood. I will prioritize sharper tailoring, cleaner lines, and elevated formality for the next look.",
                "Great. I will push recommendations toward polished combinations suitable for formal settings.",
            ],
        )
        suggestions = ["Try alternative", "Why this outfit?", "Prefer navy"]

    elif intent == "dislike_color":
        colors = extract_colors_from_message(msg)
        if colors:
            color_str = ", ".join(colors)
            response = f"Noted. I will avoid {color_str} in future recommendations and rebalance your palette accordingly."
        else:
            response = "Noted. Tell me the specific colors you want me to avoid and I will update your preferences."
        suggestions = ["Prefer warm tones", "Prefer cool tones", "Try alternative"]

    elif intent == "prefer_color":
        colors = extract_colors_from_message(msg)
        if colors:
            color_str = ", ".join(colors)
            response = f"Perfect. I will prioritize {color_str} more often while keeping occasion suitability intact."
        else:
            response = "Share your preferred colors and I will prioritize them in future outfits."
        suggestions = ["Try alternative", "Why this color?", "Make it formal"]

    elif intent == "try_alternative":
        response = _pick(
            msg,
            [
                "I will generate a different combination using your same occasion and constraints, with better variety.",
                "I am switching to an alternative outfit that keeps context fit but changes the piece mix.",
            ],
        )
        suggestions = ["Why this outfit?", "Make it casual", "Make it formal"]

    elif intent == "refine_constraints":
        response = _pick(
            msg,
            [
                "Understood. I will apply these constraints and regenerate the next best matching outfits.",
                "Got it. I will re-rank your wardrobe combinations with your updated requirements.",
            ],
        )
        suggestions = ["Show another outfit", "Make it casual", "In black"]

    else:
        body_tip = ""
        if body_type:
            tips = {
                "Rectangle": "Create waist definition with layered structure and balanced contrast.",
                "Triangle": "Use upper-body visual weight and cleaner bottom lines for balance.",
                "Inverted Triangle": "Use fuller or straighter bottoms to balance shoulder width.",
                "Hourglass": "Use cuts that follow natural waist and maintain proportion continuity.",
            }
            body_tip = f" Body tip: {tips.get(body_type, '')}".strip()

        response = _pick(
            msg,
            [
                "Ask me to tune by occasion, confidence, comfort, or color and I will adapt your next recommendation." + (f" {body_tip}" if body_tip else ""),
                "I can refine your look instantly: make it more casual/formal, avoid colors, or explain why a look works." + (f" {body_tip}" if body_tip else ""),
            ],
        )
        suggestions = ["Why this outfit?", "Make it casual", "Try alternative"]

    return response, suggestions
