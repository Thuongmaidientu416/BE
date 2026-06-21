"""
WanderHUB AI — Layer 1: Data Engine
Collects real user context, intent parsing, and time context from the database.
"""

from __future__ import annotations
import sqlite3
from datetime import datetime


# ── Mood keyword mapping ─────────────────────────────────────────
MOOD_KEYWORDS = {
    "chill": ["chill", "thư giãn", "relax", "nhẹ nhàng", "yên tĩnh"],
    "date": ["date", "hẹn hò", "lãng mạn", "romantic", "couple"],
    "group": ["nhóm", "group", "bạn bè", "team", "đông người"],
    "healing": ["healing", "chữa lành", "bình yên", "thiền"],
    "culture": ["văn hóa", "culture", "bảo tàng", "lịch sử", "museum"],
    "checkin": ["checkin", "check-in", "chụp ảnh", "sống ảo", "landmark"],
    "foodie": ["ăn", "food", "foodie", "ẩm thực", "quán ăn", "seafood", "ốc"],
    "nightlife": ["bar", "nightlife", "đêm", "pub", "club"],
    "solo": ["solo", "một mình", "alone"],
    "hidden_gem": ["hidden", "gem", "ẩn", "bí mật", "ngóc ngách"],
    "premium": ["premium", "cao cấp", "luxury", "sang", "đẳng cấp"],
    "budget": ["rẻ", "budget", "tiết kiệm", "free", "miễn phí"],
    "work_study": ["work", "study", "làm việc", "học bài", "co-working"],
    "creative": ["creative", "sáng tạo", "art", "nghệ thuật"],
    "must_try": ["must try", "phải thử", "nổi tiếng", "hot"],
}

# ── Time-of-day classification ───────────────────────────────────
TIME_PERIODS = {
    "morning": (6, 11),
    "afternoon": (11, 17),
    "evening": (17, 21),
    "night": (21, 6),
}


def classify_time_period(hour: int) -> str:
    """Classify hour into morning/afternoon/evening/night."""
    if 6 <= hour < 11:
        return "morning"
    elif 11 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def parse_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' string into (hour, minute)."""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def detect_moods(text: str) -> list[str]:
    """Detect mood codes from free-text input."""
    lower = text.lower()
    detected = []
    for mood_code, keywords in MOOD_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            detected.append(mood_code)
    return detected or ["chill"]  # Default to chill


def get_user_context(
    conn: sqlite3.Connection,
    user_id: int | None,
    mood_input: str,
    budget_max: int,
    time_start: str,
    time_end: str,
    district: str,
    food_preference: str | None = None,
    transport: str = "Be / Xanh SM",
) -> dict:
    """
    Layer 1 — Build complete user context from DB and input.

    Returns a structured dict with:
    - user profile (from DB if authenticated)
    - detected moods
    - time context (period, available minutes)
    - location context
    - budget context
    """
    # ── User profile ──
    user_data = None
    if user_id:
        row = conn.execute(
            "SELECT id, name, email, preferences_json, budget_default FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row:
            user_data = dict(row)

    # ── Parse times ──
    start_h, start_m = parse_time(time_start)
    end_h, end_m = parse_time(time_end)

    # Calculate available minutes
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m
    if end_total <= start_total:
        end_total += 24 * 60  # crosses midnight
    available_minutes = end_total - start_total

    # ── Detect moods ──
    moods = detect_moods(mood_input)

    # ── Current time context ──
    now = datetime.now()
    time_period = classify_time_period(start_h)

    # ── Transport mode normalization ──
    transport_mode = "car"
    transport_lower = transport.lower()
    if "bộ" in transport_lower or "walk" in transport_lower:
        transport_mode = "walk"
    elif "máy" in transport_lower or "xe máy" in transport_lower:
        transport_mode = "motorbike"

    return {
        "user": user_data,
        "moods": moods,
        "mood_input": mood_input,
        "budget_max": budget_max,
        "time_start": time_start,
        "time_end": time_end,
        "start_hour": start_h,
        "available_minutes": available_minutes,
        "time_period": time_period,
        "district": district,
        "food_preference": food_preference,
        "transport": transport,
        "transport_mode": transport_mode,
        "current_time": now.strftime("%H:%M"),
        "current_date": now.strftime("%Y-%m-%d"),
    }
