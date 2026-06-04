"""
WanderHUB Backend — Pydantic Request/Response Schemas
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional


# ── Auth ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=200)
    password: str = Field(..., min_length=4, max_length=200)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserProfile


class UserProfile(BaseModel):
    id: int
    name: str
    email: str
    preferences_json: Optional[str] = None
    budget_default: Optional[int] = None


# ── Provider ─────────────────────────────────────────────────────

class ProviderCard(BaseModel):
    provider_id: int
    title: str
    district: str
    category: str
    role: str
    price_min_vnd: Optional[int] = None
    price_max_vnd: Optional[int] = None
    avg_duration_min: Optional[int] = None
    wanderhub_score: Optional[int] = None
    ai_base_score: Optional[float] = None
    image_url: Optional[str] = None
    image_credit: Optional[str] = None
    description: Optional[str] = None


class ProviderDetail(ProviderCard):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    moods: list[str] = []
    squad_scores: Optional[dict] = None


class ProviderListResponse(BaseModel):
    providers: list[ProviderCard]
    total: int


# ── Itinerary ────────────────────────────────────────────────────

class ItineraryGenerateRequest(BaseModel):
    mood: str = Field("chill", description="Mood/vibe code or text")
    budget_max: int = Field(500000, description="Max budget in VND")
    time_start: str = Field("18:00", description="Start time HH:MM")
    time_end: str = Field("22:00", description="End time HH:MM")
    district: str = Field("Quận 1", description="Preferred district")
    food_preference: Optional[str] = Field(None, description="Food preferences")
    transport: str = Field("Be / Xanh SM", description="Transport mode")
    max_stops: int = Field(6, ge=2, le=8)


class ItineraryStop(BaseModel):
    step: int
    provider_id: int
    title: str
    district: str
    category: str
    category_code: Optional[str] = None
    role: str
    arrival_time: str
    duration_min: int
    cost_estimated: int
    avg_price_vnd: Optional[int] = None
    reason: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_min_vnd: Optional[int] = None
    price_max_vnd: Optional[int] = None
    score: Optional[float] = None
    knn_similarity: Optional[float] = None
    business_tag: Optional[str] = None


class ItineraryResponse(BaseModel):
    itinerary_id: Optional[int] = None
    session_id: Optional[int] = None
    title: str
    mood: str
    total_cost: str
    total_duration: str
    transport: str
    stops: list[ItineraryStop]
    commercial_suggestions: list[ItineraryStop] = Field(default_factory=list)


class RerouteRequest(BaseModel):
    itinerary_id: Optional[int] = None
    stops: list[ItineraryStop]
    replace_step: int = Field(..., description="Step number to replace (1-based)")
    mood: str = "chill"
    budget_max: int = 500000
    district: str = "Quận 1"


# ── Chat ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)
    groq_key: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    source: str = "ai"  # "ai" | "mock" | "error"


# ── Contact ──────────────────────────────────────────────────────

class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=5)
    subject: Optional[str] = None
    message: str = Field(..., min_length=1)


class ContactResponse(BaseModel):
    success: bool
    message: str


# ── Landing ──────────────────────────────────────────────────────

class LandingResponse(BaseModel):
    hero: dict
    metrics: dict
    district_summary: list[dict]
    category_summary: list[dict]


# ── Feedback ─────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class InteractionRequest(BaseModel):
    session_id: Optional[int] = None
    itinerary_id: Optional[int] = None
    provider_id: Optional[int] = None
    event_type: Literal["view", "hover", "click", "choose", "save", "dislike", "reroute"]
    weight: Optional[float] = Field(None, ge=-10, le=10)
    metadata: Optional[dict] = None


class InteractionResponse(BaseModel):
    success: bool
    interaction_id: int
    message: str


# Fix forward reference
AuthResponse.model_rebuild()
