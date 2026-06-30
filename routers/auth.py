"""
WanderHUB Backend — Auth Router (Register / Login / Me)
"""

from __future__ import annotations
from typing import Any
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from database import get_db_dependency
from models.schemas import RegisterRequest, LoginRequest, AuthResponse, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return secrets.compare_digest(digest, expected)
    except Exception:
        return False


def _create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int | None:
    """Extract user_id from JWT, returns None if not authenticated."""
    if creds is None:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """Require valid JWT, raise 401 if missing/invalid."""
    if creds is None:
        raise HTTPException(status_code=401, detail="Token required")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/register")
def register(body: RegisterRequest, conn: Any = Depends(get_db_dependency)):
    # Check if email already exists
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng.")

    hashed = _hash_password(body.password)
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (body.name, body.email, hashed),
    )
    conn.commit()
    user_id = cursor.lastrowid

    token = _create_token(user_id)
    return AuthResponse(
        token=token,
        user=UserProfile(id=user_id, name=body.name, email=body.email),
    )


@router.post("/login")
def login(body: LoginRequest, conn: Any = Depends(get_db_dependency)):
    row = conn.execute(
        "SELECT id, name, email, password_hash, role, preferences_json, budget_default FROM users WHERE email = ?",
        (body.email,),
    ).fetchone()
    if not row or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")

    token = _create_token(row["id"])
    return AuthResponse(
        token=token,
        user=UserProfile(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=row["role"],
            preferences_json=row["preferences_json"],
            budget_default=row["budget_default"],
        ),
    )


@router.get("/me")
def get_me(
    user_id: int = Depends(require_auth),
    conn: Any = Depends(get_db_dependency),
):
    row = conn.execute(
        "SELECT id, name, email, role, preferences_json, budget_default FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(**dict(row))
