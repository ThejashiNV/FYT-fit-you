"""
ranking_model.py
================
Lightweight learnable ranking weights (online update from feedback).
"""

from __future__ import annotations

import json
import math
import os
from typing import Dict, List


MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model_weights.json")

DEFAULT_WEIGHTS = {
    "keyword_relevance": 1.4,
    "formality_match": 1.3,
    "category_compatibility": 1.0,
    "color_compatibility": 0.8,
    "preference_alignment": 1.2,
    "chat_constraint_match": 1.2,
    "novelty": 0.7,
    "new_item_boost": 0.6,
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def load_weights() -> Dict[str, float]:
    if not os.path.exists(MODEL_PATH):
        return dict(DEFAULT_WEIGHTS)
    try:
        with open(MODEL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        weights = dict(DEFAULT_WEIGHTS)
        for k in weights:
            if k in data:
                weights[k] = float(data[k])
        return weights
    except Exception:
        return dict(DEFAULT_WEIGHTS)


def save_weights(weights: Dict[str, float]) -> None:
    try:
        with open(MODEL_PATH, "w", encoding="utf-8") as f:
            json.dump(weights, f)
    except Exception:
        pass


def predict_score(features: Dict[str, float], weights: Dict[str, float] | None = None) -> float:
    w = weights or load_weights()
    z = 0.0
    for k, v in features.items():
        z += float(w.get(k, 0.0)) * float(v)
    return _sigmoid(z / max(1.0, len(features)))


def update_weights_online(feature_vectors: List[Dict[str, float]], labels: List[float], lr: float = 0.06) -> Dict[str, float]:
    if not feature_vectors or not labels or len(feature_vectors) != len(labels):
        return load_weights()

    weights = load_weights()
    keys = set(DEFAULT_WEIGHTS.keys())
    for fv, y in zip(feature_vectors, labels):
        pred = predict_score(fv, weights)
        err = pred - float(y)
        for k in keys:
            grad = err * float(fv.get(k, 0.0))
            weights[k] = float(weights.get(k, 0.0)) - lr * grad
    save_weights(weights)
    return weights
