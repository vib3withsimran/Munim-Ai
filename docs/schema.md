# Munim AI — Data Schema (Finalized v2)

> This is the contract between the AI layer and the storage layer.  
> Do **not** change column names without updating both the AI prompt and the Sheet/DB simultaneously.

---

## AI Structured JSON Output

Every message processed by Gemini must return this exact shape:

```json
{
  "message_id": "wamid.xxx",
  "timestamp": "2026-10-30T15:30:00+05:30",
  "media_type": "text | audio | image",
  "type": "order | payment | partial_payment | question | catalog_query | delivery_query | complaint | command | unknown",
  "customer_phone": "919876543210",
  "customer_name": null,
  "items": [
    {
      "name": "kurti",
      "qty": 2,
      "size": "M",
      "color": null,
      "unit_price": null
    }
  ],
  "amount": 599,
  "upi_txn_id": null,
  "linked_order_id": null,
  "delivery_address": null,
  "raw_text": "original or transcribed message text",
  "confidence": {
    "overall": 0.92,
    "items": 0.95,
    "amount": 0.88
  },
  "reply_needed": true,
  "escalate_to_owner": false,
  "escalation_reason": null
}
```

### Field notes

| Field | Source | Notes |
|---|---|---|
| `message_id` | Meta webhook (`wamid.xxx`) | Idempotency key — check SQLite before processing. Meta retries failed webhooks. |
| `timestamp` | Meta webhook (`messages[].timestamp`) | Use this, NOT server time. Convert Unix epoch → ISO 8601. |
| `media_type` | Webhook `messages[].type` | `text` / `audio` / `image` |
| `customer_name` | WhatsApp profile OR AI extraction from message ("main Neha hoon") | Nullable. Used to populate Customers tab. |
| `unit_price` | AI extraction from screenshot or message | Nullable. Catalog lookup happens post-extraction. |
| `linked_order_id` | AI inference from context | Nullable. See Payment→Order Linking section below. |
| `confidence.overall` | AI self-rating | Threshold < 0.75 → escalate to owner |
| `escalation_reason` | AI explanation string | Human-readable, sent to owner in escalation message |

### `type` field values

| Value | When to use |
|---|---|
| `order` | Customer is placing a new order |
| `payment` | Customer sent UPI screenshot or confirmed full payment |
| `partial_payment` | Customer mentioned advance / partial amount |
| `question` | Generic question not about catalog (e.g. "kab milega?") |
| `catalog_query` | Asking about products, sizes, prices, availability |
| `delivery_query` | Asking about delivery status of an existing order |
| `complaint` | Wrong item, damage, refund request |
| `command` | Owner command (summary, balance, #private, #resume) |
| `unknown` | Cannot classify confidently |

### Escalation rules

Set `escalate_to_owner: true` when:
- `confidence.overall < 0.75`
- `type` is `complaint` or `partial_payment`
- Item or price not found in catalog
- `linked_order_id` is null on a payment and customer has multiple pending orders
- Customer explicitly asks to speak to owner

---

## Payment → Order Linking Logic

This is the hardest mapping problem. Handle in this priority order:

1. **`upi_txn_id` match** — if screenshot has a transaction ID and it's unique, link directly.
2. **Amount match** — if customer has exactly one pending order with the same amount, auto-link.
3. **Ambiguous** — customer has multiple pending orders with the same or similar amount → set `linked_order_id: null`, set `escalate_to_owner: true`, include in `escalation_reason`:  
   `"₹599 payment received — is this for Order #12 (pink kurti) or Order #15 (blue set)?"`
4. **No pending orders** — store payment as unlinked, alert owner.

> Never silently guess when ambiguous. Always escalate.

---

## Google Sheets Structure

### Tab: `Customers`

| Column | Type | Notes |
|---|---|---|
| `phone` | string | Primary key, international format (no +) |
| `name` | string | From WhatsApp profile or AI extraction |
| `status` | enum | `active` / `private` |
| `last_seen` | datetime | Updated on every inbound message |
| `total_due` | formula | `=SUMIF(Orders!B:B, A2, Orders!M:M)` — sum of `amount_due` per customer |
| `created_at` | datetime | First message timestamp |

### Tab: `Orders`

| Column | Type | Notes |
|---|---|---|
| `order_id` | string | Auto-generated, e.g. `ORD-001` |
| `customer_phone` | string | FK → Customers |
| `items_json` | string | Raw JSON array — for programmatic use |
| `items_readable` | string | Human-readable, e.g. `2x Kurti (M, pink), 1x Dupatta` — for owner |
| `amount` | number | Total order amount |
| `amount_paid` | number | Updated on each linked payment |
| `amount_due` | formula | `= amount - amount_paid` |
| `delivery_address` | string | Nullable |
| `status` | enum | `pending` / `partially_paid` / `paid` / `cancelled` |
| `created_at` | datetime | From message timestamp |
| `updated_at` | datetime | Updated on every status change |

### Tab: `Payments`

| Column | Type | Notes |
|---|---|---|
| `payment_id` | string | Auto-generated UUID |
| `order_id` | string | FK → Orders. Nullable if unlinked. |
| `customer_phone` | string | |
| `amount` | number | |
| `method` | enum | `upi` / `cash` / `other` |
| `upi_txn_id` | string | Extracted from screenshot. Nullable. |
| `screenshot_url` | string | WhatsApp media URL. **Note: expires after ~5 days — download and store locally if needed.** |
| `verified` | enum | `pending` / `yes` / `no` — owner confirms low-confidence AI reads |
| `created_at` | datetime | From message timestamp |

### Tab: `Catalog`

| Column | Type | Notes |
|---|---|---|
| `product_id` | string | |
| `name` | string | Canonical product name |
| `aliases` | string | Comma-separated alternate names e.g. `kurti,kurta,kurt,top` — AI uses this for fuzzy matching |
| `price` | number | |
| `available` | boolean | `yes` / `no` |
| `stock_qty` | number | Nullable. For future inventory tracking. |
| `description` | string | Used by AI to generate replies |

### Tab: `PrivateList`

| Column | Type | Notes |
|---|---|---|
| `phone` | string | Numbers never sent to AI or stored |

### Tab: `Dashboard`

Formula-driven only — no manual rows.  
Suggested charts (all auto-update when rows are added):
- Sales per day (Orders `created_at` vs `amount`)
- Pending dues by customer (`total_due` from Customers)
- Top products (parse `items_readable`)
- Paid vs Pending orders (status breakdown)
