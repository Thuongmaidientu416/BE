"""
WanderHUB Backend — DB Connection Manager
Supports SQLite (local dev) and PostgreSQL/Supabase (production).
"""

import sqlite3
import shutil
from contextlib import contextmanager
from pathlib import Path

from config import DB_PATH, SEED_DB_PATH, DATABASE_URL

_USE_PG = bool(DATABASE_URL)

if _USE_PG:
    import psycopg2
    import psycopg2.extras

# ── PostgreSQL row/cursor wrapper (mimics sqlite3 interface) ────────

class _PGRow(dict):
    """Dict that also supports row[0] index access like sqlite3.Row."""
    def __init__(self, d):
        super().__init__(d)
        self._keys_list = list(d.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._keys_list[key])
        return super().__getitem__(key)

    def keys(self):
        return self._keys_list


class _PGCursor:
    """Wraps psycopg2 cursor to mimic sqlite3 cursor."""
    def __init__(self, cur, last_id=None):
        self._cur = cur
        self._last_id = last_id

    @property
    def lastrowid(self):
        return self._last_id

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        row = self._cur.fetchone()
        return _PGRow(dict(row)) if row else None

    def fetchall(self):
        return [_PGRow(dict(r)) for r in self._cur.fetchall()]


class _PGConn:
    """Wraps psycopg2 connection to mimic sqlite3.Connection."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        pg_sql = sql.replace("?", "%s")
        is_insert = pg_sql.strip().upper().startswith("INSERT")
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        last_id = None
        if is_insert and "RETURNING" not in pg_sql.upper():
            try:
                cur.execute(pg_sql + " RETURNING id", params or ())
                row = cur.fetchone()
                last_id = dict(row).get("id") if row else None
            except Exception:
                self._conn.rollback()
                cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(pg_sql, params or ())
        else:
            cur.execute(pg_sql, params or ())
        return _PGCursor(cur, last_id)

    def executemany(self, sql, params_list):
        pg_sql = sql.replace("?", "%s")
        cur = self._conn.cursor()
        cur.executemany(pg_sql, params_list)
        return _PGCursor(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


# ── SQLite schema (local dev only) ─────────────────────────────────

SCHEMA_EXTENSIONS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    preferences_json TEXT,
    budget_default INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itineraries (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    mood_code TEXT,
    district_preference TEXT,
    budget_min INTEGER,
    budget_max INTEGER,
    time_start TEXT,
    time_end TEXT,
    transport_mode TEXT,
    total_cost_estimated INTEGER,
    total_duration_min INTEGER,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itinerary_stops (
    id INTEGER PRIMARY KEY,
    itinerary_id INTEGER NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
    provider_id INTEGER NOT NULL REFERENCES providers(id),
    step_order INTEGER NOT NULL,
    arrival_time TEXT,
    duration_min INTEGER,
    cost_estimated INTEGER,
    reason TEXT,
    status TEXT DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itinerary_feedback (
    id INTEGER PRIMARY KEY,
    itinerary_id INTEGER REFERENCES itineraries(id),
    user_id INTEGER REFERENCES users(id),
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recommendation_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    itinerary_id INTEGER REFERENCES itineraries(id),
    mood_input TEXT,
    district TEXT,
    budget_max INTEGER,
    time_start TEXT,
    time_end TEXT,
    transport_mode TEXT,
    parsed_context_json TEXT,
    rules_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_interactions (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES recommendation_sessions(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id),
    itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
    provider_id INTEGER REFERENCES providers(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('view', 'hover', 'click', 'choose', 'save', 'dislike', 'reroute')
    ),
    weight REAL NOT NULL DEFAULT 1,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_user_interactions_user_provider
    ON user_interactions(user_id, provider_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_session
    ON user_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_event
    ON user_interactions(event_type);
CREATE TABLE IF NOT EXISTS user_plans (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    plan_key TEXT NOT NULL,
    selected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);
CREATE TABLE IF NOT EXISTS vehicle_fleet (
    id INTEGER PRIMARY KEY,
    vehicle_type TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    total_count INTEGER NOT NULL,
    available_count INTEGER NOT NULL CHECK(available_count >= 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vehicle_bookings (
    id INTEGER PRIMARY KEY,
    vehicle_type TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id),
    itinerary_id INTEGER REFERENCES itineraries(id),
    driver_name TEXT NOT NULL,
    driver_rating REAL NOT NULL,
    plate_number TEXT NOT NULL,
    eta_minutes INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vehicle_images (
    id INTEGER PRIMARY KEY,
    vehicle_type TEXT NOT NULL UNIQUE,
    image_url TEXT NOT NULL,
    description TEXT,
    features TEXT,
    capacity TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recommendation_logs (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES recommendation_sessions(id) ON DELETE CASCADE,
    itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
    provider_id INTEGER REFERENCES providers(id) ON DELETE CASCADE,
    rank_position INTEGER NOT NULL,
    score REAL,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_recommendation_logs_session
    ON recommendation_logs(session_id);
"""


