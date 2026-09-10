import json
import sqlite3
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from database import get_db
from services.quota import check_quota
from services.pricing import calculate_token_cost_micro_cents, format_micro_cents_to_dollars
from services.openrouter import generate_completion

class MeterService:
    @staticmethod
    async def record_billable_action(
        tenant_id: str,
        idempotency_key: str,
        prompt: str,
        simulated_tokens: Optional[Dict[str, int]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Executes a billable AI action with guaranteed exactly-once metering.
        1. Checks idempotency cache. If key exists, replays cached response with zero new event recorded.
        2. Validates tenant quota (raises 429 if quota exceeded, 402 if subscription lapsed).
        3. Calls OpenRouter / simulator.
        4. Calculates cost using integer micro-cents arithmetic.
        5. Atomically writes usage event & caches response.
        """
        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Idempotency Check: return original response if replayed
            cursor.execute("""
                SELECT status_code, response_json
                FROM idempotency_cache
                WHERE idempotency_key = ? AND tenant_id = ?
            """, (idempotency_key, tenant_id))
            cached = cursor.fetchone()
            if cached:
                cached_status = cached["status_code"]
                cached_data = json.loads(cached["response_json"])
                cached_data["_replayed"] = True
                return cached_status, cached_data

            # 2. Check Quota boundaries before execution
            requested_qty = 0
            if simulated_tokens:
                requested_qty = simulated_tokens.get("input_tokens", 0) + simulated_tokens.get("output_tokens", 0)
            check_quota(conn, tenant_id, requested_tokens=requested_qty)

        # 3. Call AI Service (OpenRouter or deterministic simulation)
        ai_result = await generate_completion(prompt, simulated_tokens=simulated_tokens)
        token_info = ai_result["tokens"]

        cost_micro = calculate_token_cost_micro_cents(
            input_tokens=token_info["input_tokens"],
            cached_input_tokens=token_info["cached_input_tokens"],
            output_tokens=token_info["output_tokens"],
            reasoning_tokens=token_info["reasoning_tokens"]
        )

        response_payload = {
            "status": "success",
            "tenant_id": tenant_id,
            "idempotency_key": idempotency_key,
            "model": ai_result["model"],
            "result": ai_result["text"],
            "usage": {
                "api_calls": 1,
                "input_tokens": token_info["input_tokens"],
                "cached_input_tokens": token_info["cached_input_tokens"],
                "output_tokens": token_info["output_tokens"],
                "reasoning_tokens": token_info["reasoning_tokens"],
                "total_tokens": token_info["total_tokens"],
                "cost_usd": format_micro_cents_to_dollars(cost_micro),
                "cost_micro_cents": cost_micro,
            }
        }

        # 4. Atomic persistence of usage event and response cache
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO usage_events (
                        tenant_id, idempotency_key, event_type, quantity,
                        input_tokens, cached_input_tokens, output_tokens, reasoning_tokens,
                        cost_micro_cents
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tenant_id,
                    idempotency_key,
                    "ai_token",
                    token_info["total_tokens"],
                    token_info["input_tokens"],
                    token_info["cached_input_tokens"],
                    token_info["output_tokens"],
                    token_info["reasoning_tokens"],
                    cost_micro
                ))

                cursor.execute("""
                    INSERT INTO idempotency_cache (idempotency_key, tenant_id, status_code, response_json)
                    VALUES (?, ?, ?, ?)
                """, (
                    idempotency_key,
                    tenant_id,
                    status.HTTP_200_OK,
                    json.dumps(response_payload)
                ))
            except sqlite3.IntegrityError:
                # Concurrent race condition caught by UNIQUE constraint
                cursor.execute("""
                    SELECT status_code, response_json
                    FROM idempotency_cache
                    WHERE idempotency_key = ? AND tenant_id = ?
                """, (idempotency_key, tenant_id))
                cached = cursor.fetchone()
                if cached:
                    return cached["status_code"], json.loads(cached["response_json"])

        return status.HTTP_200_OK, response_payload

