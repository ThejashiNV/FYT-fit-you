"""
nlp_constraints.py
==================
NLP helpers to parse occasion text and stylist chat constraints.
"""

from __future__ import annotations

import re
from typing import Any


ALL_COLORS = {
    "black", "white", "grey", "gray", "cream", "beige", "khaki", "charcoal",
    "navy", "blue", "light blue", "teal", "purple", "lavender",
    "maroon", "red", "rust", "orange", "mustard", "brown", "tan",
    "olive", "green", "burgundy", "camel", "terracotta",
    "pink", "peach", "mint", "sky blue", "lilac", "yellow",
}

CATEGORY_ALIASES = {
    "top": {"top", "shirt", "tshirt", "t-shirt", "blouse", "kurta", "tee"},
    "bottom": {"bottom", "pants", "trousers", "jeans", "shorts", "skirt"},
    "dress": {"dress", "gown"},
    "outerwear": {"blazer", "jacket", "coat", "outerwear", "layer"},
    "footwear": {"shoe", "shoes", "sneakers", "heels", "sandals", "footwear"},
}

FORMALITY_KEYWORDS = {
    "casual": {"casual", "relaxed", "chill", "informal", "comfortable"},
    "smart casual": {"smart casual", "smart-casual"},
    "semi-formal": {"semi formal", "semi-formal", "semi formal"},
    "formal": {"formal", "office", "professional", "interview", "wedding", "dinner", "presentation"},
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z]+", text.lower()) if len(t) > 1]


def extract_keywords(text: str) -> list[str]:
    return sorted(set(_tokens(text)))


def detect_colors(text: str) -> list[str]:
    msg = text.lower()
    found = []
    for color in sorted(ALL_COLORS, key=len, reverse=True):
        if color in msg:
            found.append(color.title())
    return sorted(set(found))


def detect_target_formality(text: str) -> str | None:
    msg = text.lower()
    for level, words in FORMALITY_KEYWORDS.items():
        for w in words:
            if w in msg:
                if level == "semi-formal":
                    return "Semi-Formal"
                if level == "smart casual":
                    return "Smart Casual"
                return level.title()
    return None


def detect_categories(text: str) -> list[str]:
    msg = text.lower()
    cats: list[str] = []
    for canonical, aliases in CATEGORY_ALIASES.items():
        if any(a in msg for a in aliases):
            cats.append(canonical.title() if canonical != "outerwear" else "Outerwear")
    return sorted(set(cats))


def parse_occasion_constraints(occasion_text: str) -> dict[str, Any]:
    """
    Parse occasion string into machine-usable retrieval constraints.
    """
    return {
        "keywords": extract_keywords(occasion_text),
        "target_formality": detect_target_formality(occasion_text),
        "include_colors": detect_colors(occasion_text),
        "include_categories": detect_categories(occasion_text),
        "exclude_categories": [],
        "exclude_colors": [],
        "style_keywords": extract_keywords(occasion_text),
        "request_alternative": False,
    }


def parse_chat_constraints(message: str) -> dict[str, Any]:
    """
    Parse stylist chat prompt for preference overrides and exclusions.
    """
    msg = message.lower().strip()
    keywords = extract_keywords(message)
    include_colors = detect_colors(message)
    include_categories = detect_categories(message)
    target_formality = detect_target_formality(message)

    exclude_categories: list[str] = []
    exclude_colors: list[str] = []

    negative_markers = ["no ", "not ", "without ", "exclude ", "don't ", "dont ", "avoid "]
    if any(m in msg for m in negative_markers):
        for cat in detect_categories(message):
            exclude_categories.append(cat)
        for c in detect_colors(message):
            exclude_colors.append(c)

    request_alternative = any(
        w in msg for w in ["another", "alternative", "other outfit", "show next", "recommend other"]
    )

    return {
        "keywords": keywords,
        "target_formality": target_formality,
        "include_colors": include_colors,
        "include_categories": include_categories,
        "exclude_categories": sorted(set(exclude_categories)),
        "exclude_colors": sorted(set(exclude_colors)),
        "style_keywords": keywords,
        "request_alternative": request_alternative,
    }


def merge_constraints(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    if not override:
        return dict(base)
    merged = dict(base)
    for key in ["keywords", "include_colors", "include_categories", "exclude_categories", "exclude_colors", "style_keywords"]:
        vals = list(base.get(key, [])) + list(override.get(key, []))
        merged[key] = sorted(set(v for v in vals if v))
    merged["target_formality"] = override.get("target_formality") or base.get("target_formality")
    merged["request_alternative"] = bool(override.get("request_alternative", False))
    return merged