# ── SQLite helpers ──────────────────────────────────────────────────

def _make_sqlite(db_path) -> sqlite3.Connection:
    if Path(db_path) != SEED_DB_PATH and not Path(db_path).exists():
        shutil.copyfile(SEED_DB_PATH, db_path)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── PostgreSQL helpers ──────────────────────────────────────────────

def _make_pg() -> _PGConn:
    from urllib.parse import urlparse, unquote
    p = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        host=p.hostname,
        port=p.port or 5432,
        dbname=(p.path or "/postgres").lstrip("/"),
        user=p.username,
        password=unquote(p.password or ""),
        sslmode="require",
        connect_timeout=10,
    )
    conn.autocommit = False
    return _PGConn(conn)


# ── Public API ──────────────────────────────────────────────────────

def init_db() -> None:
    if _USE_PG:
        print("[DB] Using PostgreSQL (Supabase) — schema managed via migration SQL")
        return

    conn = _make_sqlite(DB_PATH)
    try:
        conn.executescript(SCHEMA_EXTENSIONS)
        if conn.execute("SELECT COUNT(*) AS cnt FROM vehicle_fleet").fetchone()["cnt"] == 0:
            conn.executemany(
                "INSERT INTO vehicle_fleet (vehicle_type, label, total_count, available_count) VALUES (?, ?, ?, ?)",
                [
                    ("motorbike", "Xe máy WanderHUB", 50, 50),
                    ("car7",      "Xe 7 chỗ WanderHUB", 20, 20),
                ],
            )
        if conn.execute("SELECT COUNT(*) AS cnt FROM vehicle_images").fetchone()["cnt"] == 0:
            conn.executemany(
                "INSERT INTO vehicle_images (vehicle_type, image_url, description, features, capacity) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        "motorbike",
                        "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=600&h=400&fit=crop",
                        "Xe máy WanderHUB - Di động, nhanh gọn, phù hợp cho 1-2 người",
                        "Bình xăng lớn, phanh ABS, đèn LED, bảo hiểm đầy đủ",
                        "1-2 người"
                    ),
                    (
                        "car7",
                        "https://images.unsplash.com/photo-1464207687429-7505649dae38?w=600&h=400&fit=crop",
                        "Xe 7 chỗ WanderHUB - Rộng rãi, thoải mái, tuyệt vời cho nhóm",
                        "Điều hòa 2 vùng, ghế gập linh hoạt, cửa trượt tự động, WiFi 4G",
                        "5-7 người"
                    ),
                ],
            )
        conn.commit()
    finally:
        conn.close()
    print(f"[DB] SQLite schema + seed applied to {DB_PATH}")


@contextmanager
def get_db():
    if _USE_PG:
        conn = _make_pg()
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = _make_sqlite(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()


def get_db_dependency():
    if _USE_PG:
        conn = _make_pg()
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = _make_sqlite(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()
