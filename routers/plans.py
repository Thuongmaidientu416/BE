"""
WanderHUB Backend — Plans Router (Select / Get current plan)
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException

from database import get_db_dependency
from models.schemas import PlanSelectRequest, PlanResponse
from routers.auth import require_auth

router = APIRouter(prefix="/api/plans", tags=["plans"])

PLAN_LIMITS: dict[str, int | None] = {
    "basic": 1,       # 1 itinerary per 20 days
    "premium": None,
    "international": None,
}

PLAN_PERIOD_DAYS = 20  # days between resets for basic


def _usage_info(conn: sqlite3.Connection, user_id: int, plan_key: str) -> tuple[int, str | None]:
    """Return (usage_count_in_period, period_reset_at_iso or None)."""
    if plan_key == "basic":
        row = conn.execute(
            """
            SELECT created_at FROM itineraries
            WHERE user_id = ?
              AND datetime(created_at) > datetime('now', ?)
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, f"-{PLAN_PERIOD_DAYS} days"),
        ).fetchone()
        if row:
            last_dt = datetime.fromisoformat(row["created_at"])
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            reset_at = last_dt + timedelta(days=PLAN_PERIOD_DAYS)
            return 1, reset_at.isoformat()
        return 0, None
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM itineraries WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return (row["cnt"] if row else 0), None


@router.post("/select", response_model=PlanResponse)
def select_plan(
    body: PlanSelectRequest,
    user_id: int = Depends(require_auth),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    if body.plan_key not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Gói dịch vụ không hợp lệ.")

    conn.execute(
        """
        INSERT INTO user_plans (user_id, plan_name, plan_key)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            plan_name   = excluded.plan_name,
            plan_key    = excluded.plan_key,
            selected_at = CURRENT_TIMESTAMP
        """,
        (user_id, body.plan_name, body.plan_key),
    )
    conn.commit()

    row = conn.execute(
        "SELECT plan_name, plan_key, selected_at FROM user_plans WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    usage, reset_at = _usage_info(conn, user_id, row["plan_key"])
    return PlanResponse(
        plan_name=row["plan_name"],
        plan_key=row["plan_key"],
        selected_at=row["selected_at"],
        usage_this_month=usage,
        monthly_limit=PLAN_LIMITS.get(row["plan_key"]),
        period_reset_at=reset_at,
        period_days=PLAN_PERIOD_DAYS,
    )


@router.get("/me", response_model=PlanResponse)
def get_my_plan(
    user_id: int = Depends(require_auth),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute(
        "SELECT plan_name, plan_key, selected_at FROM user_plans WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Chưa chọn gói dịch vụ.")

    usage, reset_at = _usage_info(conn, user_id, row["plan_key"])
    return PlanResponse(
        plan_name=row["plan_name"],
        plan_key=row["plan_key"],
        selected_at=row["selected_at"],
        usage_this_month=usage,
        monthly_limit=PLAN_LIMITS.get(row["plan_key"]),
        period_reset_at=reset_at,
        period_days=PLAN_PERIOD_DAYS,
    )
