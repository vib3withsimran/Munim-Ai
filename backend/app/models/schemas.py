from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class OrderItem(BaseModel):
    name: str = Field(description="Name or description of the product/item")
    qty: int = Field(default=1, description="Quantity of the item")
    size: Optional[str] = Field(default=None, description="Size (e.g. S, M, L, XL, XXL) if specified")
    color: Optional[str] = Field(default=None, description="Color if specified")
    unit_price: Optional[float] = Field(default=None, description="Price per unit if identified")

class ConfidenceScore(BaseModel):
    overall: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall confidence of the AI extraction (0.0 to 1.0)")
    items: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in item extraction")
    amount: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in amount extraction")

class ExtractedMessage(BaseModel):
    message_id: str = Field(default="", description="WhatsApp message ID (wamid.xxx)")
    timestamp: str = Field(default="", description="Message timestamp in ISO 8601 format")
    media_type: Literal["text", "audio", "image"] = Field(default="text", description="Type of media received")
    type: Literal[
        "order",
        "payment",
        "partial_payment",
        "question",
        "catalog_query",
        "delivery_query",
        "complaint",
        "command",
        "unknown"
    ] = Field(description="Classification of the incoming message")
    customer_phone: str = Field(description="Customer phone number in international format without +")
    customer_name: Optional[str] = Field(default=None, description="Extracted customer name if mentioned or known")
    items: List[OrderItem] = Field(default_factory=list, description="List of items mentioned in order")
    amount: Optional[float] = Field(default=None, description="Total amount mentioned or identified in currency INR")
    upi_txn_id: Optional[str] = Field(default=None, description="UPI reference/transaction ID if found in screenshot or text")
    linked_order_id: Optional[str] = Field(default=None, description="Order ID linked to this payment if known")
    delivery_address: Optional[str] = Field(default=None, description="Customer delivery address if provided")
    raw_text: str = Field(default="", description="The original or transcribed user message text")
    confidence: ConfidenceScore = Field(default_factory=ConfidenceScore)
    reply_needed: bool = Field(default=True, description="Whether an automated reply should be sent to customer")
    escalate_to_owner: bool = Field(default=False, description="Whether to escalate/alert the business owner")
    escalation_reason: Optional[str] = Field(default=None, description="Reason for escalating to owner")

    def items_readable(self) -> str:
        """Returns human-readable items string like '2x Kurti (M, pink)' for Google Sheets."""
        if not self.items:
            return ""
        parts = []
        for it in self.items:
            details = []
            if it.size:
                details.append(f"Size: {it.size}")
            if it.color:
                details.append(it.color)
            detail_str = f" ({', '.join(details)})" if details else ""
            parts.append(f"{it.qty}x {it.name}{detail_str}")
        return ", ".join(parts)

