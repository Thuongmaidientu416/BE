"""
WanderHUB Backend — Landing Page Router
"""

from __future__ import annotations
import sqlite3
from fastapi import APIRouter, Depends

from database import get_db_dependency
from models.schemas import LandingResponse

router = APIRouter(prefix="/api/landing", tags=["landing"])


@router.get("", response_model=LandingResponse)
def get_landing(conn: sqlite3.Connection = Depends(get_db_dependency)):
    """Return all data needed for the Home page hero + stats sections."""

    # Hero content
    hero = {
        "headline": "WanderHUB",
        "subheadline": "AI trip planner cho những buổi đi chơi trong thành phố.",
        "cta_primary": "Tạo lịch trình",
        "cta_secondary": "Khám phá địa điểm",
    }

    # Metrics
    total_providers = conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
    total_districts = conn.execute("SELECT COUNT(*) FROM districts").fetchone()[0]
    total_categories = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]

    metrics = {
        "total_providers": total_providers,
        "total_districts": total_districts,
        "total_categories": total_categories,
    }

    # District summary
    district_rows = conn.execute(
        "SELECT * FROM v_district_summary ORDER BY total_places DESC"
    ).fetchall()
    district_summary = [dict(r) for r in district_rows]

    # Category summary
    category_rows = conn.execute("""
        SELECT
            category_name,
            SUM(total_places) AS total_places,
            ROUND(AVG(avg_wanderhub_score), 1) AS avg_wanderhub_score
        FROM v_category_summary
        GROUP BY category_name
        ORDER BY total_places DESC
    """).fetchall()
    category_summary = [dict(r) for r in category_rows]

    return LandingResponse(
        hero=hero,
        metrics=metrics,
        district_summary=district_summary,
        category_summary=category_summary,
    )
