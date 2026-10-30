import logging
from datetime import datetime
from fastapi import APIRouter, Request, Query, Response, status

from backend.app.core.config import settings
from backend.app.services.db import is_duplicate_message, record_processed_message
from backend.app.services.whatsapp import send_whatsapp_message
from backend.app.services.ai import analyze_message, generate_smart_reply
from backend.app.services.sheets import (
    add_or_update_customer,
    add_order,
    add_payment,
    get_catalog,
    get_store_summary
)
from backend.app.utils.privacy import check_privacy

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Meta Webhook Verification Handshake (GET).
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verification handshake successful!")
        return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)
    
    logger.warning(f"Webhook verification failed. Token provided: {hub_verify_token}")
    return Response(content="Verification token mismatch", status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Full Munim AI Webhook Pipeline (POST):
    1. Deduplication check
    2. Privacy filtering (#private / #resume / PrivateList)
    3. Owner command interception (summary, dues)
    4. AI Multimodal extraction (Gemini)
    5. Google Sheets auto-update (Customers, Orders, Payments)
    6. Owner escalation on low confidence / complaints
    7. Customer auto-reply
    """
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Error parsing webhook JSON: {e}")
        return Response(content="Invalid JSON", status_code=status.HTTP_400_BAD_REQUEST)

    entries = data.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            
            # Skip status callbacks (sent, delivered, read)
            if "statuses" in value and "messages" not in value:
                continue

            # Extract profile name if present
            contacts = value.get("contacts", [])
            contact_name = contacts[0].get("profile", {}).get("name") if contacts else None

            messages = value.get("messages", [])
            for msg in messages:
                message_id = msg.get("id")
                sender_phone = msg.get("from", "")
                msg_type = msg.get("type", "unknown")
                msg_timestamp = msg.get("timestamp")

                # Format ISO timestamp
                if msg_timestamp:
                    try:
                        timestamp_iso = datetime.fromtimestamp(int(msg_timestamp)).isoformat()
                    except Exception:
                        timestamp_iso = datetime.now().isoformat()
                else:
                    timestamp_iso = datetime.now().isoformat()

                # Deduplication check
                if is_duplicate_message(message_id):
                    logger.info(f"Duplicate message ignored: {message_id}")
                    continue

                raw_text = ""
                if msg_type == "text":
                    raw_text = msg.get("text", {}).get("body", "")
                elif msg_type in ["audio", "voice"]:
                    raw_text = "[Voice Note / Audio Message]"
                elif msg_type == "image":
                    raw_text = "[Image Message / UPI Screenshot]"
                else:
                    raw_text = f"[{msg_type} message]"

                # Record message to prevent re-processing on webhook retries
                record_processed_message(
                    message_id=message_id,
                    sender_phone=sender_phone,
                    media_type=msg_type,
                    raw_text=raw_text
                )

                logger.info(f"Processing incoming message from {sender_phone} ({msg_type}): {raw_text}")

                # 1. Privacy Filter Check
                is_private, privacy_msg = check_privacy(sender_phone, raw_text)
                if is_private:
                    logger.info(f"Private chat active for {sender_phone}. Bypassing AI processing and storage.")
                    # Acknowledge if this was the triggering #private command
                    if raw_text.strip().lower().startswith("#private"):
                        await send_whatsapp_message(sender_phone, "🔒 Munim AI assistant paused for this chat. Type #resume to restart.")
                    continue

                if raw_text.strip().lower().startswith("#resume"):
                    await send_whatsapp_message(sender_phone, "🔓 Munim AI assistant resumed for this chat.")
                    continue

                # 2. Check for Owner Commands
                clean_sender = sender_phone.replace("+", "").strip()
                clean_owner = settings.OWNER_WHATSAPP_NUMBER.replace("+", "").strip()
                lower_text = raw_text.strip().lower()

                if clean_sender and clean_sender == clean_owner and lower_text in ["summary", "pending dues", "dues", "hisaab"]:
                    summary_text = get_store_summary()
                    await send_whatsapp_message(sender_phone, summary_text)
                    continue

                # 3. AI Extraction (Gemini)
                catalog = get_catalog()
                catalog_summary = "\n".join([
                    f"- {c.get('name')}: ₹{c.get('price')} (Sizes/Details: {c.get('description', '')})"
                    for c in catalog
                ])

                extracted = await analyze_message(
                    raw_text=raw_text,
                    customer_phone=sender_phone,
                    message_id=message_id,
                    timestamp=timestamp_iso,
                    media_type=msg_type,
                    catalog_summary=catalog_summary
                )

                logger.info(f"Extracted intent for {sender_phone}: {extracted.type} (confidence: {extracted.confidence.overall})")

                # 4. Update Google Sheets (Customers, Orders, Payments)
                customer_display_name = extracted.customer_name or contact_name
                add_or_update_customer(
                    phone=sender_phone,
                    name=customer_display_name,
                    status="active"
                )

                if extracted.type == "order":
                    add_order(extracted)

                elif extracted.type in ["payment", "partial_payment"]:
                    add_payment(extracted)

                # 5. Owner Escalation Check
                if extracted.escalate_to_owner and clean_owner:
                    reason = extracted.escalation_reason or "Customer inquiry requires manual attention."
                    escalation_alert = (
                        "🚨 *Munim AI Alert — Attention Needed*\n"
                        f"• Customer: +{sender_phone}\n"
                        f"• Type: {extracted.type}\n"
                        f"• Reason: {reason}\n"
                        f"• Message: \"{raw_text}\""
                    )
                    await send_whatsapp_message(clean_owner, escalation_alert)
                    logger.info(f"Escalated message to owner ({clean_owner}).")

                # 6. Customer Auto-Reply
                if extracted.reply_needed:
                    reply_text = generate_smart_reply(extracted, catalog)
                    await send_whatsapp_message(sender_phone, reply_text)
                    logger.info(f"Replied to customer {sender_phone}: {reply_text[:60]}...")

    return {"status": "success"}
