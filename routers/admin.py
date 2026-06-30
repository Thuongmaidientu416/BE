"""
WanderHUB Backend — Admin Router
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any
import json
from database import get_db_dependency
from routers.auth import require_auth

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(
    user_id: int = Depends(require_auth),
    conn: Any = Depends(get_db_dependency),
) -> int:
    row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row or row["role"] != "admin":
        raise HTTPException(status_code=403, detail="Quyền truy cập bị từ chối. Chỉ dành cho Admin.")
    return user_id


@router.get("/stats")
def get_stats(
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """Retrieve high-level metrics for dashboard."""
    user_count = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()["cnt"]
    itinerary_count = conn.execute("SELECT COUNT(*) AS cnt FROM itineraries").fetchone()["cnt"]
    booking_count = conn.execute("SELECT COUNT(*) AS cnt FROM vehicle_bookings").fetchone()["cnt"]
    contact_count = conn.execute("SELECT COUNT(*) AS cnt FROM contacts").fetchone()["cnt"]
    interaction_count = conn.execute("SELECT COUNT(*) AS cnt FROM user_interactions").fetchone()["cnt"]

    # Simple breakdown by vibe
    vibe_stats = conn.execute(
        """
        SELECT mood_code, COUNT(*) AS count
        FROM itineraries
        GROUP BY mood_code
        """
    ).fetchall()
    vibes = {r["mood_code"]: r["count"] for r in vibe_stats if r["mood_code"]}

    # Simple breakdown by plan type
    plan_stats = conn.execute(
        """
        SELECT plan_name, COUNT(*) AS count
        FROM user_plans
        GROUP BY plan_name
        """
    ).fetchall()
    plans = {r["plan_name"]: r["count"] for r in plan_stats if r["plan_name"]}

    return {
        "metrics": {
            "users": user_count,
            "itineraries": itinerary_count,
            "bookings": booking_count,
            "contacts": contact_count,
            "interactions": interaction_count,
        },
        "breakdown": {
            "vibes": vibes,
            "plans": plans,
        }
    }


@router.get("/users")
def list_users(
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """List all registered users along with their role and active plan."""
    rows = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role, u.created_at,
               p.plan_name, p.plan_key
        FROM users u
        LEFT JOIN user_plans p ON p.user_id = u.id
        ORDER BY u.created_at DESC
        """
    ).fetchall()

    users = []
    from routers.plans import _usage_info
    for r in rows:
        user_dict = dict(r)
        plan_key = user_dict["plan_key"] or "free"
        if not user_dict["plan_name"]:
            user_dict["plan_name"] = "Free"

        usage, reset_at = _usage_info(conn, user_dict["id"], plan_key)
        user_dict["usage_this_month"] = usage
        user_dict["period_reset_at"] = reset_at
        users.append(user_dict)

    return users


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    body: dict,
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """Change a user's role (admin vs user)."""
    new_role = body.get("role")
    if new_role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role không hợp lệ.")

    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    return {"success": True, "message": f"Đã cập nhật vai trò thành {new_role}."}


@router.put("/users/{user_id}/plan")
def update_user_plan(
    user_id: int,
    body: dict,
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """Change a user's subscription plan directly."""
    plan_name = body.get("plan_name")
    plan_key = body.get("plan_key", "basic")

    if plan_name not in ("Free", "Basic", "Premium", "International Tourist"):
        raise HTTPException(status_code=400, detail="Tên gói không hợp lệ.")

    # Check if user has a plan in user_plans
    plan = conn.execute("SELECT id FROM user_plans WHERE user_id = ?", (user_id,)).fetchone()
    if plan:
        conn.execute(
            """
            UPDATE user_plans
            SET plan_name = ?, plan_key = ?
            WHERE user_id = ?
            """,
            (plan_name, plan_key, user_id)
        )
    else:
        conn.execute(
            """
            INSERT INTO user_plans (user_id, plan_name, plan_key)
            VALUES (?, ?, ?)
            """,
            (user_id, plan_name, plan_key)
        )
    conn.commit()
    return {"success": True, "message": f"Đã nâng cấp lên gói {plan_name}."}


@router.get("/contacts")
def list_contacts(
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """List all contact forms submitted."""
    rows = conn.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@router.get("/itineraries")
def list_itineraries(
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """List generated itineraries with details and user's names."""
    rows = conn.execute(
        """
        SELECT i.id, i.title, i.mood_code, i.district_preference,
               i.total_cost_estimated, i.total_duration_min, i.transport_mode, i.created_at,
               u.name AS user_name, u.email AS user_email
        FROM itineraries i
        LEFT JOIN users u ON u.id = i.user_id
        ORDER BY i.created_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/feedbacks")
def list_feedbacks(
    admin_id: int = Depends(require_admin),
    conn: Any = Depends(get_db_dependency),
):
    """List user feedback on itineraries."""
    rows = conn.execute(
        """
        SELECT f.id, f.itinerary_id, f.rating, f.comment, f.created_at,
               u.name AS user_name, u.email AS user_email, i.title AS itinerary_title
        FROM itinerary_feedback f
        LEFT JOIN users u ON u.id = f.user_id
        LEFT JOIN itineraries i ON i.id = f.itinerary_id
        ORDER BY f.created_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]
