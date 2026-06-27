"""
WanderHUB Backend — Contact Router
"""

from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends

from database import get_db_dependency
from models.schemas import ContactRequest, ContactResponse

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", response_model=ContactResponse)
def submit_contact(
    body: ContactRequest,
    conn: Any = Depends(get_db_dependency),
):
    """Save a contact form submission to the database."""
    conn.execute(
        "INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
        (body.name, body.email, body.subject, body.message),
    )
    conn.commit()
    return ContactResponse(
        success=True,
        message="Gửi liên hệ thành công! Đội ngũ WanderHUB sẽ phản hồi qua email của bạn.",
    )
