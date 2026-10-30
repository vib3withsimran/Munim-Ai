import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import gspread
from google.oauth2.service_account import Credentials
from backend.app.core.config import settings
from backend.app.models.schemas import ExtractedMessage

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

TAB_HEADERS = {
    "Customers": ["phone", "name", "status", "last_seen", "total_due", "created_at"],
    "Orders": ["order_id", "customer_phone", "items_json", "items_readable", "amount", "amount_paid", "amount_due", "delivery_address", "status", "created_at", "updated_at"],
    "Payments": ["payment_id", "order_id", "customer_phone", "amount", "method", "upi_txn_id", "screenshot_url", "verified", "created_at"],
    "Catalog": ["product_id", "name", "aliases", "price", "available", "stock_qty", "description"],
    "PrivateList": ["phone"],
    "Dashboard": ["Metric", "Value"]
}

def get_service_account_path() -> str:
    path = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not os.path.isabs(path):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        path = os.path.join(base_dir, path.lstrip("./").lstrip(".\\"))
    return path

def get_sheets_client() -> Optional[gspread.Spreadsheet]:
    svc_path = get_service_account_path()
    if not os.path.isfile(svc_path) or not settings.GOOGLE_SHEET_ID:
        logger.warning(f"Google service account or Sheet ID not configured. Path: {svc_path}")
        return None

    try:
        creds = Credentials.from_service_account_file(svc_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
        return spreadsheet
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None


def init_spreadsheet_tabs():
    """
    Ensures all 6 tabs and standard headers exist in the Google Sheet.
    If a tab is missing, it creates it and sets the headers.
    """
    doc = get_sheets_client()
    if not doc:
        return

    try:
        existing_worksheets = {ws.title: ws for ws in doc.worksheets()}

        for tab_name, headers in TAB_HEADERS.items():
            if tab_name not in existing_worksheets:
                logger.info(f"Creating missing Google Sheet tab: {tab_name}")
                ws = doc.add_worksheet(title=tab_name, rows=100, cols=len(headers) + 2)
                ws.append_row(headers)
            else:
                ws = existing_worksheets[tab_name]
                rows = ws.get_all_values()
                if not rows:
                    ws.append_row(headers)

        # Populate sample catalog if Catalog tab only has headers
        catalog_ws = doc.worksheet("Catalog")
        if len(catalog_ws.get_all_values()) <= 1:
            catalog_ws.append_rows([
                ["PROD-001", "Cotton Anarkali Kurti", "kurti, kurta, pink kurti, anarkali", 599, "yes", 50, "Pink pure cotton flared anarkali kurti (Sizes: S, M, L, XL)"],
                ["PROD-002", "Chanderi Silk Suit Set", "suit, silk suit, salwar suit, set", 1299, "yes", 25, "Chanderi silk embroidered 3-piece suit with dupatta (Sizes: M, L, XL)"],
                ["PROD-003", "Straight Office Kurti", "office kurti, daily kurti, blue kurti", 450, "yes", 40, "Comfortable breathable daily wear straight kurti (Sizes: S, M, L, XL, XXL)"]
            ])
            logger.info("Populated default sample catalog items.")

    except Exception as e:
        logger.error(f"Error initializing Google Sheet tabs: {e}")


def add_or_update_customer(phone: str, name: Optional[str] = None, status: str = "active"):
    doc = get_sheets_client()
    if not doc:
        return

    try:
        ws = doc.worksheet("Customers")
        records = ws.get_all_records()
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if customer already exists
        for idx, row in enumerate(records, start=2): # start=2 accounting for 1-based index and header
            if str(row.get("phone", "")).strip() == str(phone).strip():
                # Update last seen and name if newly discovered
                ws.update_cell(idx, 4, now_iso)
                if name and not row.get("name"):
                    ws.update_cell(idx, 2, name)
                return

        # New Customer
        ws.append_row([
            str(phone),
            name or "",
            status,
            now_iso,
            f"=SUMIF(Orders!B:B, A{len(records) + 2}, Orders!G:G)", # formula for total_due
            now_iso
        ], value_input_option="USER_ENTERED")
        logger.info(f"Saved new customer {phone} to Google Sheet.")
    except Exception as e:
        logger.error(f"Error adding customer to Google Sheet: {e}")


def add_order(extracted: ExtractedMessage) -> str:
    """
    Appends a new order row to the Orders tab.
    Returns generated order_id.
    """
    doc = get_sheets_client()
    if not doc:
        return ""

    try:
        ws = doc.worksheet("Orders")
        records = ws.get_all_values()
        order_num = max(1, len(records))
        order_id = f"ORD-{order_num:03d}"

        items_json_str = json.dumps([it.model_dump() for it in extracted.items])
        items_readable = extracted.items_readable()
        amount = extracted.amount or 0.0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_idx = len(records) + 1

        # amount_due formula: = amount - amount_paid
        due_formula = f"=E{row_idx}-F{row_idx}"

        ws.append_row([
            order_id,
            extracted.customer_phone,
            items_json_str,
            items_readable,
            amount,
            0.0, # initial amount_paid
            due_formula,
            extracted.delivery_address or "",
            "pending",
            now_str,
            now_str
        ], value_input_option="USER_ENTERED")

        logger.info(f"Recorded Order {order_id} for {extracted.customer_phone} in Google Sheets.")
        return order_id
    except Exception as e:
        logger.error(f"Error adding order to Google Sheet: {e}")
        return ""


def add_payment(extracted: ExtractedMessage) -> str:
    """
    Appends a payment row to the Payments tab.
    Returns generated payment_id.
    """
    doc = get_sheets_client()
    if not doc:
        return ""

    try:
        ws = doc.worksheet("Payments")
        payment_id = f"PAY-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        verified_status = "yes" if extracted.confidence.amount >= 0.8 else "pending"

        ws.append_row([
            payment_id,
            extracted.linked_order_id or "",
            extracted.customer_phone,
            extracted.amount or 0.0,
            "upi",
            extracted.upi_txn_id or "",
            "", # screenshot_url placeholder
            verified_status,
            now_str
        ])

        logger.info(f"Recorded Payment {payment_id} for {extracted.customer_phone} in Google Sheets.")
        return payment_id
    except Exception as e:
        logger.error(f"Error adding payment to Google Sheet: {e}")
        return ""


def get_catalog() -> List[Dict[str, Any]]:
    """
    Reads all products currently defined in the Catalog tab.
    """
    doc = get_sheets_client()
    if not doc:
        return []

    try:
        ws = doc.worksheet("Catalog")
        return ws.get_all_records()
    except Exception as e:
        logger.error(f"Error fetching catalog from Google Sheet: {e}")
        return []


def is_in_privatelist(phone: str) -> bool:
    """
    Checks if phone number is listed in PrivateList tab.
    """
    doc = get_sheets_client()
    if not doc:
        return False

    try:
        ws = doc.worksheet("PrivateList")
        phones = ws.col_values(1)
        clean_target = phone.replace("+", "").strip()
        return any(p.replace("+", "").strip() == clean_target for p in phones[1:]) # skip header
    except Exception as e:
        logger.error(f"Error checking PrivateList: {e}")
        return False

def get_store_summary() -> str:
    """
    Computes a quick summary from the Orders tab for the store owner.
    """
    doc = get_sheets_client()
    if not doc:
        return "Unable to access Google Sheets right now."

    try:
        ws = doc.worksheet("Orders")
        records = ws.get_all_records()

        total_orders = len(records)
        pending_orders = sum(1 for r in records if str(r.get("status", "")).lower() == "pending")
        paid_orders = sum(1 for r in records if str(r.get("status", "")).lower() == "paid")
        
        total_sales = 0.0
        for r in records:
            try:
                total_sales += float(r.get("amount", 0) or 0)
            except (ValueError, TypeError):
                pass

        return (
            "📊 *Munim AI — Store Summary*\n"
            f"• Total Orders: {total_orders}\n"
            f"• Pending Dues/Orders: {pending_orders}\n"
            f"• Completed/Paid: {paid_orders}\n"
            f"• Total Sales Volume: ₹{total_sales:.2f}\n\n"
            "View full records in your Google Sheet."
        )
    except Exception as e:
        logger.error(f"Error computing store summary: {e}")
        return "Error fetching store summary from sheet."
