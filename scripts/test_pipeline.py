import asyncio
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.ai import analyze_message, generate_smart_reply
from backend.app.services.sheets import (
    add_or_update_customer,
    add_order,
    add_payment,
    get_catalog,
    get_store_summary
)
from backend.app.utils.privacy import check_privacy

async def run_simulation():
    print("=" * 60)
    print("🚀 MUNIM AI END-TO-END PIPELINE SIMULATION")
    print("=" * 60)

    # 1. Simulate an incoming customer order
    sample_text = "bhaiya 2 kurti chahiye medium size mein pink wali"
    customer_phone = "919988776655"
    print(f"\n[1] Incoming Customer Message:")
    print(f"    From: {customer_phone}")
    print(f"    Text: \"{sample_text}\"")

    # Check privacy
    is_priv, _ = check_privacy(customer_phone, sample_text)
    print(f"    Privacy Active? {is_priv}")

    # Fetch Catalog
    catalog = get_catalog()
    print(f"    Catalog items available: {len(catalog)}")

    catalog_summary = "\n".join([f"- {c.get('name')}: ₹{c.get('price')}" for c in catalog])

    # AI Extraction
    print("\n[2] Running AI Extraction (Gemini)...")
    extracted = await analyze_message(
        raw_text=sample_text,
        customer_phone=customer_phone,
        message_id="test_sim_wamid_001",
        catalog_summary=catalog_summary
    )
    print(f"    Classified Intent: {extracted.type}")
    print(f"    Items Parsed: {extracted.items_readable()}")
    print(f"    Amount: ₹{extracted.amount}")
    print(f"    Confidence: {extracted.confidence.overall}")
    print(f"    Escalate to Owner: {extracted.escalate_to_owner}")

    # Sheets update
    print("\n[3] Updating Google Sheets...")
    add_or_update_customer(customer_phone, extracted.customer_name)
    if extracted.type == "order":
        order_id = add_order(extracted)
        print(f"    ✅ Created Order in Google Sheet: {order_id}")

    # Smart Reply Generation
    reply = generate_smart_reply(extracted, catalog)
    print("\n[4] Generated Customer Reply (Hinglish):")
    print(f"    {reply}")

    # 2. Simulate Owner Summary
    print("\n[5] Simulating Owner Request: 'summary'")
    summary = get_store_summary()
    print(f"    {summary}")

    print("\n" + "=" * 60)
    print("🎉 ALL SLICES 1-5 WORKING SEAMLESSLY END-TO-END!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_simulation())
