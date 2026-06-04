"""
WanderHUB AI - Content-based KNN feature scoring.

This is a lightweight, deterministic recommender layer: each provider and each
user intent is represented as a feature vector, then scored with cosine
similarity. It avoids LLM hallucination because recommendations are selected
only from real database providers.
"""

from __future__ import annotations

import math

CATEGORY_FEATURES = ["food", "cafe_drink", "nightlife", "culture", "checkin", "entertainment"]
ROLE_FEATURES = ["core", "premium", "experiential", "exploratory"]
EXPERIENCE_FEATURES = [
    "quiet",
    "romantic",
    "group_friendly",
    "food_focus",
    "night_energy",
    "culture_depth",
    "photo_spot",
    "budget_friendly",
    "premium_feel",
    "solo_friendly",
    "hidden_gem",
    "creative",
    "commerce_ready",
]

FEATURES = [
    *[f"category:{item}" for item in CATEGORY_FEATURES],
    *[f"role:{item}" for item in ROLE_FEATURES],
    *[f"xp:{item}" for item in EXPERIENCE_FEATURES],
    "price:budget",
    "price:mid",
    "price:premium",
    "quality:high",
    "quality:data_rich",
    "business:deal_ready",
    "business:sponsored_candidate",
]

FEATURE_INDEX = {name: idx for idx, name in enumerate(FEATURES)}

MOOD_WEIGHTS = {
    "chill": {"category:cafe_drink": 1.0, "category:checkin": 0.65, "xp:quiet": 0.9, "xp:solo_friendly": 0.45, "price:mid": 0.3},
    "date": {"xp:romantic": 1.0, "category:cafe_drink": 0.8, "category:food": 0.75, "category:checkin": 0.5, "category:nightlife": 0.45, "xp:premium_feel": 0.55},
    "group": {"xp:group_friendly": 1.0, "category:food": 0.9, "category:entertainment": 0.8, "category:cafe_drink": 0.55, "category:nightlife": 0.65, "category:checkin": 0.25},
    "foodie": {"xp:food_focus": 1.0, "category:food": 1.0, "category:cafe_drink": 0.55, "quality:high": 0.35},
    "nightlife": {"xp:night_energy": 1.0, "category:nightlife": 1.0, "category:food": 0.55, "xp:group_friendly": 0.4},
    "culture": {"xp:culture_depth": 1.0, "category:culture": 1.0, "category:checkin": 0.55, "xp:creative": 0.35},
    "checkin": {"xp:photo_spot": 1.0, "category:checkin": 1.0, "category:culture": 0.35, "xp:group_friendly": 0.25},
    "hidden_gem": {"xp:hidden_gem": 1.0, "role:exploratory": 0.75, "category:cafe_drink": 0.55, "category:food": 0.45},
    "healing": {"xp:quiet": 1.0, "category:checkin": 0.7, "category:cafe_drink": 0.55, "xp:solo_friendly": 0.55},
    "premium": {"xp:premium_feel": 1.0, "role:premium": 0.9, "price:premium": 0.6, "category:food": 0.55},
    "budget": {"xp:budget_friendly": 1.0, "price:budget": 1.0, "category:checkin": 0.65, "category:food": 0.45},
    "solo": {"xp:solo_friendly": 1.0, "xp:quiet": 0.55, "category:cafe_drink": 0.65, "category:culture": 0.45},
    "creative": {"xp:creative": 1.0, "category:culture": 0.75, "category:entertainment": 0.5, "category:cafe_drink": 0.45},
    "must_try": {"quality:high": 1.0, "xp:food_focus": 0.55, "xp:photo_spot": 0.45, "category:food": 0.55},
}

FOOD_PREFERENCE_WEIGHTS = {
    "chup hinh": {"xp:photo_spot": 0.7, "category:checkin": 0.55},
    "check": {"xp:photo_spot": 0.65, "category:checkin": 0.5},
    "cafe": {"category:cafe_drink": 0.7, "xp:quiet": 0.25},
    "am thuc": {"category:food": 0.7, "xp:food_focus": 0.45},
    "food": {"category:food": 0.7, "xp:food_focus": 0.45},
    "van hoa": {"category:culture": 0.65, "xp:culture_depth": 0.45},
    "night": {"category:nightlife": 0.65, "xp:night_energy": 0.45},
    "vui choi": {"category:entertainment": 0.65, "xp:group_friendly": 0.35},
}

