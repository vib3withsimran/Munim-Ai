import json
import logging
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.app.core.config import settings
from backend.app.models.schemas import ExtractedMessage, OrderItem, ConfidenceScore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are 'Munim AI', an expert business assistant and accountant for small Indian home sellers (e.g., kurti/clothing, bakery, jewellery).
Your job is to read customer messages (in English, Hindi, or Hinglish) and return a strictly structured JSON object.

Output JSON Format:
{
  "type": "order" | "payment" | "partial_payment" | "question" | "catalog_query" | "delivery_query" | "complaint" | "command" | "unknown",
  "customer_name": string or null,
  "items": [
    {"name": string, "qty": number, "size": string or null, "color": string or null, "unit_price": number or null}
  ],
  "amount": number or null,
  "upi_txn_id": string or null,
  "linked_order_id": string or null,
  "delivery_address": string or null,
  "confidence": {
    "overall": number between 0.0 and 1.0,
    "items": number between 0.0 and 1.0,
    "amount": number between 0.0 and 1.0
  },
  "reply_needed": boolean,
  "escalate_to_owner": boolean,
  "escalation_reason": string or null
}

Rules for Classification:
- "order": customer wants to buy or place an order (e.g. "2 kurti chahiye medium mein", "send 1 pink suit")
- "payment": customer states they paid in full or sent payment proof (e.g. "599 bhej diya", "payment done via UPI")
- "partial_payment": customer offers advance/token money (e.g. "200 abhi de rahi hoon, baaki delivery pe")
- "catalog_query": asking about catalog, sizes, prices, what's in stock (e.g. "kurti ke kya sizes hain?", "price kya hai?")
- "delivery_query": asking when order will arrive or tracking (e.g. "mera parcel kab aayega?")
- "complaint": wrong size, damage, refund request, defect (e.g. "galat size aa gaya", "stitching kharab hai")
- "command": owner command (e.g. "summary", "pending dues", "#private", "#resume")
- "question": generic inquiry not covered above
- "unknown": gibberish, casual chatter ("hahaha", "👍")

Escalation Rules:
- Set "escalate_to_owner": true if:
  1. confidence.overall < 0.75
  2. type is "complaint" or "partial_payment"
  3. Custom price, discount requested, or unclear request
  Provide a concise "escalation_reason" in Hinglish/English.
- Return ONLY the JSON object. Do not enclose in markdown backticks.
"""

async def analyze_message(
    raw_text: str,
    customer_phone: str,
    message_id: str = "",
    timestamp: str = "",
    media_type: str = "text",
    catalog_summary: str = ""
) -> ExtractedMessage:
    """
    Extracts structured intent, items, amount, and confidence from customer message using Gemini.
    """
    if not timestamp:
        timestamp = datetime.now().isoformat()

    # Fast-path for empty or trivial inputs
    clean_text = raw_text.strip()
    if not clean_text or clean_text.lower() in ["hi", "hello", "hey", "namaste"]:
        return ExtractedMessage(
            message_id=message_id,
            timestamp=timestamp,
            media_type=media_type,
            type="question" if clean_text else "unknown",
            customer_phone=customer_phone,
            raw_text=raw_text,
            confidence=ConfidenceScore(overall=1.0, items=1.0, amount=1.0),
            reply_needed=True,
            escalate_to_owner=False
        )

    user_prompt = f"""
