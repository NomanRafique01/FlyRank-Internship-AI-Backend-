from config import PRICING_PER_MILLION_MICRO_CENTS

def calculate_token_cost_micro_cents(
    input_tokens: int = 0,
    cached_input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> int:
    """
    Computes total cost in micro-cents ($1 = 100,000,000 micro-cents)
    strictly using integer arithmetic to prevent floating-point rounding errors.
    
    Rules per Capstone Spec:
    - Cached input tokens are cheaper (50% off standard input).
    - Reasoning tokens count as output tokens.
    - Token categories cannot simply be added together without weighting.
    """
    input_cost = (input_tokens * PRICING_PER_MILLION_MICRO_CENTS["input"]) // 1_000_000
    cached_cost = (cached_input_tokens * PRICING_PER_MILLION_MICRO_CENTS["cached_input"]) // 1_000_000
    output_cost = (output_tokens * PRICING_PER_MILLION_MICRO_CENTS["output"]) // 1_000_000
    reasoning_cost = (reasoning_tokens * PRICING_PER_MILLION_MICRO_CENTS["reasoning"]) // 1_000_000

    return input_cost + cached_cost + output_cost + reasoning_cost

def format_micro_cents_to_dollars(micro_cents: int) -> str:
    """Format integer micro-cents into readable USD string e.g. $0.001234"""
    dollars = micro_cents / 100_000_000.0
    return f"${dollars:.6f}"
