"""
WanderHUB Backend — Scoring Utilities
"""


def calculate_recommendation_score(
    ai_base_score: float,
    mood_match: bool,
    distance_km: float,
    budget_remaining: int,
    price_max: int,
    prev_category: str | None,
    current_category: str,
) -> float:
    """Calculate a composite recommendation score for itinerary slot selection.

    Weights:
      - ai_base_score:   40%  (existing SQUAD+popularity+confidence blend)
      - mood_match:       25%  (bonus if provider has matching mood tag)
      - distance_penalty: 15%  (closer = better, penalize far providers)
      - budget_fit:       10%  (bonus if affordable within remaining budget)
      - diversity:        10%  (bonus if different category from previous stop)
    """
    # Normalize ai_base_score to 0-100 range (it's already roughly 0-100)
    base = ai_base_score * 0.4

    # Mood match: +25 if matched
    mood_bonus = 25.0 if mood_match else 0.0

    # Distance penalty: 0 at 0km, -15 at 5+ km (linear)
    distance_penalty = max(-15.0, -3.0 * distance_km)

    # Budget fit: +10 if price fits in remaining budget, -5 if over
    if price_max <= budget_remaining:
        budget_fit = 10.0
    elif price_max <= budget_remaining * 1.2:
        budget_fit = 3.0
    else:
        budget_fit = -5.0

    # Diversity: +10 if different category from last stop
    diversity = 10.0 if (prev_category is None or prev_category != current_category) else 0.0

    total = base + mood_bonus + distance_penalty + budget_fit + diversity
    return round(max(0, total), 2)
