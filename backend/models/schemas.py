"""
Pydantic models for all API request/response schemas.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ─── User Schemas ───────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    style_preference: str = "Minimal"
    climate_region: str = "Tropical"


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    style_preference: str
    climate_region: str
    created_at: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    style_preference: Optional[str] = None
    climate_region: Optional[str] = None


# ─── Body Profile Schemas ──────────────────────────────────────

class BodyProfileCreate(BaseModel):
    height_cm: float = Field(..., ge=120, le=230)
    weight_kg: float = Field(..., ge=30, le=250)
    shoulder_cm: float = Field(..., ge=25, le=70)
    chest_cm: float = Field(..., ge=55, le=180)
    waist_cm: float = Field(..., ge=45, le=180)
    hip_cm: float = Field(..., ge=55, le=200)
    inseam_cm: float = Field(..., ge=45, le=120)


class BodyProfileResponse(BaseModel):
    id: int
    user_id: int
    height_cm: float
    weight_kg: float
    shoulder_cm: float
    chest_cm: float
    waist_cm: float
    hip_cm: float
    inseam_cm: float
    body_type: str
    bmi: float
    bmi_category: str
    shoulder_to_hip_ratio: float
    waist_to_hip_ratio: float
    leg_to_height_ratio: float
    proportion_summary: str
    styling_suggestions: List[str] = []


class BodyScanPersistRequest(BaseModel):
    metrics: dict
    body_type: str
    symmetry: float
    posture_angle: float
    estimated_height_cm: float = 170.0
    estimated_weight_kg: float = 68.0


# ─── Wardrobe Schemas ──────────────────────────────────────────

class WardrobeItemCreate(BaseModel):
    name: Optional[str] = None
    category: str  # Top, Bottom, Dress, Outerwear, Footwear, Accessory
    color: str
    pattern: Optional[str] = "Solid"
    fabric: Optional[str] = None
    fit_type: Optional[str] = "Regular"
    formality: str  # Casual, Smart Casual, Semi-Formal, Formal
    style_tags: Optional[List[str]] = None
    occasion_tags: Optional[List[str]] = None
    active_flag: Optional[bool] = True


class WardrobeItemResponse(BaseModel):
    id: int
    user_id: int
    name: Optional[str]
    category: str
    color: str
    pattern: Optional[str] = None
    fabric: Optional[str]
    fit_type: Optional[str] = None
    formality: str
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    active_flag: bool = True
    image_path: Optional[str]
    usage_count: int = 0
    last_used: Optional[str] = None
    last_worn_at: Optional[str] = None
    created_at: Optional[str] = None


class WardrobeStats(BaseModel):
    total_items: int
    most_used: List[WardrobeItemResponse]
    least_used: List[WardrobeItemResponse]
    category_breakdown: dict


# ─── Recommendation Schemas ────────────────────────────────────

class RecommendationRequest(BaseModel):
    occasion: str  # College, Office, Wedding, Casual, Date, Presentation
    mood: Optional[str] = "Confident"
    climate: Optional[str] = "Warm"
    additional_notes: Optional[str] = None
    top_n: int = Field(3, ge=1, le=10)
    session_id: Optional[int] = None
    chat_message: Optional[str] = None


class OutfitItem(BaseModel):
    id: int
    name: Optional[str]
    category: str
    color: str
    formality: str


class OutfitSuggestion(BaseModel):
    rank: int
    items: List[OutfitItem]
    scores: dict  # {appropriateness, confidence, comfort, total}
    explanation: List[str]  # "Why this works" bullets


class RecommendationResponse(BaseModel):
    occasion: str
    mood: Optional[str]
    climate: Optional[str]
    outfits: List[OutfitSuggestion]
    body_type: Optional[str] = None
    session_id: Optional[int] = None
    applied_constraints: Optional[dict] = None


class SavedRecommendation(BaseModel):
    id: int
    occasion: str
    outfit_items: List[dict]
    scores: dict
    explanation: Optional[str]
    saved: bool
    created_at: Optional[str]


class RecommendationFeedback(BaseModel):
    label: str  # like/dislike/skip/wore


# ─── Chat Schemas ──────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None  # current recommendation context


class ChatResponse(BaseModel):
    response: str
    intent: str
    extracted_preferences: Optional[dict] = None
    updated_recommendation: Optional[OutfitSuggestion] = None
    suggestions: List[str] = []  # suggestion chips


# ─── Preference Schemas ───────────────────────────────────────

class UserPreferenceResponse(BaseModel):
    user_id: int
    preferred_colors: List[str] = []
    disliked_colors: List[str] = []
    preferred_styles: List[str] = []
    disliked_styles: List[str] = []
    disliked_categories: List[str] = []
    preferred_formality: str = "Smart Casual"
    comfort_priority: float = 0.5
    confidence_priority: float = 0.5
    temporary_constraints: dict = {}


class UserPreferenceUpdate(BaseModel):
    preferred_colors: Optional[List[str]] = None
    disliked_colors: Optional[List[str]] = None
    preferred_styles: Optional[List[str]] = None
    disliked_styles: Optional[List[str]] = None
    disliked_categories: Optional[List[str]] = None
    preferred_formality: Optional[str] = None
    comfort_priority: Optional[float] = None
    confidence_priority: Optional[float] = None
    temporary_constraints: Optional[dict] = None
