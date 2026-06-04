"""
WanderHUB Backend — Providers Router (List / Featured / Detail)
"""

from __future__ import annotations
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_db_dependency
from models.schemas import ProviderCard, ProviderDetail, ProviderListResponse

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=ProviderListResponse)
def list_providers(
    district: str | None = Query(None, description="Filter by district name"),
    category: str | None = Query(None, description="Filter by category code"),
    mood: str | None = Query(None, description="Filter by mood code"),
    budget_max: int | None = Query(None, description="Max budget VND"),
    search: str | None = Query(None, description="Search by name"),
    sort: str = Query("score", description="Sort: score, price, name"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """List providers with filtering, sorting and pagination."""
    conditions = []
    params = []

    if district:
        conditions.append("v.district_name = ?")
        params.append(district)
    if category:
        conditions.append("v.category_code = ?")
        params.append(category)
    if budget_max:
        conditions.append("v.price_max_vnd <= ?")
        params.append(budget_max)
    if search:
        conditions.append("v.provider_name LIKE ?")
        params.append(f"%{search}%")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Mood filter requires a JOIN
    mood_join = ""
    if mood:
        mood_join = """
            JOIN provider_moods pm ON pm.provider_id = v.provider_id
            JOIN moods m ON m.id = pm.mood_id AND m.code = ?
        """
        params.insert(0, mood)  # mood param goes before WHERE params

    sort_clause = {
        "score": "v.ai_base_score DESC",
        "price": "v.price_min_vnd ASC",
        "name": "v.provider_name ASC",
    }.get(sort, "v.ai_base_score DESC")

    # Count total
    count_query = f"""
        SELECT COUNT(DISTINCT v.provider_id) FROM v_recommendation_base v
        {mood_join}
        {where_clause}
    """
    total = conn.execute(count_query, params).fetchone()[0]

    # Fetch page
    data_query = f"""
        SELECT DISTINCT
            v.provider_id,
            v.provider_name AS title,
            v.district_name AS district,
            v.category_name AS category,
            v.role_name AS role,
            v.price_min_vnd,
            v.price_max_vnd,
            v.avg_duration_min,
            v.wanderhub_score,
            v.ai_base_score,
            v.primary_image_url AS image_url,
            v.primary_image_credit AS image_credit,
            v.description
        FROM v_recommendation_base v
        {mood_join}
        {where_clause}
        ORDER BY {sort_clause}
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(data_query, [*params, limit, offset]).fetchall()
    providers = [ProviderCard(**dict(r)) for r in rows]

    return ProviderListResponse(providers=providers, total=total)


@router.get("/featured")
def featured_providers(conn: sqlite3.Connection = Depends(get_db_dependency)):
    """Get top provider per category (6 total)."""
    categories = ["cafe_drink", "food", "checkin", "culture", "nightlife", "entertainment"]
    featured = []

    for cat_code in categories:
        row = conn.execute(
            """
            SELECT
                v.provider_id,
                v.provider_name AS title,
                v.district_name AS district,
                v.category_name AS category,
                v.role_name AS role,
                v.price_min_vnd,
                v.price_max_vnd,
                v.avg_duration_min,
                v.wanderhub_score,
                v.ai_base_score,
                v.primary_image_url AS image_url,
                v.primary_image_credit AS image_credit,
                v.description
            FROM v_recommendation_base v
            WHERE v.category_code = ?
            ORDER BY v.ai_base_score DESC
            LIMIT 1
            """,
            (cat_code,),
        ).fetchone()
        if row:
            featured.append(ProviderCard(**dict(row)))

    return featured


@router.get("/{provider_id}", response_model=ProviderDetail)
def get_provider(provider_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    """Get detailed provider info including SQUAD scores and mood tags."""
    row = conn.execute(
        """
        SELECT
            v.provider_id,
            v.provider_name AS title,
            v.district_name AS district,
            v.category_name AS category,
            v.role_name AS role,
            v.price_min_vnd,
            v.price_max_vnd,
            v.avg_duration_min,
            v.wanderhub_score,
            v.ai_base_score,
            v.primary_image_url AS image_url,
            v.primary_image_credit AS image_credit,
            v.description,
            v.latitude,
            v.longitude,
            v.address,
            v.phone,
            v.website,
            v.opening_hours,
            v.service_quality,
            v.gen_z_appeal,
            v.data_compatibility,
            v.experience_value,
            v.deal_viability,
            v.popularity_proxy,
            v.staff_confidence,
            v.squad_total_score
        FROM v_recommendation_base v
        WHERE v.provider_id = ?
        """,
        (provider_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")

    data = dict(row)

    # Fetch mood tags
    mood_rows = conn.execute(
        """
        SELECT m.code FROM provider_moods pm
        JOIN moods m ON m.id = pm.mood_id
        WHERE pm.provider_id = ?
        """,
        (provider_id,),
    ).fetchall()
    moods = [r["code"] for r in mood_rows]

    # Build SQUAD scores dict
    squad_scores = {
        "service_quality": data.pop("service_quality", None),
        "gen_z_appeal": data.pop("gen_z_appeal", None),
        "data_compatibility": data.pop("data_compatibility", None),
        "experience_value": data.pop("experience_value", None),
        "deal_viability": data.pop("deal_viability", None),
        "popularity_proxy": data.pop("popularity_proxy", None),
        "staff_confidence": data.pop("staff_confidence", None),
        "squad_total_score": data.pop("squad_total_score", None),
    }

    return ProviderDetail(**data, moods=moods, squad_scores=squad_scores)
