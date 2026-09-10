# Usage Metering & Billing Engine

Production-grade, zero-leak usage metering and subscription billing engine built with **Python 3**, **FastAPI**, **SQLite**, **Stripe Test Mode**, and **OpenRouter AI**.

Designed to handle high-frequency AI generation endpoints with guaranteed idempotency, strictly enforced quota boundaries, real-world token pricing rules, and signature-verified webhook synchronization.

---

## 1. System Architecture

```text
                               +------------------------------------------+
                               |              Client / Caller             |
                               +--------------------+---------------------+
                                                    |
                      POST /generate                |   GET /usage
         (X-Tenant-Id, Idempotency-Key)             |
                                                    v
                               +--------------------+---------------------+
                               |           FastAPI Gateway                |
                               +--------------------+---------------------+
                                                    |
             +--------------------------------------+--------------------------------------+
             |                                      |                                      |
             v                                      v                                      v
+------------------------+             +------------------------+             +------------------------+
|     MeterService       |             |      QuotaService      |             |     PricingService     |
| - Key deduplication    |             | - 429 Quota Exceeded   |             | - Input ($0.150 / 1M)  |
| - Atomic event logging |             | - 402 Payment Required |             | - Cached (50% disc.)   |
| - Replay cache lookup  |             | - Boundary check       |             | - Reasoning as output  |
+-----------+------------+             +------------------------+             +------------------------+
            |                                       |                                      |
            +-------------------+-------------------+--------------------------------------+
                                |
                                v
               +----------------------------------+
               |        Database (SQLite)         |
               | - tenants & subscriptions        |
               | - usage_events & cache           |
               | - processed_webhooks             |
               +----------------------------------+
                                ^
                                | Verified Webhook Events
               +----------------+-----------------+
               |          Stripe Webhook          |
               | - HMAC SHA256 Verification       |
               | - Replay Attack Deduplication    |
               | - Plan Synchronization           |
               +----------------------------------+
```

---

## 2. Plan Quotas & Boundaries

| Plan | Monthly Cost | API Call Quota | AI Token Quota | Boundary Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Free** | $0.00 | 1,000 calls / month | 100,000 tokens / month | `429 Too Many Requests` |
| **Pro** | $29.00 | 10,000 calls / month | 1,000,000 tokens / month | `429 Too Many Requests` |

- **Subscription Past Due / Lapsed**: When a customer's subscription is canceled or payment is past due, requests return `402 Payment Required`.

---

## 3. Real-World AI Token Pricing Rules

Token costs are calculated in integer micro-cents ($1 = 100,000,000 micro-cents) to eliminate floating point rounding error:
- **Standard Input Tokens**: \$0.150 / 1M tokens (150,000 micro-cents).
- **Cached Input Tokens**: \$0.075 / 1M tokens (50% discount = 75,000 micro-cents).
- **Standard Output Tokens**: \$0.600 / 1M tokens (600,000 micro-cents).
- **Reasoning Tokens**: Billed identically to output tokens (\$0.600 / 1M tokens).

---

## 4. Setup & Running

### Prerequisites
- Python 3.10+
- `pip`

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Inside `.env`, you can provide your OpenRouter API key:
```env
OPENROUTER_API_KEY=your_actual_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```
*(If no key is configured, the system automatically uses deterministic local simulation mode).*

### Step 3: Seed the Database
```bash
python seed.py
```

### Step 4: Run the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Run Automated Acceptance Tests (All 5 Probes)
```bash
pytest test_engine.py -v
```

---

## 5. API Endpoints

### 1. Billable Generation
`POST /generate`
- **Headers**:
  - `X-Tenant-Id: tenant_free`
  - `Idempotency-Key: my-unique-req-uuid`
- **Body**:
  ```json
  {
    "prompt": "Explain neural networks in one sentence"
  }
  ```

### 2. Tenant Usage Rollup
`GET /usage?tenant_id=tenant_free`

### 3. Stripe Checkout
`POST /billing/checkout-session`
- **Body**:
  ```json
  {
    "tenant_id": "tenant_free"
  }
  ```

### 4. Stripe Webhook
`POST /webhooks/stripe`
- Verifies `Stripe-Signature` header.
- Deduplicates replayed webhook events using `processed_webhooks`.
- Upgrades tenant plan Free -> Pro upon `checkout.session.completed`.

---

## 6. Limitations

- **Single Currency**: Currently prices in USD cents/micro-cents. Multi-currency foreign exchange rates are not modeled.
- **Billing Cycle Boundaries**: Quotas and rollups evaluate usage on calendar months (`YYYY-MM`). Staggered mid-month billing cycles are handled as full calendar periods.
- **SQLite Storage**: While production-grade for single-node deployments using WAL mode and ACID transactions, multi-node horizontal scaling requires PostgreSQL.

