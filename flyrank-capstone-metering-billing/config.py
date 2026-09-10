import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# App settings
PORT = int(os.getenv("PORT", 8000))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "billing.db"))

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Stripe configuration (Test Mode)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder").strip()

# Plan quotas per month
PLANS = {
    "free": {
        "name": "Free",
        "max_api_calls": 1000,
        "max_ai_tokens": 100000,
        "price_cents": 0,
    },
    "pro": {
        "name": "Pro",
        "max_api_calls": 10000,
        "max_ai_tokens": 1000000,
        "price_cents": 2900,  # $29.00
    },
}

# AI Token Pricing Constants (Pinned in config)
# Stored in micro-cents ($1 = 100 cents = 100,000,000 micro-cents)
# To avoid floating point issues, all cost math is strictly integer-based.
# Rates per 1,000,000 tokens (in integer cents):
# Input: $0.150 / 1M = 15 cents / 1M
# Cached input: $0.075 / 1M = 7.5 cents / 1M -> represented as 75,000 micro-cents / 1M
# Output: $0.600 / 1M = 60 cents / 1M
# Reasoning tokens: billed at output rate
PRICING_PER_MILLION_MICRO_CENTS = {
    "input": 150000,         # $0.150 per 1M tokens = 150,000 micro-cents
    "cached_input": 75000,   # $0.075 per 1M tokens (50% cheaper) = 75,000 micro-cents
    "output": 600000,        # $0.600 per 1M tokens = 600,000 micro-cents
    "reasoning": 600000,     # Reasoning tokens priced as output tokens
}
