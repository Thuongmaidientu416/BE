"""
WanderHUB AI — Layer 3: Recommendation Engine
Scores providers and builds optimized itineraries using real database data.
"""

from __future__ import annotations
import hashlib
import random
import sqlite3

from utils.geo import haversine_km, estimate_travel_minutes
from utils.scoring import calculate_recommendation_score
from ai.data_engine import parse_time
from ai.knn_recommender import build_intent_vector, knn_similarity_score


def _fetch_user_affinity(conn: sqlite3.Connection, user_id: int | None) -> tuple[dict[int, float], dict[str, float]]:
    """Return provider/category boosts learned from a user's prior interactions."""
    if not user_id:
        return {}, {}

    try:
        provider_rows = conn.execute(
            """
            SELECT provider_id, SUM(weight) AS boost
            FROM user_interactions
            WHERE user_id = ?
              AND provider_id IS NOT NULL
            GROUP BY provider_id
            """,
            (user_id,),
        ).fetchall()

        category_rows = conn.execute(
            """
            SELECT c.code AS category_code, SUM(ui.weight) AS boost
            FROM user_interactions ui
            JOIN providers p ON p.id = ui.provider_id
            JOIN categories c ON c.id = p.category_id
            WHERE ui.user_id = ?
              AND ui.provider_id IS NOT NULL
            GROUP BY c.code
            """,
            (user_id,),
        ).fetchall()
    except Exception:
        return {}, {}

    provider_boosts = {
        int(row["provider_id"]): max(-8.0, min(10.0, float(row["boost"] or 0) * 1.2))
        for row in provider_rows
    }
    category_boosts = {
        row["category_code"]: max(-5.0, min(7.0, float(row["boost"] or 0) * 0.6))
        for row in category_rows
    }
    return provider_boosts, category_boosts


def _fetch_exposure_penalties(conn: sqlite3.Connection) -> dict[int, float]:
    """Penalize providers that have appeared too often in recent recommendations."""
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        rows = conn.execute(
            """
            SELECT provider_id, COUNT(*) AS exposure_count
            FROM recommendation_logs
            WHERE provider_id IS NOT NULL
              AND created_at >= ?
            GROUP BY provider_id
            """,
            (cutoff,)
        ).fetchall()
    except Exception:
        return {}

    return {
        int(row["provider_id"]): min(10.0, float(row["exposure_count"] or 0) * 1.1)
        for row in rows
    }


