import sqlite3
from typing import Generator
from contextlib import contextmanager
from config import DATABASE_PATH, PLANS

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Tenants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                max_api_calls INTEGER NOT NULL,
                max_ai_tokens INTEGER NOT NULL,
                price_cents INTEGER NOT NULL
            )
        """)

        # 3. Subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                plan_id TEXT NOT NULL REFERENCES plans(id),
                status TEXT NOT NULL,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Usage events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                idempotency_key TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                cached_input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                reasoning_tokens INTEGER DEFAULT 0,
                cost_micro_cents INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Idempotency responses cache (to replay exact duplicate responses)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_cache (
                idempotency_key TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                status_code INTEGER NOT NULL,
                response_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Processed webhooks table (to guarantee exactly-once webhook processing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_webhooks (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for fast tenant rollups & boundary checks
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_tenant_time ON usage_events(tenant_id, timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_idempotency ON usage_events(idempotency_key);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_tenant ON subscriptions(tenant_id);")

        # Sync plans from config
        for plan_id, plan_data in PLANS.items():
            cursor.execute("""
                INSERT INTO plans (id, name, max_api_calls, max_ai_tokens, price_cents)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    max_api_calls = excluded.max_api_calls,
                    max_ai_tokens = excluded.max_ai_tokens,
                    price_cents = excluded.price_cents
            """, (plan_id, plan_data["name"], plan_data["max_api_calls"], plan_data["max_ai_tokens"], plan_data["price_cents"]))

