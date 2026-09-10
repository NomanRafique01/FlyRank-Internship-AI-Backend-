from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to send to AI model / generator")
    simulated_tokens: Optional[Dict[str, int]] = Field(
        None,
        description="Optional simulation override for testing: {'input_tokens': int, 'cached_input_tokens': int, 'output_tokens': int, 'reasoning_tokens': int}"
    )

class TokenUsage(BaseModel):
    api_calls: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost_usd: str
    cost_micro_cents: int

class GenerateResponse(BaseModel):
    status: str
    tenant_id: str
    idempotency_key: str
    model: str
    result: str
    usage: TokenUsage
    _replayed: Optional[bool] = False

class CheckoutRequest(BaseModel):
    tenant_id: str
    plan_id: str = "pro"
    success_url: Optional[str] = "http://localhost:8000/billing/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url: Optional[str] = "http://localhost:8000/billing/cancel"
