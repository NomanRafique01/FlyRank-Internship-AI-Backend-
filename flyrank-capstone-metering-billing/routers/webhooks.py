import stripe
from fastapi import APIRouter, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
from config import STRIPE_WEBHOOK_SECRET
from models import CheckoutRequest
from services.stripe_svc import create_checkout_session, process_stripe_event

router = APIRouter(tags=["Billing & Stripe Webhooks"])

@router.post("/billing/checkout-session", summary="Create Stripe Checkout session to upgrade plan")
def create_checkout(request: CheckoutRequest):
    """
    Initiates a Stripe Checkout session in test mode for a tenant.
    """
    result = create_checkout_session(
        tenant_id=request.tenant_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url
    )
    return result

@router.post("/webhooks/stripe", summary="Stripe signed webhook endpoint")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
):
    """
    Receives and processes Stripe webhooks with cryptographic signature verification.
    - Invalid/forged signature -> 400 Bad Request
    - Duplicate event ID -> Ignored idempotently (returns 200)
    - Valid event -> Updates tenant plan/subscription state
    """
    payload = await request.body()

    # Cryptographic signature check
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'Stripe-Signature' header."
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forged or invalid Stripe webhook signature."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook parsing error: {str(e)}"
        )

    outcome = process_stripe_event(event)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True, "outcome": outcome})