def _stable_rank_offset(context: dict, provider_id: int, step_idx: int) -> float:
    """Jitter per-session so near-top candidates rotate on each new generation."""
    seed = "|".join(
        [
            str(context.get("mood_input", "")),
            str(context.get("district", "")),
            str(context.get("time_start", "")),
            str(context.get("budget_max", "")),
            str(step_idx),
            str(provider_id),
            str(context.get("session_seed", "")),
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return (bucket - 0.5) * 7.0


def _pick_balanced_candidate(scored: list[tuple[float, float, dict]], context: dict, step_idx: int) -> tuple[float, float, dict]:
    """Weighted-random selection from near-top candidates so each generation feels fresh."""
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    shortlist = [item for item in scored if item[0] >= top_score - 9.0][:8]
    if len(shortlist) <= 1:
        return scored[0]
    # Rank-based weights: position 1 gets weight N, position N gets weight 1.
    # Higher quality candidates are still more likely, but all have a real chance.
    weights = [len(shortlist) - i for i in range(len(shortlist))]
    return random.choices(shortlist, weights=weights, k=1)[0]


def _fetch_candidates(
    conn: sqlite3.Connection,
    district: str,
    category_code: str,
    avoid_ids: set[int],
    mood_codes: list[str],
    limit: int = 30,
) -> list[dict]:
    """Fetch candidate providers for a given category, prioritizing the preferred district."""
    avoid_params = list(avoid_ids) if avoid_ids else [-1]
    placeholders_ids = ",".join("?" for _ in avoid_params)
    placeholders_moods = ",".join("?" for _ in mood_codes)

    # Query: prefer district match, join moods to check match, order by ai_base_score
    query = f"""
        SELECT DISTINCT
            v.provider_id,
            v.provider_name AS title,
            v.district_name AS district,
            v.category_code,
            v.category_name AS category,
            v.role_code,
            v.role_name AS role,
            v.price_min_vnd,
            v.price_max_vnd,
            v.avg_duration_min,
            v.wanderhub_score,
            v.ai_base_score,
            v.data_compatibility,
            v.deal_viability,
            v.primary_image_url AS image_url,
            v.latitude,
            v.longitude,
            v.description,
            CASE WHEN v.district_name = ? THEN 1 ELSE 0 END AS district_match,
            CASE WHEN pm_match.mood_id IS NOT NULL THEN 1 ELSE 0 END AS mood_match
        FROM v_recommendation_base v
        LEFT JOIN provider_moods pm_match
            ON pm_match.provider_id = v.provider_id
            AND pm_match.mood_id IN (
                SELECT m.id FROM moods m WHERE m.code IN ({placeholders_moods})
            )
        WHERE v.category_code = ?
          AND v.provider_id NOT IN ({placeholders_ids})
        ORDER BY district_match DESC, mood_match DESC, v.ai_base_score DESC
        LIMIT ?
    """
    params = [
        district,
        *mood_codes,
        category_code,
        *avoid_params,
        limit,
    ]
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _fetch_any_category_candidates(
    conn: sqlite3.Connection,
    district: str,
    avoid_ids: set[int],
    avoid_categories: list[str],
    mood_codes: list[str],
    limit: int = 20,
) -> list[dict]:
    """Fetch candidates across any category (fallback when specific category has no results)."""
    avoid_params = list(avoid_ids) if avoid_ids else [-1]
    placeholders_ids = ",".join("?" for _ in avoid_params)
    placeholders_avoid = ",".join("?" for _ in avoid_categories) if avoid_categories else "'__none__'"
    placeholders_moods = ",".join("?" for _ in mood_codes)

    query = f"""
        SELECT DISTINCT
            v.provider_id,
            v.provider_name AS title,
            v.district_name AS district,
            v.category_code,
            v.category_name AS category,
            v.role_code,
            v.role_name AS role,
            v.price_min_vnd,
            v.price_max_vnd,
            v.avg_duration_min,
            v.wanderhub_score,
            v.ai_base_score,
            v.data_compatibility,
            v.deal_viability,
            v.primary_image_url AS image_url,
            v.latitude,
            v.longitude,
            v.description,
            CASE WHEN v.district_name = ? THEN 1 ELSE 0 END AS district_match,
            CASE WHEN pm_match.mood_id IS NOT NULL THEN 1 ELSE 0 END AS mood_match
        FROM v_recommendation_base v
        LEFT JOIN provider_moods pm_match
            ON pm_match.provider_id = v.provider_id
            AND pm_match.mood_id IN (
                SELECT m.id FROM moods m WHERE m.code IN ({placeholders_moods})
            )
        WHERE v.provider_id NOT IN ({placeholders_ids})
          AND v.category_code NOT IN ({placeholders_avoid})
        ORDER BY district_match DESC, mood_match DESC, v.ai_base_score DESC
        LIMIT ?
    """
    params = [
        district,
        *mood_codes,
        *avoid_params,
        *avoid_categories,
        limit,
    ]
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def generate_itinerary(
    conn: sqlite3.Connection,
    context: dict,
    rules: dict,
) -> list[dict]:
    """
    Layer 3 — Build an optimized itinerary.

    Algorithm:
    1. Get category flow from Layer 2 rules
    2. For each slot, fetch candidates matching the target category
    3. Score each candidate with composite scoring
    4. Select the best candidate
    5. Calculate arrival times and costs
    6. Generate a reason for each selection

    Returns: list of itinerary stop dicts
    """
    category_flow = rules["category_flow"]
    moods = context["moods"]
    district = context["district"]
    budget_max = context["budget_max"]
    avoid_categories = rules["avoid_categories"]
    category_boosts = rules["category_boosts"]
    max_stops = rules["max_stops"]
    user_id = context.get("user", {}).get("id") if context.get("user") else None
    provider_boosts, learned_category_boosts = _fetch_user_affinity(conn, user_id)
    exposure_penalties = _fetch_exposure_penalties(conn)
    intent_vector = build_intent_vector(context, rules)

    # Parse start time
    start_h, start_m = parse_time(context["time_start"])
    current_time_min = start_h * 60 + start_m

    used_ids: set[int] = set()
    remaining_budget = budget_max
    prev_category: str | None = None
    prev_lat: float | None = None
    prev_lon: float | None = None
    stops: list[dict] = []

    for step_idx, target_category in enumerate(category_flow[:max_stops]):
        # Skip avoided categories
        if target_category in avoid_categories:
            # Try the next preferred category
            alternatives = [c for c in rules.get("mood_category_affinity", [])
                           if c not in avoid_categories and c != prev_category]
            target_category = alternatives[0] if alternatives else "food"

        # Fetch candidates
        candidates = _fetch_candidates(
            conn, district, target_category, used_ids, moods, limit=25
        )

        # Fallback: try any category if no candidates
        if not candidates:
            candidates = _fetch_any_category_candidates(
                conn, district, used_ids, avoid_categories, moods, limit=20
            )

        if not candidates:
            continue  # No providers available

        # Score each candidate
        scored = []
        for c in candidates:
            # Calculate distance from previous stop
            dist_km = 0.0
            if prev_lat is not None and c["latitude"] and c["longitude"]:
                dist_km = haversine_km(prev_lat, prev_lon, c["latitude"], c["longitude"])

            price_max = c["price_max_vnd"] or 0
            base_score = c["ai_base_score"] or 50

            # Apply category boost
            boost = category_boosts.get(c["category_code"], 0)
            boost += learned_category_boosts.get(c["category_code"], 0)
            boost += provider_boosts.get(c["provider_id"], 0)
            boost -= exposure_penalties.get(c["provider_id"], 0)
            adjusted_base = base_score + boost

            score = calculate_recommendation_score(
                ai_base_score=adjusted_base,
                mood_match=bool(c.get("mood_match")),
                distance_km=dist_km,
                budget_remaining=remaining_budget,
                price_max=price_max,
                prev_category=prev_category,
                current_category=c["category_code"],
            )
            knn_score = knn_similarity_score(c, intent_vector)
            c["knn_similarity"] = knn_score
            quality_score = adjusted_base
            score = round((score * 0.40) + (knn_score * 0.45) + (quality_score * 0.15), 2)
            scored.append((score, dist_km, c))

        # Select a balanced near-top candidate instead of always taking the same top-1.
        best_score, best_dist, best = _pick_balanced_candidate(scored, context, step_idx)

        # Calculate arrival time
        travel_min = 0
        if prev_lat is not None and best["latitude"] and best["longitude"]:
            travel_min = estimate_travel_minutes(best_dist, context["transport_mode"])

        arrival_min = current_time_min + travel_min
        arrival_h = (arrival_min // 60) % 24
        arrival_m = arrival_min % 60

        duration = best["avg_duration_min"] or 60
        cost = best["price_max_vnd"] or 0
        # Use midpoint of price range as estimate
        if best["price_min_vnd"] and best["price_max_vnd"]:
            cost = (best["price_min_vnd"] + best["price_max_vnd"]) // 2

        # Generate reason
        reason = _generate_reason(best, context, rules, best_score)

        stop = {
            "step": step_idx + 1,
            "provider_id": best["provider_id"],
            "title": best["title"],
            "district": best["district"],
            "category": best["category"],
            "category_code": best["category_code"],
            "role": best["role"],
            "arrival_time": f"{arrival_h:02d}:{arrival_m:02d}",
            "duration_min": duration,
            "cost_estimated": cost,
            "avg_price_vnd": cost,
            "reason": reason,
            "image_url": best.get("image_url"),
            "latitude": best.get("latitude"),
            "longitude": best.get("longitude"),
            "score": best_score,
            "knn_similarity": best.get("knn_similarity"),
        }
        stops.append(stop)

        # Update state for next iteration
        used_ids.add(best["provider_id"])
        remaining_budget -= cost
        prev_category = best["category_code"]
        prev_lat = best.get("latitude")
        prev_lon = best.get("longitude")
        current_time_min = arrival_min + duration

    return stops


def find_commercial_suggestions(
    conn: sqlite3.Connection,
    context: dict,
    rules: dict,
    exclude_ids: set[int],
    limit: int = 2,
) -> list[dict]:
    """Return partner-ready places outside the main AI route."""
    moods = context.get("moods") or ["chill"]
    district = context.get("district")
    avoid_params = list(exclude_ids) if exclude_ids else [-1]
    placeholders_ids = ",".join("?" for _ in avoid_params)
    placeholders_moods = ",".join("?" for _ in moods)
    preferred_categories = list(dict.fromkeys([
        *(rules.get("mood_category_affinity") or []),
        *(rules.get("category_flow") or []),
    ]))[:5]
    placeholders_categories = ",".join("?" for _ in preferred_categories) if preferred_categories else "'__none__'"

    query = f"""
        SELECT DISTINCT
            v.provider_id,
            v.provider_name AS title,
            v.district_name AS district,
            v.category_code,
            v.category_name AS category,
            v.role_code,
            v.role_name AS role,
            v.price_min_vnd,
            v.price_max_vnd,
            v.avg_duration_min,
            v.wanderhub_score,
            v.ai_base_score,
            v.data_compatibility,
            v.deal_viability,
            v.primary_image_url AS image_url,
            v.latitude,
            v.longitude,
            v.description,
            CASE WHEN v.district_name = ? THEN 1 ELSE 0 END AS district_match,
            CASE WHEN v.category_code IN ({placeholders_categories}) THEN 1 ELSE 0 END AS category_match,
            CASE WHEN pm_match.mood_id IS NOT NULL THEN 1 ELSE 0 END AS mood_match
        FROM v_recommendation_base v
        LEFT JOIN provider_moods pm_match
            ON pm_match.provider_id = v.provider_id
            AND pm_match.mood_id IN (
                SELECT m.id FROM moods m WHERE m.code IN ({placeholders_moods})
            )
        WHERE v.provider_id NOT IN ({placeholders_ids})
          AND (
            v.deal_viability >= 4
            OR v.role_code IN ('premium', 'exploratory')
            OR v.wanderhub_score >= 82
          )
        ORDER BY
            district_match DESC,
            category_match DESC,
            v.deal_viability DESC,
            mood_match DESC,
            v.ai_base_score DESC
        LIMIT ?
    """
    params = [
        district,
        *preferred_categories,
        *moods,
        *avoid_params,
        max(limit * 4, 8),
    ]
    rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    if not rows:
        return []

    intent_vector = build_intent_vector(context, rules)
    scored: list[tuple[float, dict]] = []
    for row in rows:
        row["commercial_priority"] = True
        knn_score = knn_similarity_score(row, intent_vector)
        deal_score = (row.get("deal_viability") or 3) * 20
        district_bonus = 8 if row.get("district_match") else 0
        category_bonus = 5 if row.get("category_match") else 0
        score = round(knn_score * 0.55 + deal_score * 0.25 + (row.get("ai_base_score") or 50) * 0.15 + district_bonus + category_bonus, 2)
        row["knn_similarity"] = knn_score
        row["score"] = min(score, 99.0)
        scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    suggestions: list[dict] = []
    used_categories: set[str] = set()
    for _, item in scored:
        if item["category_code"] in used_categories and len(suggestions) < limit - 1:
            continue
        cost = item.get("price_max_vnd") or 0
        if item.get("price_min_vnd") and item.get("price_max_vnd"):
            cost = (item["price_min_vnd"] + item["price_max_vnd"]) // 2
        item.update(
            {
                "step": 0,
                "arrival_time": "Pick later",
                "duration_min": item.get("avg_duration_min") or 60,
                "cost_estimated": cost,
                "avg_price_vnd": cost,
                "business_tag": "partner_seed",
                "reason": "Gợi ý thêm vì phù hợp mood, có tiềm năng hợp tác hoặc ưu đãi thương mại để khách chọn thêm.",
            }
        )
        suggestions.append(item)
        used_categories.add(item["category_code"])
        if len(suggestions) >= limit:
            break
    return suggestions


def find_replacement(
    conn: sqlite3.Connection,
    exclude_ids: set[int],
    target_category_code: str,
    district: str,
    moods: list[str],
    budget_remaining: int,
    prev_lat: float | None = None,
    prev_lon: float | None = None,
) -> dict | None:
    """Find a single replacement provider for re-routing."""
    candidates = _fetch_candidates(
        conn, district, target_category_code, exclude_ids, moods, limit=15
    )
    if not candidates:
        candidates = _fetch_any_category_candidates(
            conn, district, exclude_ids, [target_category_code], moods, limit=15
        )
    if not candidates:
        return None

    # Score and pick best
    exposure_penalties = _fetch_exposure_penalties(conn)
    intent_vector = build_intent_vector(
        {
            "moods": moods,
            "mood_input": " ".join(moods),
            "budget_max": budget_remaining,
        },
        {
            "mood_category_affinity": [target_category_code],
            "category_flow": [target_category_code],
            "role_preference": [],
        },
    )
    best = None
    best_score = -1
    for c in candidates:
        dist_km = 0.0
        if prev_lat and c["latitude"] and c["longitude"]:
            dist_km = haversine_km(prev_lat, prev_lon, c["latitude"], c["longitude"])

        composite_score = calculate_recommendation_score(
            ai_base_score=(c["ai_base_score"] or 50) - exposure_penalties.get(c["provider_id"], 0),
            mood_match=bool(c.get("mood_match")),
            distance_km=dist_km,
            budget_remaining=budget_remaining,
            price_max=c["price_max_vnd"] or 0,
            prev_category=None,
            current_category=c["category_code"],
        )
        score = round(composite_score * 0.45 + knn_similarity_score(c, intent_vector) * 0.55, 2)
        if score > best_score:
            best_score = score
            best = c

    return best


def _generate_reason(provider: dict, context: dict, rules: dict, score: float) -> str:
    """Generate a human-readable reason for recommending this provider."""
    parts = []

    mood_text = context["mood_input"]
    if provider.get("mood_match"):
        parts.append(f"Phù hợp với mood \"{mood_text}\"")

    role = provider.get("role", "")
    role_reasons = {
        "Core": "dễ ghép vào lịch trình",
        "Premium": "điểm neo chất lượng cao",
        "Experiential": "tạo chiều sâu trải nghiệm",
        "Exploratory": "điểm khám phá thú vị",
    }
    if role in role_reasons:
        parts.append(role_reasons[role])

    ws = provider.get("wanderhub_score")
    if ws and ws >= 75:
        parts.append(f"điểm WanderHUB {ws}/100")

    district = provider.get("district", "")
    if district == context["district"]:
        parts.append(f"nằm trong {district}")

    if not parts:
        parts.append(f"Được đề xuất dựa trên AI score {score:.0f}")

    return "Được đề xuất vì " + ", ".join(parts) + "."
