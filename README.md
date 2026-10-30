# Munim AI 🧾🤖

> **Your WhatsApp is your assistant and your khata.**  
> Munim AI turns an Indian small seller's existing WhatsApp into two things simultaneously: an AI customer assistant that replies when the owner is offline, and a customer-wise self-updating ledger (orders, payments, dues) extracted from text, voice notes, and UPI screenshots. Zero new apps to learn.

---

## 🚀 Features

- 💬 **Hinglish & Multilingual AI**: Understands natural Hindi, Hinglish, and English buyer chats ("2 kurti medium mein pink wali").
- 📊 **Self-Updating Google Sheet Ledger**: Auto-creates and populates `Customers`, `Orders`, and `Payments` tabs in real time.
- 🏪 **Dynamic Catalog Integration**: Reads stock and prices directly from your `Catalog` tab — never invents prices or promises out-of-stock items.
- 🚨 **Human-in-the-Loop Escalation**: Automatically alerts the shop owner on WhatsApp when discounts, complaints, or custom requests occur.
- 🔒 **Privacy by Design**: First-word commands like `#private` pause the bot instantly; numbers in `PrivateList` are never logged or sent to AI.
- ⚡ **Offline / DRY_RUN Testing**: Full mock test suite allows testing the complete pipeline end-to-end even without active Meta Cloud credentials.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Messaging** | Meta WhatsApp Cloud API |
| **Backend Framework** | Python 3.11+, FastAPI, Uvicorn |
| **AI / Intent Extraction** | Google Gemini 3.5 Flash / 3.1 Flash Lite |
| **Audio Fallback** | Groq (Whisper Large v3) |
| **Ledger Storage** | Google Sheets API (`gspread`) |
| **State & Idempotency** | SQLite (webhook retry deduplication) |
| **Local Tunneling** | ngrok |
| **Containerization** | Docker |

---

## 📁 Project Structure

```
Munim AI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── api/routes/webhook.py    # GET (handshake) & POST (messages) webhook
│   │   ├── core/config.py           # Pydantic Settings & environment validation
│   │   ├── models/schemas.py        # Strict Pydantic models for intent extraction
│   │   ├── services/
│   │   │   ├── ai.py                # Gemini extraction & smart reply generator
│   │   │   ├── sheets.py            # Google Sheets CRUD & auto-tab setup
│   │   │   ├── whatsapp.py          # WhatsApp Cloud API message sender
│   │   │   └── db.py                # SQLite deduplication & state tracking
│   │   └── utils/privacy.py         # #private / #resume & PrivateList checker
│   └── data/                        # Local SQLite DB & service account key (gitignored)
├── docs/
│   ├── schema.md                    # Data contract between AI & storage
│   └── test_messages.md             # Curated Hinglish test dataset
├── scripts/
│   ├── check_env.py                 # Automated credentials & API validator
│   ├── test_webhook.py              # End-to-end mock webhook test suite
│   └── test_pipeline.py             # Pipeline simulation without network dependencies
├── .env.example                     # Environment variables template
├── .gitignore
├── Dockerfile                       # Production container setup (DigitalOcean / Vultr)
├── LICENSE                          # MIT License
├── requirements.txt
└── SECURITY.md                      # Security policy & Indian DPDP compliance
```

---

## 🔑 How to Get Each Required Credential (.env Guide)

Follow these step-by-step instructions to get every credential required in `.env`:

