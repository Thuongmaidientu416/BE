import sqlite3, psycopg2, psycopg2.extras

DATABASE_URL = "postgresql://postgres:khang02102005%40@db.fsbyjlhnxhbvvuejznnh.supabase.co:5432/postgres"

src = sqlite3.connect('wanderhub.db')
src.row_factory = sqlite3.Row

pg = psycopg2.connect(DATABASE_URL, sslmode="require")
pg.autocommit = True
cur = pg.cursor()

print("Step 1: Create schemas...")

SCHEMAS = [
    """CREATE TABLE IF NOT EXISTS districts (
        id BIGINT PRIMARY KEY, name TEXT NOT NULL UNIQUE, city TEXT NOT NULL DEFAULT 'Ho Chi Minh City',
        area_label TEXT, min_lat REAL, min_lon REAL, max_lat REAL, max_lon REAL, notes TEXT)""",
    """CREATE TABLE IF NOT EXISTS categories (
        id BIGINT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT)""",
    """CREATE TABLE IF NOT EXISTS roles (
        id BIGINT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT)""",
    """CREATE TABLE IF NOT EXISTS moods (
        id BIGINT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS providers (
        id BIGINT PRIMARY KEY, name TEXT NOT NULL, district_id INTEGER, category_id INTEGER,
        role_id INTEGER, latitude REAL NOT NULL, longitude REAL NOT NULL, address TEXT, street TEXT,
        phone TEXT, website TEXT, opening_hours TEXT, price_min_vnd INTEGER, price_max_vnd INTEGER,
        avg_duration_min INTEGER, osm_type TEXT NOT NULL, osm_id BIGINT NOT NULL, osm_url TEXT NOT NULL,
        wikidata_id TEXT, wikipedia_title TEXT, source TEXT NOT NULL DEFAULT 'openstreetmap',
        source_license TEXT NOT NULL DEFAULT 'ODbL', status TEXT NOT NULL DEFAULT 'candidate',
        description TEXT, raw_tags_json TEXT, created_at TEXT DEFAULT NOW()::text,
        UNIQUE(osm_type, osm_id))""",
    """CREATE TABLE IF NOT EXISTS provider_squad_scores (
        id BIGINT PRIMARY KEY, provider_id INTEGER, ai_base_score REAL, district_rank INTEGER,
        mood_diversity INTEGER, price_tier TEXT, updated_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS provider_media (
        id BIGINT PRIMARY KEY, provider_id INTEGER, image_url TEXT, source TEXT, created_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS provider_moods (
        provider_id INTEGER, mood_id INTEGER, PRIMARY KEY(provider_id, mood_id))""",
    """CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL, preferences_json TEXT, budget_default INTEGER,
        created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS itineraries (
        id BIGSERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id), title TEXT NOT NULL,
        mood_code TEXT, district_preference TEXT, budget_min INTEGER, budget_max INTEGER,
        time_start TEXT, time_end TEXT, transport_mode TEXT, total_cost_estimated INTEGER,
        total_duration_min INTEGER, status TEXT DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS itinerary_stops (
        id BIGSERIAL PRIMARY KEY, itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE CASCADE,
        provider_id INTEGER, step_order INTEGER NOT NULL, arrival_time TEXT,
        duration_min INTEGER, cost_estimated INTEGER, reason TEXT, status TEXT DEFAULT 'active')""",
    """CREATE TABLE IF NOT EXISTS contacts (
        id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL,
        subject TEXT, message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS itinerary_feedback (
        id BIGSERIAL PRIMARY KEY, itinerary_id INTEGER REFERENCES itineraries(id),
        user_id INTEGER REFERENCES users(id), rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        comment TEXT, created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS recommendation_sessions (
        id BIGSERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id),
        itinerary_id INTEGER REFERENCES itineraries(id), mood_input TEXT, district TEXT,
        budget_max INTEGER, time_start TEXT, time_end TEXT, transport_mode TEXT,
        parsed_context_json TEXT, rules_json TEXT, created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS user_interactions (
        id BIGSERIAL PRIMARY KEY,
        session_id INTEGER REFERENCES recommendation_sessions(id) ON DELETE SET NULL,
        user_id INTEGER REFERENCES users(id),
        itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
        provider_id INTEGER, event_type TEXT NOT NULL, weight REAL NOT NULL DEFAULT 1,
        metadata_json TEXT, created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS recommendation_logs (
        id BIGSERIAL PRIMARY KEY,
        session_id INTEGER REFERENCES recommendation_sessions(id) ON DELETE CASCADE,
        itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
        provider_id INTEGER, rank_position INTEGER NOT NULL, score REAL, reason TEXT,
        created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS user_plans (
        id BIGSERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        plan_name TEXT NOT NULL, plan_key TEXT NOT NULL,
        selected_at TEXT NOT NULL DEFAULT NOW()::text, UNIQUE(user_id))""",
    """CREATE TABLE IF NOT EXISTS vehicle_fleet (
        id BIGSERIAL PRIMARY KEY, vehicle_type TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
        total_count INTEGER NOT NULL, available_count INTEGER NOT NULL,
        updated_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS vehicle_bookings (
        id BIGSERIAL PRIMARY KEY, vehicle_type TEXT NOT NULL,
        user_id INTEGER REFERENCES users(id), itinerary_id INTEGER REFERENCES itineraries(id),
        driver_name TEXT NOT NULL, driver_rating REAL NOT NULL, plate_number TEXT NOT NULL,
        eta_minutes INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT NOW()::text)""",
    """CREATE TABLE IF NOT EXISTS vehicle_images (
        id BIGSERIAL PRIMARY KEY, vehicle_type TEXT NOT NULL UNIQUE, image_url TEXT NOT NULL,
        description TEXT, features TEXT, capacity TEXT,
        created_at TEXT NOT NULL DEFAULT NOW()::text)""",
]

