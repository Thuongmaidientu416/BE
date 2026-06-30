"""
WanderHUB Backend — Itinerary Router (AI Custom Tour Generation)
"""

from __future__ import annotations
from typing import Any
import json
import random
import traceback
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

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
from utils.place_details import fetch_place_details

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


@router.post("/generate")
def generate(
    body: ItineraryGenerateRequest,
    user_id: int | None = Depends(get_current_user_id),
    conn: Any = Depends(get_db_dependency),
):
    """
    Core AI endpoint: Generate a custom tour itinerary.

    Pipeline:
      Layer 1 (Data Engine) → parse input + user context
      Layer 2 (Knowledge Engine) → apply business rules
      Layer 3 (Recommendation Engine) → score & build itinerary
    """
    try:
        return _generate_inner(body, user_id, conn)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GENERATE ERROR] {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"detail": f"{type(e).__name__}: {str(e)}"})


def _generate_inner(body: ItineraryGenerateRequest, user_id, conn):
    # Enforce Basic plan limit: 1 itinerary per 20 days (skip for auto-generated previews)
    if user_id and not body.is_auto_generate:
        plan_row = conn.execute(
            "SELECT plan_key FROM user_plans WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if plan_row and plan_row["plan_key"] == "basic":
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
            last_row = conn.execute(
                """
                SELECT created_at FROM itineraries
                WHERE user_id = ?
                  AND created_at > ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id, cutoff),
            ).fetchone()
            if last_row:
                last_dt = datetime.fromisoformat(last_row["created_at"])
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                reset_at = last_dt + timedelta(days=20)
                now = datetime.now(timezone.utc)
                days_left = max(1, (reset_at - now).days + 1)
                raise HTTPException(
                    status_code=429,
                    detail=f"Gói Basic giới hạn 1 lịch trình mỗi 20 ngày. Reset sau {days_left} ngày.",
                )

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

    context["session_seed"] = random.random()

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

    # Save to DB if user is authenticated and this is a real (non-auto) generation
    itinerary_id = None
    if user_id and not body.is_auto_generate:
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

    # Enrich every stop with truthful OSM detail (cuisine, dishes, amenities, hours, address)
    detail_map = fetch_place_details(
        conn,
        [s["provider_id"] for s in stops_data] + [s["provider_id"] for s in commercial_data],
    )
    for s in stops_data:
        s.update(detail_map.get(s["provider_id"], {}))
    for s in commercial_data:
        s.update(detail_map.get(s["provider_id"], {}))

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
            cuisine=s.get("cuisine"),
            must_try=s.get("must_try") or [],
            highlights=s.get("highlights") or [],
            address=s.get("address"),
            opening_hours=s.get("opening_hours"),
            phone=s.get("phone"),
            website=s.get("website"),
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
            cuisine=s.get("cuisine"),
            must_try=s.get("must_try") or [],
            highlights=s.get("highlights") or [],
            address=s.get("address"),
            opening_hours=s.get("opening_hours"),
            phone=s.get("phone"),
            website=s.get("website"),
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
    conn: Any = Depends(get_db_dependency),
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

    rdet = fetch_place_details(conn, [replacement["provider_id"]]).get(replacement["provider_id"], {})

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
        cuisine=rdet.get("cuisine"),
        must_try=rdet.get("must_try") or [],
        highlights=rdet.get("highlights") or [],
        address=rdet.get("address"),
        opening_hours=rdet.get("opening_hours"),
        phone=rdet.get("phone"),
        website=rdet.get("website"),
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


@router.get("/history/me")
def get_my_history(
    user_id: int = Depends(get_current_user_id),
    conn: Any = Depends(get_db_dependency),
):
    """Retrieve saved itineraries for the current logged-in user."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Bạn chưa đăng nhập.")
        
    rows = conn.execute(
        """
        SELECT id, title, mood_code, district_preference,
               total_cost_estimated, total_duration_min, transport_mode, created_at
        FROM itineraries
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()

    result = []
    for r in rows:
        itinerary_id = r["id"]
        stops = conn.execute(
            """
            SELECT s.step_order AS step, p.name AS title, d.name AS district, c.name AS category,
                   s.arrival_time, s.duration_min, s.cost_estimated, s.reason, pm.image_url,
                   p.latitude, p.longitude, p.id as provider_id
            FROM itinerary_stops s
            JOIN providers p ON p.id = s.provider_id
            JOIN districts d ON d.id = p.district_id
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN provider_media pm ON pm.provider_id = p.id AND pm.is_primary = 1
            WHERE s.itinerary_id = ?
            ORDER BY s.step_order
            """,
            (itinerary_id,),
        ).fetchall()
        
        item = dict(r)
        item["stops"] = [dict(s) for s in stops]
        item["total_cost"] = _format_cost(r["total_cost_estimated"])
        item["total_duration"] = _format_duration(r["total_duration_min"])
        result.append(item)
    return result


@router.get("/popular")
def get_popular_itineraries(
    conn: Any = Depends(get_db_dependency),
):
    """Retrieve popular itineraries or return curated ones if database is empty."""
    rows = conn.execute(
        """
        SELECT i.id, i.title, i.mood_code, i.district_preference,
               i.total_cost_estimated, i.total_duration_min, i.transport_mode, i.created_at,
               COUNT(ui.id) as select_count
        FROM itineraries i
        LEFT JOIN user_interactions ui ON ui.itinerary_id = i.id AND ui.event_type IN ('choose', 'save')
        GROUP BY i.id
        ORDER BY select_count DESC, i.created_at DESC
        LIMIT 4
        """
    ).fetchall()

    result = []
    for r in rows:
        if r["id"] is None:
            continue
        itinerary_id = r["id"]
        stops = conn.execute(
            """
            SELECT s.step_order AS step, p.name AS title, d.name AS district, c.name AS category,
                   s.arrival_time, s.duration_min, s.cost_estimated, s.reason, pm.image_url,
                   p.latitude, p.longitude, p.id as provider_id
            FROM itinerary_stops s
            JOIN providers p ON p.id = s.provider_id
            JOIN districts d ON d.id = p.district_id
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN provider_media pm ON pm.provider_id = p.id AND pm.is_primary = 1
            WHERE s.itinerary_id = ?
            ORDER BY s.step_order
            """,
            (itinerary_id,),
        ).fetchall()
        
        item = dict(r)
        item["stops"] = [dict(s) for s in stops]
        item["total_cost"] = _format_cost(r["total_cost_estimated"])
        item["total_duration"] = _format_duration(r["total_duration_min"])
        result.append(item)

    if len(result) >= 3:
        return result

    # Return fallbacks if not enough itineraries
    curated = [
        {
            "id": 9991,
            "title": "Tour Trải Nghiệm Cafe & Check-in Quận 1",
            "mood_code": "chill",
            "district_preference": "Quận 1",
            "total_cost_estimated": 280000,
            "total_duration_min": 150,
            "transport_mode": "Tự đi xe máy",
            "created_at": "2026-06-29T12:00:00Z",
            "select_count": 42,
            "stops": [
                {
                    "step": 1,
                    "provider_id": 13,
                    "title": "Cộng Cà Phê",
                    "district": "Quận 1",
                    "category": "Quán uống / cafe",
                    "arrival_time": "15:00",
                    "duration_min": 45,
                    "cost_estimated": 60000,
                    "reason": "Không gian hoài niệm phù hợp để bắt đầu buổi chiều nhẹ nhàng.",
                    "image_url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&h=400&fit=crop",
                    "latitude": 10.776,
                    "longitude": 106.701
                },
                {
                    "step": 2,
                    "provider_id": 1,
                    "title": "Trần Pizza",
                    "district": "Quận 1",
                    "category": "Quán ăn / nhà hàng",
                    "arrival_time": "16:00",
                    "duration_min": 60,
                    "cost_estimated": 150000,
                    "reason": "Điểm nạp năng lượng lý tưởng với món Pizza nướng củi thơm ngon.",
                    "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&h=400&fit=crop",
                    "latitude": 10.778,
                    "longitude": 106.702
                },
                {
                    "step": 3,
                    "provider_id": 3,
                    "title": "Đảo Space",
                    "district": "Quận 1",
                    "category": "Quán uống / cafe",
                    "arrival_time": "17:15",
                    "duration_min": 45,
                    "cost_estimated": 70000,
                    "reason": "Kết thúc buổi chiều tại quán cafe hiện đại, lý tưởng để trò chuyện.",
                    "image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&h=400&fit=crop",
                    "latitude": 10.775,
                    "longitude": 106.698
                }
            ]
        },
        {
            "id": 9992,
            "title": "Food Tour Ẩm Thực Vỉa Hè Sài Gòn Q5",
            "mood_code": "foodie",
            "district_preference": "Quận 5",
            "total_cost_estimated": 200000,
            "total_duration_min": 160,
            "transport_mode": "Tự đi xe máy",
            "created_at": "2026-06-29T15:00:00Z",
            "select_count": 35,
            "stops": [
                {
                    "step": 1,
                    "provider_id": 22,
                    "title": "Cơm Tấm Huỳnh Mẫn Đạt",
                    "district": "Quận 5",
                    "category": "Quán ăn / nhà hàng",
                    "arrival_time": "18:00",
                    "duration_min": 50,
                    "cost_estimated": 55000,
                    "reason": "Đặc sản cơm tấm Sài Gòn thơm nức mũi, sườn nướng mọng nước cực đã.",
                    "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=400&fit=crop",
                    "latitude": 10.755,
                    "longitude": 106.678
                },
                {
                    "step": 2,
                    "provider_id": 11,
                    "title": "CAFE 68",
                    "district": "Quận 5",
                    "category": "Quán uống / cafe",
                    "arrival_time": "19:00",
                    "duration_min": 45,
                    "cost_estimated": 45000,
                    "reason": "Nơi nghỉ chân hoàn hảo sau bữa tối no căng bụng.",
                    "image_url": "https://images.unsplash.com/photo-1498804103079-a6351b050096?w=600&h=400&fit=crop",
                    "latitude": 10.752,
                    "longitude": 106.675
                },
                {
                    "step": 3,
                    "provider_id": 30,
                    "title": "Hồ Thị Kỷ",
                    "district": "Quận 5",
                    "category": "Quán ăn / nhà hàng",
                    "arrival_time": "20:00",
                    "duration_min": 65,
                    "cost_estimated": 100000,
                    "reason": "Thiên đường ẩm thực ăn vặt sầm uất bậc nhất Sài Thành.",
                    "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=400&fit=crop",
                    "latitude": 10.765,
                    "longitude": 106.672
                }
            ]
        },
        {
            "id": 9993,
            "title": "Vibe Đêm Lãng Mạn & Nightlife Quận 1",
            "mood_code": "date",
            "district_preference": "Quận 1",
            "total_cost_estimated": 550000,
            "total_duration_min": 170,
            "transport_mode": "Thuê xe",
            "created_at": "2026-06-29T20:00:00Z",
            "select_count": 29,
            "stops": [
                {
                    "step": 1,
                    "provider_id": 15,
                    "title": "Nhà Hàng Hương Việt",
                    "district": "Quận 1",
                    "category": "Quán ăn / nhà hàng",
                    "arrival_time": "19:30",
                    "duration_min": 60,
                    "cost_estimated": 280000,
                    "reason": "Không gian ấm cúng, sang trọng, thực đơn phong phú thích hợp cho các buổi hẹn hò.",
                    "image_url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&h=400&fit=crop",
                    "latitude": 10.774,
                    "longitude": 106.703
                },
                {
                    "step": 2,
                    "provider_id": 12,
                    "title": "The Hipster",
                    "district": "Quận 1",
                    "category": "Nightlife / bar",
                    "arrival_time": "20:45",
                    "duration_min": 70,
                    "cost_estimated": 200000,
                    "reason": "Nhạc hay, đồ uống pha chế cực chất, view phố phường chill vô cùng.",
                    "image_url": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=600&h=400&fit=crop",
                    "latitude": 10.773,
                    "longitude": 106.701
                },
                {
                    "step": 3,
                    "provider_id": 9,
                    "title": "K COFFEE",
                    "district": "Quận 1",
                    "category": "Quán uống / cafe",
                    "arrival_time": "22:05",
                    "duration_min": 40,
                    "cost_estimated": 70000,
                    "reason": "Khép lại một đêm trọn vẹn tại góc phố nhộn nhịp cùng ly bạc xỉu đá thơm ngậy.",
                    "image_url": "https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=600&h=400&fit=crop",
                    "latitude": 10.776,
                    "longitude": 106.702
                }
            ]
        }
    ]

    for c in curated:
        c["total_cost"] = _format_cost(c["total_cost_estimated"])
        c["total_duration"] = _format_duration(c["total_duration_min"])

    return curated


@router.get("/{itinerary_id}")
def get_itinerary(
    itinerary_id: int,
    conn: Any = Depends(get_db_dependency),
):
    """Retrieve a saved itinerary."""
    if itinerary_id in (9991, 9992, 9993):
        curated_list = [
            {
                "id": 9991,
                "title": "Tour Trải Nghiệm Cafe & Check-in Quận 1",
                "mood_code": "chill",
                "district_preference": "Quận 1",
                "total_cost_estimated": 280000,
                "total_duration_min": 150,
                "transport_mode": "Tự đi xe máy",
                "created_at": "2026-06-29T12:00:00Z",
                "stops": [
                    {
                        "step": 1,
                        "provider_id": 13,
                        "title": "Cộng Cà Phê",
                        "district": "Quận 1",
                        "category": "Quán uống / cafe",
                        "arrival_time": "15:00",
                        "duration_min": 45,
                        "cost_estimated": 60000,
                        "reason": "Không gian hoài niệm phù hợp để bắt đầu buổi chiều nhẹ nhàng.",
                        "image_url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&h=400&fit=crop",
                        "latitude": 10.776,
                        "longitude": 106.701
                    },
                    {
                        "step": 2,
                        "provider_id": 1,
                        "title": "Trần Pizza",
                        "district": "Quận 1",
                        "category": "Quán ăn / nhà hàng",
                        "arrival_time": "16:00",
                        "duration_min": 60,
                        "cost_estimated": 150000,
                        "reason": "Điểm nạp năng lượng lý tưởng với món Pizza nướng củi thơm ngon.",
                        "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&h=400&fit=crop",
                        "latitude": 10.778,
                        "longitude": 106.702
                    },
                    {
                        "step": 3,
                        "provider_id": 3,
                        "title": "Đảo Space",
                        "district": "Quận 1",
                        "category": "Quán uống / cafe",
                        "arrival_time": "17:15",
                        "duration_min": 45,
                        "cost_estimated": 70000,
                        "reason": "Kết thúc buổi chiều tại quán cafe hiện đại, lý tưởng để trò chuyện.",
                        "image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&h=400&fit=crop",
                        "latitude": 10.775,
                        "longitude": 106.698
                    }
                ]
            },
            {
                "id": 9992,
                "title": "Food Tour Ẩm Thực Vỉa Hè Sài Gòn Q5",
                "mood_code": "foodie",
                "district_preference": "Quận 5",
                "total_cost_estimated": 200000,
                "total_duration_min": 160,
                "transport_mode": "Tự đi xe máy",
                "created_at": "2026-06-29T15:00:00Z",
                "stops": [
                    {
                        "step": 1,
                        "provider_id": 22,
                        "title": "Cơm Tấm Huỳnh Mẫn Đạt",
                        "district": "Quận 5",
                        "category": "Quán ăn / nhà hàng",
                        "arrival_time": "18:00",
                        "duration_min": 50,
                        "cost_estimated": 55000,
                        "reason": "Đặc sản cơm tấm Sài Gòn thơm nức mũi, sườn nướng mọng nước cực đã.",
                        "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=400&fit=crop",
                        "latitude": 10.755,
                        "longitude": 106.678
                    },
                    {
                        "step": 2,
                        "provider_id": 11,
                        "title": "CAFE 68",
                        "district": "Quận 5",
                        "category": "Quán uống / cafe",
                        "arrival_time": "19:00",
                        "duration_min": 45,
                        "cost_estimated": 45000,
                        "reason": "Nơi nghỉ chân hoàn hảo sau bữa tối no căng bụng.",
                        "image_url": "https://images.unsplash.com/photo-1498804103079-a6351b050096?w=600&h=400&fit=crop",
                        "latitude": 10.752,
                        "longitude": 106.675
                    },
                    {
                        "step": 3,
                        "provider_id": 30,
                        "title": "Hồ Thị Kỷ",
                        "district": "Quận 5",
                        "category": "Quán ăn / nhà hàng",
                        "arrival_time": "20:00",
                        "duration_min": 65,
                        "cost_estimated": 100000,
                        "reason": "Thiên đường ẩm thực ăn vặt sầm uất bậc nhất Sài Thành.",
                        "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=400&fit=crop",
                        "latitude": 10.765,
                        "longitude": 106.672
                    }
                ]
            },
            {
                "id": 9993,
                "title": "Vibe Đêm Lãng Mạn & Nightlife Quận 1",
                "mood_code": "date",
                "district_preference": "Quận 1",
                "total_cost_estimated": 550000,
                "total_duration_min": 170,
                "transport_mode": "Thuê xe",
                "created_at": "2026-06-29T20:00:00Z",
                "stops": [
                    {
                        "step": 1,
                        "provider_id": 15,
                        "title": "Nhà Hàng Hương Việt",
                        "district": "Quận 1",
                        "category": "Quán ăn / nhà hàng",
                        "arrival_time": "19:30",
                        "duration_min": 60,
                        "cost_estimated": 280000,
                        "reason": "Không gian ấm cúng, sang trọng, thực đơn phong phú thích hợp cho các buổi hẹn hò.",
                        "image_url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&h=400&fit=crop",
                        "latitude": 10.774,
                        "longitude": 106.703
                    },
                    {
                        "step": 2,
                        "provider_id": 12,
                        "title": "The Hipster",
                        "district": "Quận 1",
                        "category": "Nightlife / bar",
                        "arrival_time": "20:45",
                        "duration_min": 70,
                        "cost_estimated": 200000,
                        "reason": "Nhạc hay, đồ uống pha chế cực chất, view phố phường chill vô cùng.",
                        "image_url": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=600&h=400&fit=crop",
                        "latitude": 10.773,
                        "longitude": 106.701
                    },
                    {
                        "step": 3,
                        "provider_id": 9,
                        "title": "K COFFEE",
                        "district": "Quận 1",
                        "category": "Quán uống / cafe",
                        "arrival_time": "22:05",
                        "duration_min": 40,
                        "cost_estimated": 70000,
                        "reason": "Khép lại một đêm trọi vẹn tại góc phố nhộn nhịp cùng ly bạc xỉu đá thơm ngậy.",
                        "image_url": "https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=600&h=400&fit=crop",
                        "latitude": 10.776,
                        "longitude": 106.702
                    }
                ]
            }
        ]
        match = [c for c in curated_list if c["id"] == itinerary_id]
        if match:
            itinerary = dict(match[0])
            itinerary["total_cost"] = _format_cost(itinerary["total_cost_estimated"])
            itinerary["total_duration"] = _format_duration(itinerary["total_duration_min"])
            return itinerary

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

    # Enrich stops with OSM details
    provider_ids = [s["provider_id"] for s in stops]
    detail_map = fetch_place_details(conn, provider_ids)
    
    formatted_stops = []
    for s in stops:
        stop_dict = dict(s)
        stop_dict.update(detail_map.get(s["provider_id"], {}))
        formatted_stops.append(stop_dict)

    itinerary = dict(row)
    itinerary["stops"] = formatted_stops
    itinerary["total_cost"] = _format_cost(row["total_cost_estimated"])
    itinerary["total_duration"] = _format_duration(row["total_duration_min"])
    return itinerary


@router.post("/{itinerary_id}/feedback")
def submit_feedback(
    itinerary_id: int,
    body: FeedbackRequest,
    user_id: int = Depends(get_current_user_id),
    conn: Any = Depends(get_db_dependency),
):
    """Submit user feedback for an itinerary."""
    conn.execute(
        "INSERT INTO itinerary_feedback (itinerary_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
        (itinerary_id, user_id, body.rating, body.comment),
    )
    conn.commit()
    return {"success": True, "message": "Cảm ơn bạn đã đánh giá!"}