Customer Phone: {customer_phone}
Media Type: {media_type}
Message: "{clean_text}"
"""
    if catalog_summary:
        user_prompt += f"\nStore Catalog Context:\n{catalog_summary}\n"

    candidate_models = [settings.GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-2.5-pro"]
    
    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + user_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    data = resp.json()
                    raw_json = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(raw_json)

                    # Build items list
                    items = [
                        OrderItem(
                            name=it.get("name", "Item"),
                            qty=int(it.get("qty", 1)),
                            size=it.get("size"),
                            color=it.get("color"),
                            unit_price=float(it["unit_price"]) if it.get("unit_price") is not None else None
                        )
                        for it in parsed.get("items", [])
                    ]

                    conf_dict = parsed.get("confidence", {})
                    confidence = ConfidenceScore(
                        overall=float(conf_dict.get("overall", 0.9)),
                        items=float(conf_dict.get("items", 0.9)),
                        amount=float(conf_dict.get("amount", 0.9))
                    )

                    escalate = parsed.get("escalate_to_owner", False)
                    if confidence.overall < 0.75 or parsed.get("type") in ["complaint", "partial_payment"]:
                        escalate = True

                    return ExtractedMessage(
                        message_id=message_id,
                        timestamp=timestamp,
                        media_type=media_type,
                        type=parsed.get("type", "unknown"),
                        customer_phone=customer_phone,
                        customer_name=parsed.get("customer_name"),
                        items=items,
                        amount=float(parsed["amount"]) if parsed.get("amount") is not None else None,
                        upi_txn_id=parsed.get("upi_txn_id"),
                        linked_order_id=parsed.get("linked_order_id"),
                        delivery_address=parsed.get("delivery_address"),
                        raw_text=raw_text,
                        confidence=confidence,
                        reply_needed=parsed.get("reply_needed", True),
                        escalate_to_owner=escalate,
                        escalation_reason=parsed.get("escalation_reason")
                    )
                else:
                    logger.warning(f"Gemini API ({model_name}) returned status {resp.status_code}, trying fallback model if available...")
        except Exception as e:
            logger.warning(f"Error querying Gemini model {model_name}: {e}")

    # Fallback if Gemini request or JSON parse fails
    return ExtractedMessage(
        message_id=message_id,
        timestamp=timestamp,
        media_type=media_type,
        type="unknown",
        customer_phone=customer_phone,
        raw_text=raw_text,
        confidence=ConfidenceScore(overall=0.5, items=0.5, amount=0.5),
        reply_needed=True,
        escalate_to_owner=True,
        escalation_reason="AI extraction failed or timed out; manual owner review required."
    )


def generate_smart_reply(extracted: ExtractedMessage, catalog: List[Dict[str, Any]] = None) -> str:
    """
    Generates an automated, friendly Hinglish reply matching Indian small seller communication.
    """
    msg_type = extracted.type
    name = extracted.customer_name or "Ji"

    if msg_type == "order":
        items_str = extracted.items_readable() or "aapka order"
        amt_str = f" Total amount: ₹{int(extracted.amount)}." if extracted.amount else ""
        return (
            f"Namaste {name}! 🙏\n"
            f"Aapka order note kar liya hai: {items_str}.{amt_str}\n"
            f"Kripya apna delivery address bhej dijiye aur payment UPI se confirm karein."
        )

    elif msg_type == "payment":
        amt_str = f"₹{int(extracted.amount)} " if extracted.amount else ""
        return (
            f"Dhanyawaad {name}! 🙏\n"
            f"Aapki {amt_str}payment record kar li gayi hai. "
            f"Aapka parcel jald pack karke dispatch karenge."
        )

    elif msg_type == "partial_payment":
        amt_str = f"₹{int(extracted.amount)} " if extracted.amount else ""
        return (
            f"Namaste! 🙏\n"
            f"Aapki {amt_str}advance payment note kar li hai. "
            f"Owner jald aapse baaki balance aur delivery confirm karenge."
        )

    elif msg_type == "catalog_query":
        if catalog:
            items_list = []
            for c in catalog[:5]:
                avail = "Available" if str(c.get("available", "yes")).lower() in ["yes", "true", "1"] else "Out of stock"
                items_list.append(f"• {c.get('name')}: ₹{c.get('price')} ({avail})")
            catalog_text = "\n".join(items_list)
            return (
                f"Namaste! 🙏\n"
                f"Hamare paas ye collection available hai:\n\n{catalog_text}\n\n"
                f"Aapko kaunsa piece chahiye? Size bata dijiye!"
            )
        return "Namaste! Hamare paas premium kurtis aur ethnic wear available hai. Kaunsa size ya color chahiye aapko?"

    elif msg_type == "delivery_query":
        return (
            f"Namaste {name}! 🙏\n"
            f"Aapka order processing mein hai. Hum jald aapko dispatch aur tracking details share karenge."
        )

    elif msg_type == "complaint" or extracted.escalate_to_owner:
        return (
            f"Namaste {name}. 🙏\n"
            f"Aapka message note kar liya hai. Humare store owner jald aapse personally connect karenge."
        )

    else:
        return (
            "Namaste! 🙏 Munim AI Store Assistant mein aapka swagat hai.\n"
            "Aap order place kar sakte hain, collection dekh sakte hain ya payment proof bhej sakte hain."
        )
