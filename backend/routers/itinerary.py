"""
WanderHUB Backend — Itinerary Router (AI Custom Tour Generation)
"""

from __future__ import annotations
import json
import sqlite3
from fastapi import APIRouter, Depends, HTTPException

from database import get_db_dependency
from models.schemas import (
    ItineraryGenerateRequest,
    ItineraryResponse,
    ItineraryStop,
    RerouteRequest,
    FeedbackRequest,
)
from routers.auth import get_current_user_id
from ai.data_engine import get_user_context
from ai.knowledge_engine import apply_rules
from ai.recommendation import generate_itinerary, find_commercial_suggestions, find_replacement

router = APIRouter(prefix="/api/itinerary", tags=["itinerary"])


def _format_cost(total: int) -> str:
    """Format VND cost as readable string."""
    if total >= 1_000_000:
        return f"{total / 1_000_000:.1f} triệu VNĐ"
    return f"{total:,} VNĐ".replace(",", ".")


def _format_duration(minutes: int) -> str:
    """Format minutes as 'Xh Ym'."""
    h = minutes // 60
    m = minutes % 60
    if h == 0:
        return f"{m}m"
    if m == 0:
        return f"{h}h"
    return f"{h}h {m:02d}m"


@router.post("/generate", response_model=ItineraryResponse)
def generate(
    body: ItineraryGenerateRequest,
    user_id: int | None = Depends(get_current_user_id),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """
    Core AI endpoint: Generate a custom tour itinerary.

    Pipeline:
      Layer 1 (Data Engine) → parse input + user context
      Layer 2 (Knowledge Engine) → apply business rules
      Layer 3 (Recommendation Engine) → score & build itinerary
    """
    # Layer 1: Build context
    context = get_user_context(
        conn=conn,
        user_id=user_id,
        mood_input=body.mood,
        budget_max=body.budget_max,
        time_start=body.time_start,
        time_end=body.time_end,
        district=body.district,
        food_preference=body.food_preference,
        transport=body.transport,
    )

    # Layer 2: Apply rules
    rules = apply_rules(context)

    # Override max_stops if user specified
    if body.max_stops:
        rules["max_stops"] = max(2, min(body.max_stops, 8))
        route_fillers = ["food", "cafe_drink", "checkin", "culture", "entertainment", "nightlife"]
        while len(rules["category_flow"]) < rules["max_stops"]:
            rules["category_flow"].append(route_fillers[len(rules["category_flow"]) % len(route_fillers)])

    session_cursor = conn.execute(
        """
        INSERT INTO recommendation_sessions (
            user_id, mood_input, district, budget_max,
            time_start, time_end, transport_mode,
            parsed_context_json, rules_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            body.mood,
            body.district,
            body.budget_max,
            body.time_start,
            body.time_end,
            body.transport,
            json.dumps(context, ensure_ascii=False, default=str),
            json.dumps(rules, ensure_ascii=False, default=str),
        ),
    )
    session_id = session_cursor.lastrowid

    # Layer 3: Generate itinerary
    stops_data = generate_itinerary(conn, context, rules)

    if not stops_data:
        conn.commit()
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy địa điểm phù hợp. Hãy thử thay đổi quận hoặc mood.",
        )

    # Calculate totals
    total_cost = sum(s["cost_estimated"] for s in stops_data)
    total_duration = sum(s["duration_min"] for s in stops_data)

    # Generate title
    mood_titles = {
        "chill": "Chill Vibes",
        "date": "Date Night",
        "group": "Squad Hangout",
        "foodie": "Food Tour",
        "nightlife": "Night Out",
        "culture": "Culture Walk",
        "healing": "Healing Trip",
        "checkin": "Check-in Tour",
        "hidden_gem": "Hidden Gems Discovery",
        "premium": "Premium Experience",
        "budget": "Budget Explorer",
        "solo": "Solo Adventure",
    }
    primary_mood = rules["primary_mood"]
    title = f"{mood_titles.get(primary_mood, 'Custom Tour')} — {body.district}"

    # Save to DB if user is authenticated
    itinerary_id = None
    if user_id:
        cursor = conn.execute(
            """
            INSERT INTO itineraries (
                user_id, title, mood_code, district_preference,
                budget_min, budget_max, time_start, time_end,
                transport_mode, total_cost_estimated, total_duration_min
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, title, primary_mood, body.district,
                0, body.budget_max, body.time_start, body.time_end,
                body.transport, total_cost, total_duration,
            ),
        )
        itinerary_id = cursor.lastrowid

        for stop in stops_data:
            conn.execute(
                """
                INSERT INTO itinerary_stops (
                    itinerary_id, provider_id, step_order,
                    arrival_time, duration_min, cost_estimated, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    itinerary_id, stop["provider_id"], stop["step"],
                    stop["arrival_time"], stop["duration_min"],
                    stop["cost_estimated"], stop["reason"],
                ),
            )
    conn.execute(
        "UPDATE recommendation_sessions SET itinerary_id = ? WHERE id = ?",
        (itinerary_id, session_id),
    )
    for stop in stops_data:
        conn.execute(
            """
            INSERT INTO recommendation_logs (
                session_id, itinerary_id, provider_id,
                rank_position, score, reason
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                itinerary_id,
                stop["provider_id"],
                stop["step"],
                stop.get("score"),
                stop.get("reason"),
            ),
        )
    conn.commit()

    commercial_data = find_commercial_suggestions(
        conn=conn,
        context=context,
        rules=rules,
        exclude_ids={stop["provider_id"] for stop in stops_data},
        limit=2,
    )

    # Build response
    response_stops = [
        ItineraryStop(
            step=s["step"],
            provider_id=s["provider_id"],
            title=s["title"],
            district=s["district"],
            category=s["category"],
            category_code=s.get("category_code"),
            role=s["role"],
            arrival_time=s["arrival_time"],
            duration_min=s["duration_min"],
            cost_estimated=s["cost_estimated"],
            avg_price_vnd=s.get("avg_price_vnd", s["cost_estimated"]),
            reason=s["reason"],
            description=s.get("description"),
            image_url=s.get("image_url"),
            latitude=s.get("latitude"),
            longitude=s.get("longitude"),
            price_min_vnd=s.get("price_min_vnd"),
            price_max_vnd=s.get("price_max_vnd"),
            score=s.get("score"),
            knn_similarity=s.get("knn_similarity"),
            business_tag=s.get("business_tag"),
        )
        for s in stops_data
    ]
    commercial_suggestions = [
        ItineraryStop(
            step=0,
            provider_id=s["provider_id"],
            title=s["title"],
            district=s["district"],
            category=s["category"],
            category_code=s.get("category_code"),
            role=s["role"],
            arrival_time=s.get("arrival_time", "Pick later"),
            duration_min=s["duration_min"],
            cost_estimated=s["cost_estimated"],
            avg_price_vnd=s.get("avg_price_vnd", s["cost_estimated"]),
            reason=s["reason"],
            description=s.get("description"),
            image_url=s.get("image_url"),
            latitude=s.get("latitude"),
            longitude=s.get("longitude"),
            price_min_vnd=s.get("price_min_vnd"),
            price_max_vnd=s.get("price_max_vnd"),
            score=s.get("score"),
            knn_similarity=s.get("knn_similarity"),
            business_tag=s.get("business_tag"),
        )
        for s in commercial_data
    ]

    return ItineraryResponse(
        itinerary_id=itinerary_id,
        session_id=session_id,
        title=title,
        mood=primary_mood,
        total_cost=_format_cost(total_cost),
        total_duration=_format_duration(total_duration),
        transport=body.transport,
        stops=response_stops,
        commercial_suggestions=commercial_suggestions,
    )


@router.post("/reroute", response_model=ItineraryResponse)
def reroute(
    body: RerouteRequest,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """Replace one stop in an itinerary with a similar alternative."""
    if not body.stops:
        raise HTTPException(status_code=400, detail="No stops provided")
    if body.replace_step < 1 or body.replace_step > len(body.stops):
        raise HTTPException(status_code=400, detail="Invalid step number")

    # Find the stop to replace
    target_idx = body.replace_step - 1
    target_stop = body.stops[target_idx]

    # Collect IDs to exclude (all current stops)
    exclude_ids = {s.provider_id for s in body.stops}

    # Get previous stop for distance calculation
    prev_lat = body.stops[target_idx - 1].latitude if target_idx > 0 else None
    prev_lon = body.stops[target_idx - 1].longitude if target_idx > 0 else None

    # Find replacement — try same category first, then any
    # Look up category_code from DB
    cat_row = conn.execute(
        """
        SELECT c.code FROM providers p
        JOIN categories c ON c.id = p.category_id
        WHERE p.id = ?
        """,
        (target_stop.provider_id,),
    ).fetchone()
    target_cat = cat_row["code"] if cat_row else "food"

    replacement = find_replacement(
        conn=conn,
        exclude_ids=exclude_ids,
        target_category_code=target_cat,
        district=body.district,
        moods=[body.mood],
        budget_remaining=body.budget_max,
        prev_lat=prev_lat,
        prev_lon=prev_lon,
    )

    if not replacement:
        raise HTTPException(status_code=404, detail="Không tìm thấy điểm thay thế phù hợp.")

    # Build new stop
    cost = replacement.get("price_max_vnd", 0)
    if replacement.get("price_min_vnd") and replacement.get("price_max_vnd"):
        cost = (replacement["price_min_vnd"] + replacement["price_max_vnd"]) // 2

    new_stop = ItineraryStop(
        step=body.replace_step,
        provider_id=replacement["provider_id"],
        title=replacement["title"],
        district=replacement["district"],
        category=replacement["category"],
        category_code=replacement.get("category_code"),
        role=replacement["role"],
        arrival_time=target_stop.arrival_time,
        duration_min=replacement.get("avg_duration_min", 60),
        cost_estimated=cost,
        avg_price_vnd=cost,
        reason=f"Thay thế cho {target_stop.title} — được đề xuất dựa trên AI scoring.",
        description=replacement.get("description"),
        image_url=replacement.get("image_url"),
        latitude=replacement.get("latitude"),
        longitude=replacement.get("longitude"),
        price_min_vnd=replacement.get("price_min_vnd"),
        price_max_vnd=replacement.get("price_max_vnd"),
        score=replacement.get("ai_base_score"),
    )

    # Rebuild stops list
    new_stops = list(body.stops)
    new_stops[target_idx] = new_stop

    total_cost = sum(s.cost_estimated for s in new_stops)
    total_duration = sum(s.duration_min for s in new_stops)

    return ItineraryResponse(
        itinerary_id=body.itinerary_id,
        title=f"Re-routed — {body.district}",
        mood=body.mood,
        total_cost=_format_cost(total_cost),
        total_duration=_format_duration(total_duration),
        transport="Be / Xanh SM",
        stops=new_stops,
    )


@router.get("/{itinerary_id}")
def get_itinerary(
    itinerary_id: int,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """Retrieve a saved itinerary."""
    row = conn.execute(
        "SELECT * FROM itineraries WHERE id = ?", (itinerary_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    stops = conn.execute(
        """
        SELECT
            s.step_order AS step,
            s.provider_id,
            p.name AS title,
            d.name AS district,
            c.name AS category,
            r.name AS role,
            s.arrival_time,
            s.duration_min,
            s.cost_estimated,
            s.reason,
            pm.image_url,
            p.latitude,
            p.longitude
        FROM itinerary_stops s
        JOIN providers p ON p.id = s.provider_id
        JOIN districts d ON d.id = p.district_id
        JOIN categories c ON c.id = p.category_id
        JOIN roles r ON r.id = p.role_id
        LEFT JOIN provider_media pm ON pm.provider_id = p.id AND pm.is_primary = 1
        WHERE s.itinerary_id = ?
        ORDER BY s.step_order
        """,
        (itinerary_id,),
    ).fetchall()

    itinerary = dict(row)
    itinerary["stops"] = [dict(s) for s in stops]
    return itinerary


@router.post("/{itinerary_id}/feedback")
def submit_feedback(
    itinerary_id: int,
    body: FeedbackRequest,
    user_id: int = Depends(get_current_user_id),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """Submit user feedback for an itinerary."""
    conn.execute(
        "INSERT INTO itinerary_feedback (itinerary_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
        (itinerary_id, user_id, body.rating, body.comment),
    )
    conn.commit()
    return {"success": True, "message": "Cảm ơn bạn đã đánh giá!"}
