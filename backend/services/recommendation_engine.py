"""
recommendation_engine.py
========================
Dynamic NLP + ML hybrid outfit recommendation engine.
No hardcoded outfit table is used as recommendation source.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from itertools import combinations, product
from typing import Any, Dict, List, Optional, Set, Tuple

from services.nlp_constraints import merge_constraints, parse_chat_constraints, parse_occasion_constraints
from services.ranking_model import predict_score


FORMALITY_RANK = {"Casual": 1, "Smart Casual": 2, "Semi-Formal": 3, "Formal": 4}
NEUTRAL_COLORS = {"Black", "White", "Grey", "Gray", "Cream", "Beige", "Khaki", "Navy", "Charcoal"}


def _parse_json_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [p.strip() for p in s.split(",") if p.strip()]


def normalize_item(item: dict) -> dict:
    return {
        "id": int(item["id"]),
        "name": item.get("name") or "",
        "category": str(item.get("category") or "").title(),
        "color": str(item.get("color") or "").title(),
        "pattern": item.get("pattern") or "Solid",
        "fabric": item.get("fabric") or "",
        "fit_type": item.get("fit_type") or "Regular",
        "formality": item.get("formality") or "Smart Casual",
        "style_tags": _parse_json_list(item.get("style_tags")),
        "occasion_tags": _parse_json_list(item.get("occasion_tags")),
        "active_flag": bool(item.get("active_flag", 1)),
        "usage_count": int(item.get("usage_count") or 0),
        "created_at": item.get("created_at"),
    }


def _text_blob(item: dict) -> str:
    parts = [
        item.get("name", ""),
        item.get("category", ""),
        item.get("color", ""),
        item.get("fabric", ""),
        item.get("formality", ""),
        " ".join(item.get("style_tags", [])),
        " ".join(item.get("occasion_tags", [])),
    ]
    return " ".join(str(p).lower() for p in parts if p)


def _keyword_score(item: dict, keywords: list[str]) -> float:
    if not keywords:
        return 0.3
    blob = _text_blob(item)
    hits = sum(1 for kw in keywords if kw.lower() in blob)
    return min(1.0, hits / max(1, len(keywords)))


def _formality_score(item: dict, target_formality: Optional[str]) -> float:
    if not target_formality:
        return 0.6
    a = FORMALITY_RANK.get(item.get("formality", "Smart Casual"), 2)
    b = FORMALITY_RANK.get(target_formality, 2)
    diff = abs(a - b)
    return max(0.0, 1.0 - (diff / 3.0))


def _category_score(item: dict, include_categories: list[str]) -> float:
    if not include_categories:
        return 0.6
    return 1.0 if item.get("category") in include_categories else 0.2


def _color_score(item: dict, include_colors: list[str], exclude_colors: list[str]) -> float:
    color = item.get("color", "")
    if color in exclude_colors:
        return 0.0
    if include_colors:
        return 1.0 if color in include_colors else 0.2
    return 0.6


def retrieve_relevant_items(wardrobe: List[dict], constraints: dict) -> List[dict]:
    relevant: List[dict] = []
    for raw in wardrobe:
        item = normalize_item(raw)
        if not item["active_flag"]:
            continue
        if item["category"] in constraints.get("exclude_categories", []):
            continue
        if item["color"] in constraints.get("exclude_colors", []):
            continue

        ks = _keyword_score(item, constraints.get("keywords", []))
        fs = _formality_score(item, constraints.get("target_formality"))
        cs = _category_score(item, constraints.get("include_categories", []))
        col = _color_score(item, constraints.get("include_colors", []), constraints.get("exclude_colors", []))
        base = 0.42 * ks + 0.27 * fs + 0.16 * cs + 0.15 * col
        item["retrieval_score"] = round(base, 4)
        if base >= 0.22:
            relevant.append(item)
    if not relevant:
        relevant = [normalize_item(w) for w in wardrobe if bool(w.get("active_flag", 1))]
    return sorted(relevant, key=lambda x: x["retrieval_score"], reverse=True)


def generate_combinations(items: List[dict]) -> List[List[dict]]:
    tops = [i for i in items if i["category"] == "Top"]
    bottoms = [i for i in items if i["category"] == "Bottom"]
    dresses = [i for i in items if i["category"] == "Dress"]

    combos: List[List[dict]] = []
    for top, bottom in product(tops, bottoms):
        combos.append([top, bottom])
    for dress in dresses:
        combos.append([dress])

    seen: set[str] = set()
    uniq: List[List[dict]] = []
    for c in combos:
        sig = signature(c)
        if sig not in seen:
            seen.add(sig)
            uniq.append(c)
    return uniq


def signature(items: List[dict]) -> str:
    return "-".join(sorted(str(i["id"]) for i in items))


def _color_compatibility(items: List[dict]) -> float:
    colors = [i["color"] for i in items]
    if len(colors) < 2:
        return 0.9
    if len(set(colors)) == 1:
        return 0.95
    if any(c in NEUTRAL_COLORS for c in colors):
        return 0.9
    return 0.65


def _preference_alignment(items: List[dict], preferences: Optional[dict]) -> float:
    if not preferences:
        return 0.6
    pref_colors = set(preferences.get("preferred_colors", []))
    dislike_colors = set(preferences.get("disliked_colors", []))
    pref_styles = set(preferences.get("preferred_styles", []))
    dislike_styles = set(preferences.get("disliked_styles", []))
    dislike_categories = set(preferences.get("disliked_categories", []))
    score = 0.6
    for it in items:
        if it["color"] in pref_colors:
            score += 0.12
        if it["color"] in dislike_colors:
            score -= 0.22
        if it["category"] in dislike_categories:
            score -= 0.25
        tags = set(it.get("style_tags", []))
        if tags.intersection(pref_styles):
            score += 0.08
        if tags.intersection(dislike_styles):
            score -= 0.18
    return max(0.0, min(1.0, score))


def _chat_constraint_match(items: List[dict], constraints: dict) -> float:
    score = 0.6
    include_colors = set(constraints.get("include_colors", []))
    include_categories = set(constraints.get("include_categories", []))
    for it in items:
        if include_colors and it["color"] in include_colors:
            score += 0.12
        if include_categories and it["category"] in include_categories:
            score += 0.12
    return max(0.0, min(1.0, score))


def _new_item_boost(items: List[dict]) -> float:
    now = datetime.utcnow()
    boosts: list[float] = []
    for it in items:
        created = it.get("created_at")
        if not created:
            boosts.append(0.4)
            continue
        try:
            dt = datetime.fromisoformat(str(created).replace("Z", ""))
            boosts.append(1.0 if dt >= now - timedelta(days=7) else 0.35)
        except Exception:
            boosts.append(0.4)
    return sum(boosts) / max(1, len(boosts))


def _category_compatibility(items: List[dict]) -> float:
    cats = [i["category"] for i in items]
    if cats == ["Dress"]:
        return 1.0
    return 1.0 if set(cats) == {"Top", "Bottom"} else 0.0


def score_outfit(
    items: List[dict],
    constraints: dict,
    preferences: Optional[dict],
    shown_signatures: Set[str],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    keyword_relevance = sum(i.get("retrieval_score", 0.0) for i in items) / len(items)
    formality_match = sum(_formality_score(i, constraints.get("target_formality")) for i in items) / len(items)
    category_compatibility = _category_compatibility(items)
    color_compatibility = _color_compatibility(items)
    preference_alignment = _preference_alignment(items, preferences)
    chat_constraint_match = _chat_constraint_match(items, constraints)
    novelty = 0.1 if signature(items) in shown_signatures else 1.0
    new_item_boost = _new_item_boost(items)

    features = {
        "keyword_relevance": keyword_relevance,
        "formality_match": formality_match,
        "category_compatibility": category_compatibility,
        "color_compatibility": color_compatibility,
        "preference_alignment": preference_alignment,
        "chat_constraint_match": chat_constraint_match,
        "novelty": novelty,
        "new_item_boost": new_item_boost,
    }

    ml_score = predict_score(features)
    weighted = (
        0.24 * keyword_relevance
        + 0.18 * formality_match
        + 0.11 * category_compatibility
        + 0.09 * color_compatibility
        + 0.16 * preference_alignment
        + 0.12 * chat_constraint_match
        + 0.06 * novelty
        + 0.04 * new_item_boost
    )
    final = 0.62 * weighted + 0.38 * ml_score

    # Legacy-compatible summary scores for frontend display cards.
    appropriateness = (keyword_relevance + formality_match + category_compatibility + color_compatibility) / 4.0
    confidence = (preference_alignment + chat_constraint_match + novelty) / 3.0
    comfort = (formality_match + color_compatibility + preference_alignment) / 3.0

    scores = {
        "keyword_relevance": round(keyword_relevance * 100, 1),
        "formality_match": round(formality_match * 100, 1),
        "category_compatibility": round(category_compatibility * 100, 1),
        "color_compatibility": round(color_compatibility * 100, 1),
        "preference_alignment": round(preference_alignment * 100, 1),
        "chat_constraint_match": round(chat_constraint_match * 100, 1),
        "novelty": round(novelty * 100, 1),
        "new_item_boost": round(new_item_boost * 100, 1),
        "ml_score": round(ml_score * 100, 1),
        "appropriateness": round(appropriateness * 100, 1),
        "confidence": round(confidence * 100, 1),
        "comfort": round(comfort * 100, 1),
        "suitability_score": round(appropriateness * 100, 1),
        "total": round(final * 100, 1),
    }
    return scores, features


def explain_outfit(items: List[dict], constraints: dict, scores: dict) -> List[str]:
    pieces = ", ".join((i["name"] or i["category"]) for i in items)
    bullets = [
        f"This outfit uses wardrobe items that match your occasion keywords ({scores['keyword_relevance']}% relevance).",
        f"It aligns with the requested formality ({scores['formality_match']}%).",
        f"It keeps category compatibility valid for wearable styling ({scores['category_compatibility']}%).",
        f"Color pairing suitability is {scores['color_compatibility']}%, balancing visual coherence.",
        f"Preference and chat-constraint alignment is {scores['chat_constraint_match']}%.",
        f"Selected pieces: {pieces}.",
    ]
    return bullets[:5]


def generate_recommendations(
    wardrobe: List[dict],
    occasion: str,
    mood: Optional[str],
    climate: Optional[str],
    preferences: Optional[dict],
    top_n: int = 3,
    additional_notes: Optional[str] = None,
    chat_message: Optional[str] = None,
    shown_signatures: Optional[Set[str]] = None,
) -> Tuple[List[dict], dict]:
    """
    Full dynamic flow:
    occasion NLP -> retrieval -> combination generation -> ranking -> top N.
    """
    if not wardrobe:
        return [], {}

    base_constraints = parse_occasion_constraints(occasion)
    if additional_notes:
        base_constraints = merge_constraints(base_constraints, parse_chat_constraints(additional_notes))
    chat_constraints = parse_chat_constraints(chat_message or "")
    constraints = merge_constraints(base_constraints, chat_constraints)

    relevant_items = retrieve_relevant_items(wardrobe, constraints)
    combos = generate_combinations(relevant_items)
    shown = shown_signatures or set()

    ranked = []
    for combo in combos:
        if signature(combo) in shown:
            continue
        scores, features = score_outfit(combo, constraints, preferences, shown)
        ranked.append(
            {
                "items": combo,
                "scores": scores,
                "features": features,
                "signature": signature(combo),
                "explanation": explain_outfit(combo, constraints, scores),
            }
        )

    ranked.sort(key=lambda x: x["scores"]["total"], reverse=True)
    selected = ranked[:max(1, top_n)]

    results: List[dict] = []
    for idx, row in enumerate(selected, start=1):
        results.append(
            {
                "rank": idx,
                "items": [
                    {
                        "id": i["id"],
                        "name": i["name"],
                        "category": i["category"],
                        "color": i["color"],
                        "formality": i["formality"],
                    }
                    for i in row["items"]
                ],
                "scores": {**row["scores"], "feature_vector": row["features"]},
                "explanation": row["explanation"],
                "signature": row["signature"],
            }
        )
    return results, constraints
