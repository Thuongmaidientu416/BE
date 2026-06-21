"""
WanderHUB Backend — Configuration
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR
SEED_DB_PATH = PROJECT_ROOT / "wanderhub.db"
DB_PATH = Path("/tmp/wanderhub.db") if (os.getenv("VERCEL") or os.getenv("RENDER")) else SEED_DB_PATH

# ── Auth ───────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("WANDERHUB_JWT_SECRET", "wanderhub-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ── Groq LLM ──────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ── CORS ──────────────────────────────────────────────────────────
CORS_ORIGINS = [
    "http://localhost:5173",   # Vite dev
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",   # Vite preview
    "http://127.0.0.1:4173",
]

# ── AI Recommendation defaults ────────────────────────────────────
DEFAULT_MAX_STOPS = 4
DEFAULT_BUDGET_VND = 500_000
DEFAULT_DURATION_MIN = 240  # 4 hours
