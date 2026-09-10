# System Design Document: Usage Metering & Billing Engine

**Author**: Noman Rafique  
**Track**: FlyRank Internship (Backend AI Engineering)  
**Status**: Approved (Phase 1 Gate)

---

## 1. Problem Statement
Modern SaaS products billing on usage require high-precision tracking, strictly enforced quotas, and guaranteed idempotency. The system must prevent duplicate event recording on network retries, block requests when limits are exceeded, account for AI token pricing tiers (cached input, standard input, output, and reasoning tokens), and synchronize subscription states with Stripe test mode via signature-verified webhooks.

**Explicit Non-Goal**: Real monetary transactions, complex multi-tenant credit invoicing, and continuous proration calculations. Stripe test mode is exclusively used.

---

## 2. Data Model & Database Schema

The persistence layer uses SQLite (relational, ACID-compliant) with foreign keys enabled and dedicated indexes.

### Entities:

1. **`tenants`**
   - `id`: TEXT PRIMARY KEY (e.g., `tenant_free`, `tenant_pro`)
   - `name`: TEXT NOT NULL
   - `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

2. **`plans`**
   - `id`: TEXT PRIMARY KEY (`free`, `pro`)
   - `name`: TEXT NOT NULL
   - `max_api_calls`: INTEGER NOT NULL (Free: 1,000 / month; Pro: 10,000 / month)
   - `max_ai_tokens`: INTEGER NOT NULL (Free: 100,000 / month; Pro: 1,000,000 / month)
   - `monthly_price_cents`: INTEGER NOT NULL (Free: 0; Pro: 2900)

3. **`subscriptions`**
   - `id`: TEXT PRIMARY KEY
   - `tenant_id`: TEXT NOT NULL REFERENCES tenants(id)
   - `plan_id`: TEXT NOT NULL REFERENCES plans(id)
   - `status`: TEXT NOT NULL (e.g., `active`, `past_due`, `canceled`)
   - `stripe_customer_id`: TEXT
   - `stripe_subscription_id`: TEXT
   - `current_period_start`: TIMESTAMP
   - `current_period_end`: TIMESTAMP

4. **`usage_events`**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `tenant_id`: TEXT NOT NULL REFERENCES tenants(id)
   - `idempotency_key`: TEXT UNIQUE NOT NULL
   - `event_type`: TEXT NOT NULL (`api_call`, `ai_token`)
   - `quantity`: INTEGER NOT NULL
   - `input_tokens`: INTEGER DEFAULT 0
   - `cached_input_tokens`: INTEGER DEFAULT 0
   - `output_tokens`: INTEGER DEFAULT 0
   - `reasoning_tokens`: INTEGER DEFAULT 0
   - `cost_cents_micro`: INTEGER DEFAULT 0  (Integer math: $0.000001 per unit)
   - `timestamp`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

5. **`processed_webhooks`**
   - `event_id`: TEXT PRIMARY KEY (Stripe `evt_...` ID)
   - `event_type`: TEXT NOT NULL
   - `processed_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## 3. Plan & Quota Definitions

| Plan | Monthly Cost | API Call Quota | AI Token Quota | Overage Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Free** | $0.00 (0¢) | 1,000 calls / month | 100,000 tokens / month | Returns `429 Too Many Requests` |
| **Pro** | $29.00 (2,900¢) | 10,000 calls / month | 1,000,000 tokens / month | Returns `429 Too Many Requests` |

*Note*: If a tenant's subscription is canceled or payment is past due, the system returns `402 Payment Required`.

---

## 4. Metering API Contract & Idempotency Strategy

### Billable Endpoint:
- `POST /generate`
- **Headers**:
  - `X-Tenant-Id: <tenant_id>` (Required)
  - `Idempotency-Key: <uuid_or_unique_string>` (Required)
- **Request Body**:
  ```json
  {
    "prompt": "Explain quantum computing in one sentence",
    "simulated_tokens": null
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "tenant_id": "tenant_free",
    "idempotency_key": "abc-123",
    "result": "Quantum computing harnesses superposition and entanglement...",
    "usage": {
      "api_calls": 1,
      "total_tokens": 42,
      "input_tokens": 12,
      "cached_input_tokens": 0,
      "output_tokens": 30,
      "reasoning_tokens": 0
    }
  }
  ```

### Idempotency Guarantee:
1. Every incoming billable request passes through `MeterService`.
2. A lookup checks if `idempotency_key` has already been recorded for this tenant.
3. If an event with the same key exists, the original response is replayed immediately without incrementing usage metrics or charging tokens.
4. Database unique constraint `UNIQUE(idempotency_key)` guarantees exactly-once recording even under concurrent network retries.

---

## 5. Token Pricing Rules (Integer Cents Math)

Token pricing adheres strictly to real-world AI engine costing models:
- **Cached Input Tokens**: Billed at 50% discount compared to regular input tokens.
- **Reasoning Tokens**: Billed at standard output token rates.
- **Math Precision**: Costs calculated in micro-cents ($1 = 100 cents = 100,000,000 micro-cents) to ensure zero floating-point drift.

