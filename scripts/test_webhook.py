import os
import sys
import uuid
import asyncio
import httpx

sys.stdout.reconfigure(encoding="utf-8")

# Ensure DRY_RUN is enabled for testing
os.environ["DRY_RUN"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import app

def make_meta_payload(text: str, phone: str = "919876543210", name: str = "Priya Sharma", msg_id: str = None):
    """Creates a mock WhatsApp Cloud API webhook JSON payload exactly as Meta sends it."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15552055768",
                                "phone_number_id": "1428620580333948"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": name},
                                    "wa_id": phone
                                }
                            ],
                            "messages": [
                                {
                                    "from": phone,
                                    "id": msg_id or f"wamid.{uuid.uuid4().hex}",
                                    "timestamp": "1730000000",
                                    "type": "text",
                                    "text": {"body": text}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

async def run_tests():
    print("=" * 65)
    print("🧪 MUNIM AI — WEBHOOK TEST SUITE (MOCK META PAYLOADS)")
    print("=" * 65)

    # Use httpx.AsyncClient with ASGI app directly (no need to open external port)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        
        # Test 1: Catalog Query
        print("\n🔹 TEST 1: Catalog Query ('Kurti ka rate kya hai?')")
        p1 = make_meta_payload("Kurti ka rate kya hai?", phone="919876543210", name="Priya")
        r1 = await client.post("/webhook", json=p1)
        print(f"HTTP Status: {r1.status_code} | Response: {r1.json()}")

        # Test 2: Order Placement
        print("\n🔹 TEST 2: Order Placement ('Didi 2 anarkali kurti medium chahiye pink wali')")
        p2 = make_meta_payload("Didi 2 anarkali kurti medium chahiye pink wali", phone="919876543210", name="Priya")
        r2 = await client.post("/webhook", json=p2)
        print(f"HTTP Status: {r2.status_code} | Response: {r2.json()}")

        # Test 3: Discount / Ambiguity (Owner Escalation)
        print("\n🔹 TEST 3: Discount Request ('20% discount milega kya?') -> Should Escalate to Owner")
        p3 = make_meta_payload("20% discount milega kya?", phone="919876543210", name="Priya")
        r3 = await client.post("/webhook", json=p3)
        print(f"HTTP Status: {r3.status_code} | Response: {r3.json()}")

        # Test 4: Payment Confirmation
        print("\n🔹 TEST 4: Payment Confirmation ('Maine 1198 UPI kar diya check karo')")
        p4 = make_meta_payload("Maine 1198 UPI kar diya check karo", phone="919876543210", name="Priya")
        r4 = await client.post("/webhook", json=p4)
        print(f"HTTP Status: {r4.status_code} | Response: {r4.json()}")

        # Test 5: Duplicate Webhook Protection (Meta Retries)
        print("\n🔹 TEST 5: Duplicate Message Protection (Re-sending exact same message ID)")
        duplicate_id = f"wamid.fixed_duplicate_{uuid.uuid4().hex[:6]}"
        p5 = make_meta_payload("Hello test", msg_id=duplicate_id)
        
        r5_first = await client.post("/webhook", json=p5)
        print(f"First attempt: {r5_first.status_code}")
        
        r5_second = await client.post("/webhook", json=p5)
        print(f"Second attempt (Retry): {r5_second.status_code} (Should be silently ignored by SQLite deduplication)")

    print("\n" + "=" * 65)
    print("✅ WEBHOOK TEST SUITE COMPLETE!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_tests())

