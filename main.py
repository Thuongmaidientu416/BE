"""
WanderHUB Backend — FastAPI Application Entry Point

Start with:
    cd backend
    python main.py
    # or: uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.responses import Response

from config import CORS_ORIGINS
from database import init_db
from routers import auth, providers, landing, itinerary, chat, contact, interactions

# ── Create app ────────────────────────────────────────────────────
app = FastAPI(
    title="WanderHUB API",
    description="Backend API cho WanderHUB — AI trip planner cho trải nghiệm đô thị TP.HCM.",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────
_CORS_HEADERS = {
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Max-Age": "3600",
}

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin", "*")
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={**_CORS_HEADERS, "Access-Control-Allow-Origin": origin})
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = _CORS_HEADERS["Access-Control-Allow-Methods"]
    return response

# ── Register routers ─────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(landing.router)
app.include_router(itinerary.router)
app.include_router(chat.router)
app.include_router(contact.router)
app.include_router(interactions.router)


# ── Startup ──────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    init_db()
    print("[WanderHUB] Backend started — API docs at http://127.0.0.1:8000/docs")


# ── Health check ─────────────────────────────────────────────────
@app.get("/api/health")
def health():
    import os
    groq_set = bool(os.getenv("GROQ_API_KEY", ""))
    return {"status": "ok", "service": "WanderHUB Backend", "groq_key_set": groq_set}


# ── Run ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