### 1. Google Gemini API Key (`GEMINI_API_KEY`)
1. Visit **[Google AI Studio](https://aistudio.google.com/)** and sign in with your Google account.
2. Click the blue **"Get API key"** button on the top left.
3. Click **"Create API key in new project"**.
4. Copy the key (starts with `AIzaSy...` or `AQ...`) and paste it as `GEMINI_API_KEY=...`.
5. Set `GEMINI_MODEL=gemini-3.5-flash`.

---

### 2. Google Sheets API & Service Account (`GOOGLE_SERVICE_ACCOUNT_JSON` & `GOOGLE_SHEET_ID`)

#### A. Generate Service Account JSON:
1. Open **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Create a new project (e.g., `Munim-AI`) or select an existing one.
3. Go to **APIs & Services** > **Library**.
4. Search for **"Google Sheets API"** and click **Enable**.
5. Search for **"Google Drive API"** and click **Enable**.
6. Go to **IAM & Admin** > **Service Accounts** > click **"Create Service Account"**.
7. Name it (e.g. `munim-sheets-bot`) and click **Done**.
8. Click on your newly created service account > go to the **Keys** tab > click **Add Key** > **Create new key** > select **JSON** > **Create**.
9. The JSON file will download automatically. Rename this file to `service_account.json` and move it to:
   ```
   backend/data/service_account.json
   ```
10. Note the service account email (e.g., `munim-sheets-bot@your-project.iam.gserviceaccount.com`).

#### B. Setup Google Sheet:
1. Create a blank Google Sheet in your [Google Drive](https://drive.google.com/).
2. Click **Share** (top right) and paste the **Service Account email** from step 10 with **Editor** permissions.
3. Copy the Sheet ID from your browser URL:
   ```
   https://docs.google.com/spreadsheets/d/<COPY_THIS_SHEET_ID_HERE>/edit
   ```
4. Paste it as `GOOGLE_SHEET_ID=...` in your `.env`.

*(Note: Munim AI automatically creates all required tabs — `Customers`, `Orders`, `Payments`, `Catalog`, `PrivateList` — on first run!)*

---

### 3. Meta WhatsApp Cloud API (`WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`)
1. Go to **[Meta for Developers](https://developers.facebook.com/)** and log in.
2. Click **My Apps** > **Create App** > select **Other** > choose **Business** type.
3. In the App Dashboard, scroll to **WhatsApp** and click **Set up**.
4. In the left navigation, open **WhatsApp** > **API Setup**:
   - Copy **Phone number ID** and paste as `WHATSAPP_PHONE_NUMBER_ID=...`.
   - Copy **Temporary access token** and paste as `WHATSAPP_ACCESS_TOKEN=...`.  
     *(Note: Dev tokens expire every 24 hours. Generate a fresh one when resuming work).*
5. Set `WHATSAPP_VERIFY_TOKEN` to any secure secret string (default: `munim_verify_2026`).
6. Set `WHATSAPP_API_VERSION=v19.0`.

---

### 4. Owner WhatsApp Number (`OWNER_WHATSAPP_NUMBER`)
- Enter your personal WhatsApp number in **international format without `+` or spaces**.
- Example for India: `919876543210`.
- Used to receive owner escalation alerts (custom discounts, complaints) and store summary reports.

---

### 5. Groq Whisper API Key (`GROQ_API_KEY`)
1. Go to **[Groq Console](https://console.groq.com/)** and create an account.
2. In the sidebar, click **API Keys** > **Create API Key**.
3. Name it `Munim-AI` and click **Submit**.
4. Copy the key (starts with `gsk_...`) and paste as `GROQ_API_KEY=...`.

---

## ⚡ Quick Start Guide

### 1. Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/vib3withsimran/Munim-Ai-.git
cd "Munim AI"

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Verify Credentials & Connections
Run the built-in diagnostic tool to test all credentials before running the server:
```bash
python scripts/check_env.py
```

---

## 🧪 Testing the Webhook

### Option A: Local Mock Test Suite (No Active Meta Account Needed!)
Test the entire pipeline (AI extraction, Google Sheets order creation, escalation alert, and deduplication) locally:
```bash
python scripts/test_webhook.py
```
This sends simulated WhatsApp payloads directly into FastAPI with `DRY_RUN=1` and prints outbound replies in your terminal.

---

### Option B: Live WhatsApp Testing (via ngrok)

1. **Start the FastAPI server:**
   ```bash
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```

2. **In a second terminal, launch ngrok:**
   ```bash
   ngrok http 8000
   ```

3. **Configure Meta Webhook:**
   - In Meta Developer Console > **WhatsApp** > **Configuration** > **Edit Webhook**.
   - **Callback URL**: `https://<YOUR-NGROK-SUBDOMAIN>.ngrok-free.app/webhook`
   - **Verify Token**: `munim_verify_2026`
   - Click **Verify and Save**.
   - Under **Webhook fields**, click **Manage** and subscribe to **`messages`**.

4. **Send a WhatsApp Message:**
   Send a text like *"2 kurti chahiye medium pink wali"* to your test business number and watch it reply and log directly to your Google Sheet!

---

## 🛡️ License & Compliance

- Distributed under the [MIT License](LICENSE).
- Complies with India's **Digital Personal Data Protection (DPDP) Act 2023** principles through data minimization and explicit `#private` opt-out switches. See [SECURITY.md](SECURITY.md) for details.
