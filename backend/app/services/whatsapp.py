import httpx
import logging
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

async def send_whatsapp_message(to_phone: str, text: str) -> dict:
    """
    Sends a standard WhatsApp text reply to the specified phone number
    via Meta WhatsApp Cloud API (or logs in DRY_RUN mode).
    """
    clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")

    # DRY RUN mode: useful when Meta account or token is unavailable during development
    if settings.DRY_RUN:
        print(f"\n[DRY RUN WHATSAPP OUTBOUND] 📲 To +{clean_phone}:\n{text}\n" + "-"*50)
        return {"status": "dry_run_success", "recipient": clean_phone}

    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response_data = response.json()
            if response.status_code >= 400:
                logger.error(f"WhatsApp API Error ({response.status_code}): {response_data}")
            else:
                logger.info(f"WhatsApp message sent to {clean_phone}: {response_data}")
            return response_data
    except (httpx.HTTPError, ValueError, TypeError) as e:
        logger.error(f"Failed to send WhatsApp message to {clean_phone}: {e}")
        return {"error": str(e)}

