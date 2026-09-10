import time
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from main import app
from database import get_db, init_db
from seed import seed_data
from config import STRIPE_WEBHOOK_SECRET, PRICING_PER_MILLION_MICRO_CENTS
from services.pricing import calculate_token_cost_micro_cents

client = TestClient(app)

def setup_module():
    seed_data()

def test_probe_1_idempotency():
    """
    PROBE 1 — Send the same billable request twice with one idempotency key
    -> exactly one usage event; the second response mirrors the first.
    """
    tenant_id = "tenant_free"
    key = f"idem-key-{time.time()}"
    payload = {"prompt": "Test idempotent prompt 1"}
    headers = {
        "X-Tenant-Id": tenant_id,
        "Idempotency-Key": key
    }

    # Count before
    with get_db() as conn:
        before_count = conn.execute(
            "SELECT COUNT(*) FROM usage_events WHERE idempotency_key = ?", (key,)
        ).fetchone()[0]

    # First request
    res1 = client.post("/generate", json=payload, headers=headers)
    assert res1.status_code == 200, f"Request 1 failed: {res1.text}"
    data1 = res1.json()

    # Second request (exact retry)
    res2 = client.post("/generate", json=payload, headers=headers)
    assert res2.status_code == 200, f"Request 2 failed: {res2.text}"
    data2 = res2.json()

    # Verify results
    assert data1["idempotency_key"] == data2["idempotency_key"]
    assert data1["usage"] == data2["usage"]
    assert data2.get("_replayed") is True

    # Count after in database: exactly 1 event
    with get_db() as conn:
        after_count = conn.execute(
            "SELECT COUNT(*) FROM usage_events WHERE idempotency_key = ?", (key,)
        ).fetchone()[0]

    assert before_count == 0
    assert after_count == 1, f"Expected exactly 1 event, got {after_count}"
    print("\n[PASS] PROBE 1: Idempotency verified. Duplicate request replayed cached result with 1 DB event.")

def test_probe_2_quota_enforcement():
    """
    PROBE 2 — Drive a tenant to its exact quota
    -> the request at the boundary behaves per your documented rule; the one after returns 429 / 402 with a clear message.
    """
    # 1. Test 402 Payment Required on lapsed tenant
    res_lapsed = client.post(
        "/generate",
        json={"prompt": "Should fail with 402"},
        headers={"X-Tenant-Id": "tenant_lapsed", "Idempotency-Key": f"key-lapsed-{time.time()}"}
    )
    assert res_lapsed.status_code == 402, f"Expected 402, got {res_lapsed.status_code}: {res_lapsed.text}"
    assert "Payment Required" in res_lapsed.text

    # 2. Test 429 Too Many Requests on quota exhaustion
    quota_tenant = "tenant_quota_test"
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO tenants (id, name) VALUES (?, ?)", (quota_tenant, "Quota Tester"))
        conn.execute("INSERT OR REPLACE INTO subscriptions (id, tenant_id, plan_id, status) VALUES (?, ?, 'free', 'active')", ("sub_quota", quota_tenant))
        # Set quota to limit: Free plan allows 1,000 calls. Insert 1,000 dummy events.
        conn.execute("DELETE FROM usage_events WHERE tenant_id = ?", (quota_tenant,))
        for i in range(1000):
            conn.execute("""
                INSERT INTO usage_events (tenant_id, idempotency_key, event_type, quantity, cost_micro_cents)
                VALUES (?, ?, 'api_call', 10, 50)
            """, (quota_tenant, f"fill-{i}"))

    # The 1,001st call must return 429
    res_exceeded = client.post(
        "/generate",
        json={"prompt": "Boundary breaker"},
        headers={"X-Tenant-Id": quota_tenant, "Idempotency-Key": f"key-boundary-{time.time()}"}
    )
    assert res_exceeded.status_code == 429, f"Expected 429, got {res_exceeded.status_code}: {res_exceeded.text}"
    assert "Retry-After" in res_exceeded.headers
    assert "Quota Exceeded" in res_exceeded.text
    print("\n[PASS] PROBE 2: Boundary honesty verified. Lapsed returns 402; exceeded limit returns 429 with Retry-After.")