for stmt in SCHEMAS:
    try:
        cur.execute(stmt)
        tname = stmt.split('EXISTS')[1].split('(')[0].strip()
        print(f"  OK: {tname}")
    except Exception as e:
        print(f"  SKIP: {str(e)[:80]}")

print("\nStep 2: Migrate data from SQLite...")

def insert_table(table, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    vals = [tuple(r[c] for c in cols) for r in rows]
    placeholders = '(' + ','.join(['%s'] * len(cols)) + ')'
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES %s ON CONFLICT DO NOTHING"
    try:
        psycopg2.extras.execute_values(cur, sql, vals, template=placeholders, page_size=50)
        print(f"  {table}: {len(rows)} rows OK")
    except Exception as e:
        print(f"  {table} ERROR: {str(e)[:120]}")

for table in ['districts', 'categories', 'roles', 'moods', 'providers',
              'provider_squad_scores', 'provider_media', 'provider_moods']:
    rows = src.execute(f'SELECT * FROM {table}').fetchall()
    insert_table(table, rows)

print("\nStep 3: Seed vehicle data...")
cur.execute("""
    INSERT INTO vehicle_fleet (vehicle_type, label, total_count, available_count) VALUES
    ('motorbike', 'Xe may WanderHUB', 50, 50),
    ('car7', 'Xe 7 cho WanderHUB', 20, 20)
    ON CONFLICT (vehicle_type) DO NOTHING
""")
cur.execute("""
    INSERT INTO vehicle_images (vehicle_type, image_url, description, features, capacity) VALUES
    ('motorbike', 'https://images.unsplash.com/photo-1593618998160-e34014e67546?w=600&h=400&fit=crop',
     'Xe may WanderHUB', 'Binh xang lon, phanh ABS, den LED', '1-2 nguoi'),
    ('car7', 'https://images.unsplash.com/photo-1464207687429-7505649dae38?w=600&h=400&fit=crop',
     'Xe 7 cho WanderHUB', 'Dieu hoa 2 vung, WiFi 4G', '5-7 nguoi')
    ON CONFLICT (vehicle_type) DO NOTHING
""")

src.close()
cur.close()
pg.close()
print("\nMigration complete!")
