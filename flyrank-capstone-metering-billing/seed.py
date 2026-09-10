from database import get_db, init_db

def seed_data():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()

        # Seed test tenants
        tenants = [
            ("tenant_free", "Acme Free Tier Corp"),
            ("tenant_pro", "Globex Pro Tier Inc"),
            ("tenant_lapsed", "Initech Unpaid LLC"),
        ]
        for t_id, name in tenants:
            cursor.execute("""
                INSERT INTO tenants (id, name)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name
            """, (t_id, name))

        # Seed subscriptions
        subscriptions = [
            ("sub_free", "tenant_free", "free", "active", "cus_test_free", None),
            ("sub_pro", "tenant_pro", "pro", "active", "cus_test_pro", "sub_test_pro"),
            ("sub_lapsed", "tenant_lapsed", "pro", "past_due", "cus_test_lapsed", "sub_test_lapsed"),
        ]
        for s_id, t_id, p_id, status, cus_id, sub_id in subscriptions:
            cursor.execute("""
                INSERT INTO subscriptions (id, tenant_id, plan_id, status, stripe_customer_id, stripe_subscription_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    plan_id = excluded.plan_id,
                    status = excluded.status,
                    stripe_customer_id = excluded.stripe_customer_id,
                    stripe_subscription_id = excluded.stripe_subscription_id
            """, (s_id, t_id, p_id, status, cus_id, sub_id))

        print("Database seeded successfully with test tenants and subscriptions.")

if __name__ == "__main__":
    seed_data()
