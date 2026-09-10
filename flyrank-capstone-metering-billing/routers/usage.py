from fastapi import APIRouter, Query, HTTPException, status
from database import get_db
from services.quota import get_tenant_subscription, get_current_month_usage
from services.pricing import format_micro_cents_to_dollars

router = APIRouter(tags=["Usage"])

@router.get("/usage", summary="Tenant usage rollup, limits, and cost")
def get_usage(tenant_id: str = Query(..., description="Tenant ID to retrieve usage for")):
    """
    Returns monthly aggregated usage, remaining quotas, and accrued token costs for a tenant.
    """
    with get_db() as conn:
        sub = get_tenant_subscription(conn, tenant_id)
        usage = get_current_month_usage(conn, tenant_id)

    total_cost_micro = usage["total_cost_micro_cents"]

    return {
        "tenant_id": tenant_id,
        "plan": {
            "id": sub["plan_id"],
            "name": sub["plan_name"],
            "status": sub["status"],
        },
        "usage": {
            "api_calls": {
                "used": usage["api_calls"],
                "limit": sub["max_api_calls"],
                "remaining": max(0, sub["max_api_calls"] - usage["api_calls"]),
            },
            "tokens": {
                "total_used": usage["total_tokens"],
                "limit": sub["max_ai_tokens"],
                "remaining": max(0, sub["max_ai_tokens"] - usage["total_tokens"]),
                "breakdown": {
                    "input_tokens": usage["input_tokens"],
                    "cached_input_tokens": usage["cached_input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "reasoning_tokens": usage["reasoning_tokens"],
                },
            },
        },
        "cost": {
            "currency": "USD",
            "total_micro_cents": total_cost_micro,
            "total_formatted": format_micro_cents_to_dollars(total_cost_micro),
        }
    }

