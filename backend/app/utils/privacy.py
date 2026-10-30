import sqlite3
import logging
from typing import Tuple
from backend.app.services.db import get_db_path
from backend.app.services.sheets import is_in_privatelist

logger = logging.getLogger(__name__)

def set_customer_privacy(phone: str, is_private: bool):
    """Updates customer privacy state in SQLite."""
    clean_phone = phone.replace("+", "").strip()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO customer_state (phone, is_private, last_message_at)
    VALUES (?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(phone) DO UPDATE SET is_private = excluded.is_private, last_message_at = CURRENT_TIMESTAMP
    """, (clean_phone, 1 if is_private else 0))
    conn.commit()
    conn.close()

def is_customer_private_in_db(phone: str) -> bool:
    """Checks if customer has privacy toggle enabled in SQLite."""
    clean_phone = phone.replace("+", "").strip()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT is_private FROM customer_state WHERE phone = ?", (clean_phone,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == 1:
        return True
    return False

def check_privacy(phone: str, text: str) -> Tuple[bool, str]:
    """
    Evaluates privacy signals and status.
    Returns: (is_private, action_message)
    """
    first_word = text.strip().split()[0].lower() if text.strip() else ""

    # Check privacy switch command
    if first_word == "#private":
        set_customer_privacy(phone, True)
        logger.info(f"Privacy activated for {phone} via #private")
        return (True, "Bot paused for this chat (#private activated).")

    if first_word == "#resume":
        set_customer_privacy(phone, False)
        logger.info(f"Privacy deactivated for {phone} via #resume")
        return (False, "Bot resumed for this chat (#resume activated).")

    # Check if previously marked private in local DB
    if is_customer_private_in_db(phone):
        return (True, "Chat is currently in private mode.")

    # Check if number exists in Sheet's PrivateList
    if is_in_privatelist(phone):
        return (True, "Number is in store's PrivateList.")

    return (False, "")

