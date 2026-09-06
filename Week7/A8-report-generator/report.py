import json
import sqlite3
from typing import Any, Dict


def getReportData(db_path: str = "report.db") -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Total number of orders
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0] or 0

    # 2. Total revenue
    cur.execute("SELECT ROUND(COALESCE(SUM(amount), 0), 2) FROM orders")
    total_revenue = cur.fetchone()[0] or 0.0

    # 3. Top 5 products by revenue
    cur.execute("""
        SELECT product, ROUND(SUM(amount), 2) AS revenue, COUNT(*) AS count
        FROM orders
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 5
    """)
    top_5_products = [
        {"product": row[0], "revenue": row[1], "count": row[2]}
        for row in cur.fetchall()
    ]

    # 4. Orders per day for the last 7 days
    cur.execute("""
        SELECT date(created_at) AS order_date, COUNT(*) AS count, ROUND(SUM(amount), 2) AS revenue
        FROM orders
        GROUP BY date(created_at)
        ORDER BY order_date DESC
        LIMIT 7
    """)
    orders_last_7_days = [
        {"date": row[0], "count": row[1], "revenue": row[2]}
        for row in cur.fetchall()
    ]

    # All orders for detail view in the rendered document
    cur.execute("""
        SELECT id, customer, product, amount, created_at
        FROM orders
        ORDER BY id ASC
    """)
    all_orders = [
        {
            "id": row[0],
            "customer": row[1],
            "product": row[2],
            "amount": row[3],
            "created_at": row[4],
        }
        for row in cur.fetchall()
    ]

    conn.close()

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "top_5_products": top_5_products,
        "orders_last_7_days": orders_last_7_days,
        "all_orders": all_orders,
    }


if __name__ == "__main__":
    report_data = getReportData()
    # Print as valid JSON with 4 key sections
    summary_view = {
        "total_orders": report_data["total_orders"],
        "total_revenue": report_data["total_revenue"],
        "top_5_products": report_data["top_5_products"],
        "orders_last_7_days": report_data["orders_last_7_days"],
    }
    print(json.dumps(summary_view, indent=2))

