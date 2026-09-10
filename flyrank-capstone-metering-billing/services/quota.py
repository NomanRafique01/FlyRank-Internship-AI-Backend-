import sqlite3
from typing import Dict, Any, Tuple
from fastapi import HTTPException, status
from config import PLANS

def get_tenant_subscription(conn: sqlite3.Connection, tenant_id: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.tenant_id, s.plan_id, s.status, p.max_api_calls, p.max_ai_tokens, p.name as plan_name
        FROM subscriptions s
        JOIN plans p ON s.plan_id = p.id
        WHERE s.tenant_id = ?
    """, (tenant_id,))
    row = cursor.fetchone()
    if not row:
        # Check if tenant exists
        cursor.execute("SELECT id FROM tenants WHERE id = ?", (tenant_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found."
            )
        # Default to free if no subscription row
        return {
            "plan_id": "free",
            "status": "active",
            "max_api_calls": PLANS["free"]["max_api_calls"],
            "max_ai_tokens": PLANS["free"]["max_ai_tokens"],
            "plan_name": "Free"
        }
    return dict(row)

def get_current_month_usage(conn: sqlite3.Connection, tenant_id: str) -> Dict[str, int]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as api_calls,
            COALESCE(SUM(quantity), 0) as total_tokens,
            COALESCE(SUM(input_tokens), 0) as input_tokens,
            COALESCE(SUM(cached_input_tokens), 0) as cached_input_tokens,
            COALESCE(SUM(output_tokens), 0) as output_tokens,
            COALESCE(SUM(reasoning_tokens), 0) as reasoning_tokens,
            COALESCE(SUM(cost_micro_cents), 0) as total_cost_micro_cents
        FROM usage_events
        WHERE tenant_id = ?
          AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
    """, (tenant_id,))
    row = cursor.fetchone()
    return dict(row) if row else {
        "api_calls": 0,
        "total_tokens": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_cost_micro_cents": 0
    }

def check_quota(conn: sqlite3.Connection, tenant_id: str, requested_tokens: int = 0) -> Dict[str, Any]:
    sub = get_tenant_subscription(conn, tenant_id)

    # 1. Check subscription validity (402 Payment Required)
    if sub["status"] in ["past_due", "canceled", "unpaid"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Payment Required",
                "tenant_id": tenant_id,
                "subscription_status": sub["status"],
                "message": "Subscription is past due or canceled. Please upgrade or update payment method."
            }
        )

    # 2. Check quota limits (429 Too Many Requests)
    usage = get_current_month_usage(conn, tenant_id)
    max_calls = sub["max_api_calls"]
    max_tokens = sub["max_ai_tokens"]

    # Boundary check: At exactly 1,000 calls, a 1,001st call is rejected.
    if usage["api_calls"] >= max_calls:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "86400"},
            detail={
                "error": "Quota Exceeded",
                "tenant_id": tenant_id,
                "metric": "api_calls",
                "used": usage["api_calls"],
                "limit": max_calls,
                "message": f"Tenant {tenant_id} has exceeded the monthly API call quota ({usage['api_calls']}/{max_calls}). Upgrade to Pro to continue."
            }
        )

    if (usage["total_tokens"] + requested_tokens) > max_tokens:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "86400"},
            detail={
                "error": "Quota Exceeded",
                "tenant_id": tenant_id,
                "metric": "ai_tokens",
                "used": usage["total_tokens"],
                "requested": requested_tokens,
                "limit": max_tokens,
                "message": f"Tenant {tenant_id} would exceed monthly AI token quota ({usage['total_tokens'] + requested_tokens}/{max_tokens})."
            }
        )

    return {
        "subscription": sub,
        "usage": usage
    }

