# Live AI Test Report: OpenRouter Mistral Integration

**Author**: Noman Rafique<br>
**Engine**: FlyRank Usage Metering & Billing Engine<br>
**Provider**: OpenRouter API<br>
**Model**: `mistralai/mistral-small-24b-instruct-2501`<br>
**Date**: September 10, 2026<br>
**Status**: VERIFIED & PASSING

---

## 1. Test Overview

This test exercised live end-to-end billable AI generation using the OpenRouter API key configured in the git-ignored `.env` file.

It verified:
1. Real HTTP request routing through FastAPI to OpenRouter.
2. Extraction of provider token usage, including cached and reasoning token fields.
3. Integer micro-cent cost calculation using the pinned pricing constants.
4. Idempotent replay of an identical request.
5. Tenant usage rollup and quota accounting.

The duplicate `OPENROUTER_MODEL` setting in `.env` was removed before this run so the Mistral model was actually selected.

---

## 2. Initial Billable AI Generation

- **Endpoint**: `POST /generate`
- **Headers**:
  - `X-Tenant-Id: tenant_pro`
  - `Idempotency-Key: mistral-live-1789056423`
- **Request payload**:

```json
{
  "prompt": "Explain machine learning in exactly 8 words."
}
```

### Live Response: HTTP 200 OK

```json
{
  "status": "success",
  "tenant_id": "tenant_pro",
  "idempotency_key": "mistral-live-1789056423",
  "model": "mistralai/mistral-small-24b-instruct-2501",
  "result": "Machine learning is teaching computers to learn from data.",
  "usage": {
    "api_calls": 1,
    "input_tokens": 173,
    "cached_input_tokens": 0,
    "output_tokens": 11,
    "reasoning_tokens": 0,
    "total_tokens": 184,
    "cost_usd": "$0.000000",
    "cost_micro_cents": 31
  }
}
```

The response content is provider-generated. The prompt asks for eight words, but the provider returned a nine-word sentence; this did not affect routing, usage extraction, billing, or idempotency behavior.

---

## 3. Idempotency Retest

The exact same request was submitted again with the same tenant and idempotency key.

### Replayed Response: HTTP 200 OK

The replay returned the same model result and usage values, plus:

```json
{
  "_replayed": true
}
```

### Database Verification

```sql
SELECT COUNT(*)
FROM usage_events
WHERE idempotency_key = 'mistral-live-1789056423';
-- Result: 1
```

The retry therefore produced one billable database event, preventing duplicate charging.

---

## 4. Tenant Usage Rollup

- **Endpoint**: `GET /usage?tenant_id=tenant_pro`
- **Response**: HTTP 200 OK

The rollup after the test reported:

```json
{
  "tenant_id": "tenant_pro",
  "plan": {
    "id": "pro",
    "name": "Pro",
    "status": "active"
  },
  "usage": {
    "api_calls": {
      "used": 4,
      "limit": 10000,
      "remaining": 9996
    },
    "tokens": {
      "total_used": 425,
      "limit": 1000000,
      "remaining": 999575,
      "breakdown": {
        "input_tokens": 378,
        "cached_input_tokens": 0,
        "output_tokens": 47,
        "reasoning_tokens": 0
      }
    }
  },
  "cost": {
    "currency": "USD",
    "total_micro_cents": 81,
    "total_formatted": "$0.000001"
  }
}
```

The rollup is cumulative for `tenant_pro` and includes earlier live probes. The current Mistral test itself contributed one usage event, 184 tokens, and 31 micro-cents.

---

## 5. Verification Checklist

- [x] OpenRouter API key loaded from the git-ignored `.env` file without exposing it in this report.
- [x] Mistral model contacted successfully through OpenRouter.
- [x] FastAPI returned HTTP 200 for the billable request.
- [x] Provider token usage was extracted successfully.
- [x] Cost calculated as 31 integer micro-cents.
- [x] Exact retry returned `_replayed: true`.
- [x] SQLite contained exactly one event for the test idempotency key.
- [x] `GET /usage` returned the updated tenant rollup.

## 6. Validation Notes

The run emitted an existing `RequestsDependencyWarning` from the local Python environment. It did not affect the OpenRouter request or test result.
