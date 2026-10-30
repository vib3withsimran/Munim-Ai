import sqlite3
import os
from datetime import datetime
from backend.app.core.config import settings

def get_db_path() -> str:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        rel_path = db_url.replace("sqlite:///", "")
        # Resolve path relative to project root
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        clean_path = rel_path.lstrip("./").lstrip(".\\")
        return os.path.join(base_dir, clean_path)
    return "munim.db"

def init_db():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table to protect against Meta webhook retry duplicates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_messages (
        message_id TEXT PRIMARY KEY,
        sender_phone TEXT,
        media_type TEXT,
        raw_text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table for storing basic interaction history / state
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_state (
        phone TEXT PRIMARY KEY,
        last_message_at DATETIME,
        is_private INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()

def is_duplicate_message(message_id: str) -> bool:
    """Returns True if this Meta message ID has already been received/processed."""
    if not message_id:
        return False
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def record_processed_message(message_id: str, sender_phone: str, media_type: str = "text", raw_text: str = ""):
    """Records the message ID in DB to prevent future duplicate processing."""
    if not message_id:
        return
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO processed_messages (message_id, sender_phone, media_type, raw_text)
    VALUES (?, ?, ?, ?)
    """, (message_id, sender_phone, media_type, raw_text))
    conn.commit()
    conn.close()

# Auto-initialize DB on import
init_db()