CATEGORY_TO_XP = {
    "food": {"xp:food_focus": 0.9, "xp:group_friendly": 0.45},
    "cafe_drink": {"xp:quiet": 0.45, "xp:solo_friendly": 0.45, "xp:romantic": 0.25},
    "nightlife": {"xp:night_energy": 0.95, "xp:group_friendly": 0.55},
    "culture": {"xp:culture_depth": 0.95, "xp:creative": 0.55, "xp:solo_friendly": 0.35},
    "checkin": {"xp:photo_spot": 0.95, "xp:budget_friendly": 0.35, "xp:group_friendly": 0.25},
    "entertainment": {"xp:group_friendly": 0.85, "xp:creative": 0.35},
}

ROLE_TO_XP = {
    "core": {"role:core": 0.8},
    "premium": {"role:premium": 0.9, "xp:premium_feel": 0.75},
    "experiential": {"role:experiential": 0.9, "xp:culture_depth": 0.25, "xp:creative": 0.25},
    "exploratory": {"role:exploratory": 0.9, "xp:hidden_gem": 0.75},
}


def _zero_vector() -> list[float]:
    return [0.0] * len(FEATURES)


def _add(vector: list[float], feature: str, weight: float) -> None:
    idx = FEATURE_INDEX.get(feature)
    if idx is not None:
        vector[idx] += weight


def _normalize_score(value: float | int | None, default: float = 50.0) -> float:
    if value is None:
        return default
    return max(0.0, min(100.0, float(value)))


def _price_band(price_min: int | None, price_max: int | None, budget_max: int | None = None) -> str:
    price = price_max or price_min or 0
    if budget_max and price and price <= budget_max / 3:
        return "price:budget"
    if price <= 120_000:
        return "price:budget"
    if price <= 350_000:
        return "price:mid"
    return "price:premium"


def build_intent_vector(context: dict, rules: dict) -> list[float]:
    vector = _zero_vector()
    moods = context.get("moods") or ["chill"]
    for mood in moods:
        for feature, weight in MOOD_WEIGHTS.get(mood, {}).items():
            _add(vector, feature, weight)

    for category in rules.get("mood_category_affinity", []):
        _add(vector, f"category:{category}", 0.45)
    for category in rules.get("category_flow", [])[:4]:
        _add(vector, f"category:{category}", 0.25)
    for role in rules.get("role_preference", []):
        _add(vector, f"role:{role}", 0.35)

    budget = context.get("budget_max") or 0
    if budget < 250_000:
        _add(vector, "price:budget", 0.9)
        _add(vector, "xp:budget_friendly", 0.65)
    elif budget > 700_000:
        _add(vector, "price:premium", 0.45)
        _add(vector, "xp:premium_feel", 0.35)
    else:
        _add(vector, "price:mid", 0.55)

    food_preference = str(context.get("food_preference") or "").strip().casefold()
    for keyword, weights in FOOD_PREFERENCE_WEIGHTS.items():
        if keyword in food_preference:
            for feature, weight in weights.items():
                _add(vector, feature, weight)

    if "hidden_gem" in moods or "premium" in moods or budget >= 500_000:
        _add(vector, "business:deal_ready", 0.25)
        _add(vector, "xp:commerce_ready", 0.2)

    return vector


def build_provider_vector(provider: dict) -> list[float]:
    vector = _zero_vector()
    category = provider.get("category_code")
    role = provider.get("role_code") or str(provider.get("role", "")).strip().casefold()

    if category:
        _add(vector, f"category:{category}", 1.0)
        for feature, weight in CATEGORY_TO_XP.get(category, {}).items():
            _add(vector, feature, weight)

    for feature, weight in ROLE_TO_XP.get(role, {}).items():
        _add(vector, feature, weight)

    _add(vector, _price_band(provider.get("price_min_vnd"), provider.get("price_max_vnd")), 0.65)

    wanderhub_score = _normalize_score(provider.get("wanderhub_score"))
    data_score = _normalize_score((provider.get("data_compatibility") or 3) * 20)
    deal_score = _normalize_score((provider.get("deal_viability") or 3) * 20)
    if wanderhub_score >= 78:
        _add(vector, "quality:high", 0.65)
    if data_score >= 70 or provider.get("image_url") or provider.get("description"):
        _add(vector, "quality:data_rich", 0.45)
    if deal_score >= 80:
        _add(vector, "business:deal_ready", 0.8)
        _add(vector, "xp:commerce_ready", 0.45)
    elif deal_score >= 60:
        _add(vector, "business:deal_ready", 0.35)
    if provider.get("commercial_priority"):
        _add(vector, "business:sponsored_candidate", 0.8)
        _add(vector, "xp:commerce_ready", 0.55)

    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def knn_similarity_score(provider: dict, intent_vector: list[float]) -> float:
    """Return a 0-100 content similarity score."""
    return round(cosine_similarity(intent_vector, build_provider_vector(provider)) * 100.0, 2)
