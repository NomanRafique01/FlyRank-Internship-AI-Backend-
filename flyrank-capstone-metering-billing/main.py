from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from database import init_db
from routers import billable, usage, webhooks
from config import PORT

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Usage Metering & Billing Engine",
    description="Production-grade usage metering, quota enforcement, and Stripe subscription integration.",
    version="1.0.0",
    lifespan=lifespan
)

# Exception handlers for boundary validation
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": exc.errors()}
    )

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "Usage Metering & Billing Engine"}

# Include feature routers
app.include_router(billable.router)
app.include_router(usage.router)
app.include_router(webhooks.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

