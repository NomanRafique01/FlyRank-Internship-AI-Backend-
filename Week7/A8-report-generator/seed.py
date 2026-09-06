import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "report.db"

PRODUCTS = [
    "Mechanical Keyboard",
    "Wireless Mouse",
    "Gaming Monitor",
    "Noise-Cancelling Headphones",
    "USB-C Hub",
    "Ergonomic Chair",
]

CUSTOMERS = [
    "Alice Smith",
    "Bob Jones",
    "Charlie Brown",
    "Diana Prince",
    "Evan Wright",
    "Fiona Gallagher",
    "George Clark",
    "Hannah Abbott",
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            product TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def seed_orders(count: int = 200):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clean previous rows so script is safe to run twice (idempotent)
    cursor.execute("DELETE FROM orders")

    now = datetime.now()
    orders = []
    rng = random.Random(42)

    for _ in range(count):
        customer = rng.choice(CUSTOMERS)
        product = rng.choice(PRODUCTS)
        amount = round(rng.uniform(10.0, 250.0), 2)
        days_ago = rng.randint(0, 29)
        hours_ago = rng.randint(0, 23)
        minutes_ago = rng.randint(0, 59)
        order_time = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        created_at = order_time.strftime("%Y-%m-%d %H:%M:%S")
        orders.append((customer, product, amount, created_at))

    cursor.executemany(
        "INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)",
        orders,
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM orders")
    row_count = cursor.fetchone()[0]
    conn.close()
    return row_count


if __name__ == "__main__":
    count = seed_orders(200)
    print(f"Seeded report.db. Total orders count: {count}")

