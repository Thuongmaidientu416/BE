"""
WanderHUB Backend - Interaction Router

Tracks recommendation behavior such as hover, click, choose and reroute events.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from database import get_db_dependency
from models.schemas import InteractionRequest, InteractionResponse
from routers.auth import get_current_user_id

router = APIRouter(prefix="/api/interactions", tags=["interactions"])

EVENT_WEIGHTS = {
    "view": 0.2,
    "hover": 0.5,
    "click": 1.5,
    "choose": 3.0,
    "save": 2.5,
    "dislike": -2.0,
    "reroute": -0.6,
}


@router.post("", response_model=InteractionResponse)
def track_interaction(
    body: InteractionRequest,
    user_id: int | None = Depends(get_current_user_id),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """Persist a customer interaction so recommendations can improve later."""
    if body.provider_id is None and body.event_type not in {"view", "reroute"}:
        raise HTTPException(status_code=400, detail="provider_id is required for this event")

    if body.provider_id is not None:
        exists = conn.execute("SELECT id FROM providers WHERE id = ?", (body.provider_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Provider not found")

    if body.session_id is not None:
        session = conn.execute("SELECT id FROM recommendation_sessions WHERE id = ?", (body.session_id,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Recommendation session not found")

    weight = body.weight if body.weight is not None else EVENT_WEIGHTS[body.event_type]
    metadata_json = json.dumps(body.metadata or {}, ensure_ascii=False)

    cursor = conn.execute(
        """
        INSERT INTO user_interactions (
            session_id, user_id, itinerary_id, provider_id,
            event_type, weight, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.session_id,
            user_id,
            body.itinerary_id,
            body.provider_id,
            body.event_type,
            weight,
            metadata_json,
        ),
    )

    if body.session_id is not None and body.itinerary_id is not None:
        conn.execute(
            "UPDATE recommendation_sessions SET itinerary_id = COALESCE(itinerary_id, ?) WHERE id = ?",
            (body.itinerary_id, body.session_id),
        )

    conn.commit()
    return InteractionResponse(
        success=True,
        interaction_id=cursor.lastrowid,
        message="Interaction tracked",
    )
