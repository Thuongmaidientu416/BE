"""
WanderHUB AI — Layer 2: Knowledge Engine
Applies business rules, constraints, and contextual filters.
"""

from __future__ import annotations


# ── Category suitability by time period ──────────────────────────
# Which categories are appropriate for each time period
TIME_CATEGORY_RULES = {
    "morning": {
        "preferred": ["cafe_drink", "checkin", "culture"],
        "avoid": ["nightlife"],
        "boost": {"cafe_drink": 15, "checkin": 10, "culture": 5},
    },
    "afternoon": {
        "preferred": ["cafe_drink", "culture", "checkin", "entertainment", "food"],
        "avoid": ["nightlife"],
        "boost": {"culture": 10, "entertainment": 10, "checkin": 8},
    },
    "evening": {
        "preferred": ["food", "cafe_drink", "checkin", "nightlife"],
        "avoid": [],
        "boost": {"food": 15, "nightlife": 10, "cafe_drink": 8},
    },
    "night": {
        "preferred": ["nightlife", "food", "cafe_drink"],
        "avoid": ["culture", "checkin"],
        "boost": {"nightlife": 20, "food": 10},
    },
}

# ── Mood → category affinity ────────────────────────────────────
MOOD_CATEGORY_AFFINITY = {
    "chill": ["cafe_drink", "checkin"],
    "date": ["cafe_drink", "food", "checkin", "nightlife"],
    "group": ["food", "entertainment", "cafe_drink", "nightlife", "checkin"],
    "healing": ["cafe_drink", "checkin"],
    "culture": ["culture", "checkin"],
    "checkin": ["checkin", "culture"],
    "foodie": ["food", "cafe_drink"],
    "nightlife": ["nightlife", "food"],
    "solo": ["cafe_drink", "culture", "checkin"],
    "hidden_gem": ["cafe_drink", "food", "checkin"],
    "premium": ["food", "nightlife", "cafe_drink"],
    "budget": ["checkin", "food", "cafe_drink"],
    "work_study": ["cafe_drink"],
    "creative": ["culture", "cafe_drink", "entertainment"],
    "must_try": ["food", "checkin", "culture"],
}

# ── Itinerary flow templates ────────────────────────────────────
# Suggested category sequences for different moods
FLOW_TEMPLATES = {
    "chill": ["cafe_drink", "checkin", "food"],
    "date": ["cafe_drink", "checkin", "food", "nightlife"],
    "group": ["food", "entertainment", "cafe_drink", "nightlife", "checkin"],
    "healing": ["checkin", "cafe_drink", "food"],
    "culture": ["culture", "checkin", "cafe_drink", "food"],
    "checkin": ["checkin", "cafe_drink", "checkin", "food"],
    "foodie": ["food", "cafe_drink", "food", "checkin"],
    "nightlife": ["food", "cafe_drink", "nightlife", "nightlife"],
    "solo": ["cafe_drink", "culture", "checkin", "food"],
    "hidden_gem": ["cafe_drink", "checkin", "food", "cafe_drink"],
    "premium": ["cafe_drink", "food", "checkin", "nightlife"],
    "budget": ["checkin", "checkin", "food", "cafe_drink"],
    "work_study": ["cafe_drink", "cafe_drink", "food"],
    "creative": ["culture", "cafe_drink", "checkin", "food"],
    "must_try": ["checkin", "food", "culture", "cafe_drink"],
}


