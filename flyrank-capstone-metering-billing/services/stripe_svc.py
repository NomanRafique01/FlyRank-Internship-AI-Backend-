import stripe
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from database import get_db

stripe.api_key = STRIPE_SECRET_KEY

def create_checkout_session(tenant_id: str, success_url: str, cancel_url: str) -> Dict[str, str]:
    """
    Creates a Stripe Checkout session in test mode for upgrading to Pro plan.
    """
    try:
        # If running in test mode with placeholder or real key
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "FlyRank Pro Tier Subscription",
                            "description": "10,000 API calls & 1,000,000 AI tokens per month",
                        },
                        "unit_amount": 2900,  # $29.00
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            client_reference_id=tenant_id,
            metadata={"tenant_id": tenant_id},
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        # Safe handling for test environment
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe checkout session creation failed: {str(e)}"
        )

def process_stripe_event(event: Any) -> Dict[str, Any]:
    """
    Processes verified Stripe webhook events idempotently.
    Supported events:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    """
    if hasattr(event, "to_dict"):
        event = event.to_dict()

    event_id = event.get("id")
    event_type = event.get("type")
    data_obj = event.get("data", {}).get("object", {})

    with get_db() as conn:
        cursor = conn.cursor()

        # Webhook Idempotency Check: deduplicate replay events
        cursor.execute("SELECT event_id FROM processed_webhooks WHERE event_id = ?", (event_id,))
        if cursor.fetchone():
            return {
                "status": "ignored",
                "reason": "Duplicate webhook event already processed",
                "event_id": event_id
            }

        if event_type == "checkout.session.completed":
            tenant_id = data_obj.get("client_reference_id") or data_obj.get("metadata", {}).get("tenant_id")
            customer_id = data_obj.get("customer")
            sub_id = data_obj.get("subscription")

            if tenant_id:
                cursor.execute("""
                    UPDATE subscriptions
                    SET plan_id = 'pro',
                        status = 'active',
                        stripe_customer_id = COALESCE(?, stripe_customer_id),
                        stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenant_id = ?
                """, (customer_id, sub_id, tenant_id))

        elif event_type in ["customer.subscription.updated", "customer.subscription.created"]:
            sub_id = data_obj.get("id")
            customer_id = data_obj.get("customer")
            sub_status = data_obj.get("status", "active")

            cursor.execute("""
                UPDATE subscriptions
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE stripe_subscription_id = ? OR stripe_customer_id = ?
            """, (sub_status, sub_id, customer_id))

        elif event_type == "customer.subscription.deleted":
            sub_id = data_obj.get("id")
            customer_id = data_obj.get("customer")

            cursor.execute("""
                UPDATE subscriptions
                SET plan_id = 'free',
                    status = 'canceled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE stripe_subscription_id = ? OR stripe_customer_id = ?
            """, (sub_id, customer_id))

        # Record webhook as processed
        cursor.execute("""
            INSERT INTO processed_webhooks (event_id, event_type)
            VALUES (?, ?)
        """, (event_id, event_type))

    return {
        "status": "processed",
        "event_id": event_id,
        "event_type": event_type
    }
