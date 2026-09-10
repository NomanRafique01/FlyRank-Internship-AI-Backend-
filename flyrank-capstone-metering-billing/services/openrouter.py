import json
import httpx
from typing import Dict, Any, Optional
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL

async def generate_completion(
    prompt: str,
    simulated_tokens: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Generates text and retrieves exact token counts.
    - If simulated_tokens is supplied (used for testing boundary conditions & pricing probes),
      it returns the simulated numbers immediately.
    - If OPENROUTER_API_KEY is configured in .env, it calls the live OpenRouter API.
    - If no key is configured and no simulation provided, it safely falls back to a deterministic simulation.
    """
    if simulated_tokens:
        input_tokens = simulated_tokens.get("input_tokens", 10)
        cached_input = simulated_tokens.get("cached_input_tokens", 0)
        output_tokens = simulated_tokens.get("output_tokens", 25)
        reasoning_tokens = simulated_tokens.get("reasoning_tokens", 0)
        total = input_tokens + cached_input + output_tokens + reasoning_tokens
        return {
            "text": f"[Simulated Response] Generated content for: {prompt[:40]}...",
            "tokens": {
                "input_tokens": input_tokens,
                "cached_input_tokens": cached_input,
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": total,
            },
            "model": "simulated/deterministic-engine",
        }

    # If OpenRouter API key is set, call live API
    if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "your_openrouter_api_key_here":
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/NomanRafique01/FlyRank-Internship-AI-Backend-",
            "X-Title": "FlyRank Usage Metering Billing Engine",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Extract token details (cached, reasoning)
            prompt_details = usage.get("prompt_tokens_details", {})
            comp_details = usage.get("completion_tokens_details", {})

            cached_input = prompt_details.get("cached_tokens", 0)
            reasoning_tokens = comp_details.get("reasoning_tokens", 0)
            input_tokens = usage.get("prompt_tokens", 0) - cached_input
            if input_tokens < 0:
                input_tokens = usage.get("prompt_tokens", 0)

            output_tokens = usage.get("completion_tokens", 0) - reasoning_tokens
            if output_tokens < 0:
                output_tokens = usage.get("completion_tokens", 0)

            total_tokens = usage.get("total_tokens", input_tokens + cached_input + output_tokens + reasoning_tokens)

            return {
                "text": choice,
                "tokens": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached_input,
                    "output_tokens": output_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "total_tokens": total_tokens,
                },
                "model": data.get("model", OPENROUTER_MODEL),
            }

    # Deterministic fallback when no API key is provided
    calc_input = max(5, len(prompt.split()) * 2)
    calc_output = 20
    return {
        "text": f"Billing Engine simulated completion for: '{prompt}'",
        "tokens": {
            "input_tokens": calc_input,
            "cached_input_tokens": 0,
            "output_tokens": calc_output,
            "reasoning_tokens": 0,
            "total_tokens": calc_input + calc_output,
        },
        "model": "simulated/local-mode",
    }