def _generate_stripe_signature(payload_bytes: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"

def test_probe_3_and_4_stripe_webhooks():
    """
    PROBE 3 — Complete a Stripe test Checkout -> the webhook flips the tenant Free -> Pro; GET /usage shows the new limits.
    PROBE 4 — Send a forged webhook (bad signature) -> 400, nothing changes. Replay a real event twice -> processed once.
    """
    target_tenant = "tenant_free"

    # Verify initial plan is Free
    initial_usage = client.get(f"/usage?tenant_id={target_tenant}").json()
    assert initial_usage["plan"]["id"] == "free"
    assert initial_usage["usage"]["api_calls"]["limit"] == 1000

    # Probe 4A: Forged webhook (invalid signature) -> 400
    fake_payload = json.dumps({
        "id": "evt_fake_123",
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": target_tenant}}
    }).encode("utf-8")

    res_forged = client.post(
        "/webhooks/stripe",
        content=fake_payload,
        headers={"Stripe-Signature": "t=12345,v1=bad_signature_hash", "Content-Type": "application/json"}
    )
    assert res_forged.status_code == 400, f"Expected 400 for forged signature, got {res_forged.status_code}"

    # Verify tenant is still Free after forged webhook
    check_usage = client.get(f"/usage?tenant_id={target_tenant}").json()
    assert check_usage["plan"]["id"] == "free"

    # Probe 3: Legitimate webhook for checkout.session.completed -> flips tenant Free to Pro
    event_id = f"evt_checkout_{int(time.time())}"
    valid_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc123",
                "client_reference_id": target_tenant,
                "customer": "cus_test_upgraded",
                "subscription": "sub_test_upgraded"
            }
        }
    }
    valid_payload_bytes = json.dumps(valid_event).encode("utf-8")
    valid_sig = _generate_stripe_signature(valid_payload_bytes, STRIPE_WEBHOOK_SECRET)

    res_valid = client.post(
        "/webhooks/stripe",
        content=valid_payload_bytes,
        headers={"Stripe-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert res_valid.status_code == 200, f"Expected 200, got: {res_valid.text}"

    # Verify tenant is now Pro with new limits
    upgraded_usage = client.get(f"/usage?tenant_id={target_tenant}").json()
    assert upgraded_usage["plan"]["id"] == "pro", f"Expected plan 'pro', got: {upgraded_usage['plan']['id']}"
    assert upgraded_usage["usage"]["api_calls"]["limit"] == 10000
    assert upgraded_usage["usage"]["tokens"]["limit"] == 1000000

    # Probe 4B: Replay the exact same webhook twice -> ignored idempotently
    res_replay = client.post(
        "/webhooks/stripe",
        content=valid_payload_bytes,
        headers={"Stripe-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert res_replay.status_code == 200
    replay_json = res_replay.json()
    assert replay_json["outcome"]["status"] == "ignored"

    print("\n[PASS] PROBE 3 & 4: Stripe webhook signature verified, plan flipped Free -> Pro, duplicate replay ignored.")

def test_probe_5_pricing_math():
    """
    PROBE 5 — Check the pinned pricing rules -> cached-input and reasoning-token rules produce the exact expected totals; GET /usage matches.
    """
    pricing_tenant = "tenant_pricing_probe"
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO tenants (id, name) VALUES (?, ?)", (pricing_tenant, "Pricing Probe Tenant"))
        conn.execute("INSERT OR REPLACE INTO subscriptions (id, tenant_id, plan_id, status) VALUES (?, ?, 'pro', 'active')", ("sub_pricing", pricing_tenant))
        conn.execute("DELETE FROM usage_events WHERE tenant_id = ?", (pricing_tenant,))

    # Token breakdown:
    # 10,000 standard input tokens @ 150,000 micro-cents/1M = 1,500 micro-cents
    # 20,000 cached input tokens @ 75,000 micro-cents/1M (50% discount) = 1,500 micro-cents
    # 5,000 output tokens @ 600,000 micro-cents/1M = 3,000 micro-cents
    # 2,000 reasoning tokens @ 600,000 micro-cents/1M (same as output) = 1,200 micro-cents
    # Expected total cost = 1,500 + 1,500 + 3,000 + 1,200 = 7,200 micro-cents ($0.000072)
    expected_cost = calculate_token_cost_micro_cents(
        input_tokens=10000,
        cached_input_tokens=20000,
        output_tokens=5000,
        reasoning_tokens=2000
    )
    assert expected_cost == 7200, f"Expected 7200 micro cents, calculated {expected_cost}"

    # Fire request with simulated token breakdown
    res = client.post(
        "/generate",
        json={
            "prompt": "Evaluate pricing math",
            "simulated_tokens": {
                "input_tokens": 10000,
                "cached_input_tokens": 20000,
                "output_tokens": 5000,
                "reasoning_tokens": 2000,
            }
        },
        headers={
            "X-Tenant-Id": pricing_tenant,
            "Idempotency-Key": f"pricing-key-{time.time()}"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["usage"]["cost_micro_cents"] == 7200
    assert data["usage"]["cost_usd"] == "$0.000072"

    # Query GET /usage and verify rollups match exactly
    usage_res = client.get(f"/usage?tenant_id={pricing_tenant}")
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert usage_data["cost"]["total_micro_cents"] == 7200
    assert usage_data["cost"]["total_formatted"] == "$0.000072"
    assert usage_data["usage"]["tokens"]["breakdown"]["cached_input_tokens"] == 20000
    assert usage_data["usage"]["tokens"]["breakdown"]["reasoning_tokens"] == 2000

    print("\n[PASS] PROBE 5: Pricing rules verified. Cached input discounted, reasoning tokens priced as output, GET /usage matches exact totals.")

