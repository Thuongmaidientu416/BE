"""
WanderHUB Backend — Chat Router (AI Chatbot Proxy)
"""

from __future__ import annotations
import sqlite3
from fastapi import APIRouter, Depends

from database import get_db_dependency
from models.schemas import ChatRequest, ChatResponse
from ai.data_engine import detect_moods
from ai.conversation import generate_response, build_chat_system_data

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """
    AI Chatbot endpoint.

    Pipeline:
      1. Detect moods from user message
      2. Query relevant providers from DB
      3. Build system data context
      4. Call Layer 4 (LLM) with real data
    """
    # Detect moods from user message
    moods = detect_moods(body.message)

    # Detect district from message
    district = "Quận 1"  # default
    district_keywords = {
        "quận 1": "Quận 1", "q1": "Quận 1",
        "quận 3": "Quận 3", "q3": "Quận 3",
        "quận 4": "Quận 4", "q4": "Quận 4",
        "quận 5": "Quận 5", "q5": "Quận 5",
        "quận 10": "Quận 10", "q10": "Quận 10",
        "bình thạnh": "Bình Thạnh",
        "phú nhuận": "Phú Nhuận",
        "thảo điền": "Thảo Điền",
        "landmark": "Bình Thạnh",
    }
    lower_msg = body.message.lower()
    for kw, dist in district_keywords.items():
        if kw in lower_msg:
            district = dist
            break

    # Build system data from DB
    system_data = build_chat_system_data(conn, body.message, moods, district)

    # Call Layer 4 (LLM)
    reply, source = await generate_response(
        user_message=body.message,
        message_history=body.history,
        system_data=system_data,
        groq_key=body.groq_key,
    )

    return ChatResponse(reply=reply, source=source)