def apply_rules(context: dict) -> dict:
    """
    Layer 2 — Apply business rules and generate constraints.

    Input: context dict from Layer 1
    Output: rules dict with:
      - category_flow: ordered list of category codes for itinerary
      - category_boosts: score bonuses per category
      - avoid_categories: categories to exclude
      - max_stops: adjusted number of stops
      - budget_per_stop: average budget allocated per stop
      - constraints: list of human-readable rule descriptions
      - role_preference: preferred role types
    """
    moods = context["moods"]
    primary_mood = moods[0]
    time_period = context["time_period"]
    budget_max = context["budget_max"]
    available_minutes = context["available_minutes"]

    constraints = []
    category_boosts = {}
    avoid_categories = set()

    # ── Time-based rules ──
    time_rules = TIME_CATEGORY_RULES.get(time_period, TIME_CATEGORY_RULES["evening"])
    avoid_categories.update(time_rules["avoid"])
    category_boosts.update(time_rules["boost"])

    if time_period == "night":
        constraints.append("Buổi tối muộn: ưu tiên nightlife và ăn khuya, tránh bảo tàng/điểm tham quan.")
    elif time_period == "evening":
        constraints.append("Buổi tối: ưu tiên ăn tối, cafe và các điểm có ánh đèn đẹp.")
    elif time_period == "morning":
        constraints.append("Buổi sáng: ưu tiên cafe, check-in và tham quan văn hóa.")

    # ── Budget rules ──
    if budget_max < 200_000:
        constraints.append("Ngân sách thấp: ưu tiên check-in miễn phí và street food giá rẻ.")
        category_boosts["checkin"] = category_boosts.get("checkin", 0) + 15
        category_boosts["food"] = category_boosts.get("food", 0) + 5
        avoid_categories.discard("checkin")  # ensure checkin is available
    elif budget_max < 400_000:
        constraints.append("Ngân sách vừa phải: cân đối giữa trải nghiệm và chi phí.")
    else:
        constraints.append("Ngân sách thoải mái: có thể chọn premium và fine dining.")
        category_boosts["food"] = category_boosts.get("food", 0) + 10
        category_boosts["nightlife"] = category_boosts.get("nightlife", 0) + 5

    # ── Mood-specific rules ──
    affinity_cats = MOOD_CATEGORY_AFFINITY.get(primary_mood, ["cafe_drink", "food", "checkin"])
    for cat in affinity_cats:
        category_boosts[cat] = category_boosts.get(cat, 0) + 12

    if "date" in moods:
        constraints.append("Mood hẹn hò: ưu tiên không gian riêng tư, đẹp, premium.")
        category_boosts["cafe_drink"] = category_boosts.get("cafe_drink", 0) + 8
    if "foodie" in moods:
        constraints.append("Mood ẩm thực: tập trung nhiều điểm ăn uống.")
    if "hidden_gem" in moods:
        constraints.append("Ưu tiên exploratory role — địa điểm ít người biết.")
    if "budget" in moods:
        constraints.append("Ưu tiên free/budget-friendly locations.")

    # ── Calculate optimal stops ──
    avg_per_stop = 75  # average minutes per stop (including transit)
    max_stops = max(2, min(6, available_minutes // avg_per_stop))

    # ── Budget allocation ──
    budget_per_stop = budget_max // max_stops if max_stops > 0 else budget_max

    # ── Flow template ──
    flow = FLOW_TEMPLATES.get(primary_mood, FLOW_TEMPLATES["chill"])
    # Adjust length to max_stops
    if len(flow) > max_stops:
        flow = flow[:max_stops]
    elif len(flow) < max_stops:
        # Extend with alternating food/cafe
        extras = ["food", "cafe_drink", "checkin"]
        while len(flow) < max_stops:
            flow.append(extras[len(flow) % len(extras)])

    # ── Role preference ──
    role_pref = []
    if "premium" in moods or budget_max > 600_000:
        role_pref.append("premium")
    if "hidden_gem" in moods:
        role_pref.append("exploratory")
    if "culture" in moods:
        role_pref.append("experiential")
    if not role_pref:
        role_pref = ["core", "experiential"]

    return {
        "category_flow": flow,
        "category_boosts": category_boosts,
        "avoid_categories": list(avoid_categories),
        "max_stops": max_stops,
        "budget_per_stop": budget_per_stop,
        "constraints": constraints,
        "role_preference": role_pref,
        "primary_mood": primary_mood,
        "mood_category_affinity": affinity_cats,
    }
