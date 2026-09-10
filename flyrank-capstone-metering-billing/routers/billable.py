from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
from models import GenerateRequest
from services.metering import MeterService

router = APIRouter(tags=["Billable"])

@router.post("/generate", summary="Execute billable AI generation request")
async def generate(
    request: GenerateRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Core billable endpoint.
    - Requires X-Tenant-Id and Idempotency-Key headers.
    - Idempotent: Same key + tenant replays original response with zero duplicate charge.
    - Quota enforced: 429 when monthly quota exceeded, 402 if subscription is unpaid/past due.
    """
    if not x_tenant_id or not x_tenant_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Tenant-Id' is required."
        )

    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'Idempotency-Key' is required."
        )

    status_code, result = await MeterService.record_billable_action(
        tenant_id=x_tenant_id.strip(),
        idempotency_key=idempotency_key.strip(),
        prompt=request.prompt,
        simulated_tokens=request.simulated_tokens,
    )

    return JSONResponse(status_code=status_code, content=result)

