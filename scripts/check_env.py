"""
Munim AI — Environment & API Validator
Run: python scripts/check_env.py
"""

import os
import sys
import json
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

# Load .env manually (no external deps needed)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
env_vars = {}
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            env_vars[key.strip()] = val.strip()

def get(key):
    return env_vars.get(key, "")

OK   = "[OK] "
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(label, passed, note=""):
    icon = OK if passed else FAIL
    results.append(passed)
    print(f"  {icon}  {label}" + (f"  →  {note}" if note else ""))

def warn(label, note=""):
    print(f"  {WARN}  {label}" + (f"  →  {note}" if note else ""))

# ── 1. Required fields present ────────────────────────────────────────────────
print("\n[1] Required fields in .env")

required = [
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_VERIFY_TOKEN",
    "OWNER_WHATSAPP_NUMBER",
    "GOOGLE_SHEET_ID",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "DATABASE_URL",
    "APP_SECRET_KEY",
]
for key in required:
    val = get(key)
    check(key, bool(val), "MISSING" if not val else "")

# ── 2. Format checks ──────────────────────────────────────────────────────────
print("\n[2] Format checks")

sheet_id = get("GOOGLE_SHEET_ID")
check("GOOGLE_SHEET_ID — no URL, just the ID",
      not sheet_id.startswith("http"),
      "Remove full URL, keep only the ID between /d/ and /edit" if sheet_id.startswith("http") else "")

owner = get("OWNER_WHATSAPP_NUMBER")
check("OWNER_WHATSAPP_NUMBER — digits only, no + or spaces",
      owner.isdigit(),
      f"Got: '{owner}' — remove +, spaces, country code should be included as digits" if not owner.isdigit() else f"Got: {owner}")

phone_id = get("WHATSAPP_PHONE_NUMBER_ID")
check("WHATSAPP_PHONE_NUMBER_ID — numeric",
      phone_id.isdigit(),
      f"Got: '{phone_id}'" if not phone_id.isdigit() else "")

gemini_key = get("GEMINI_API_KEY")
# Keys from Google AI Studio can start with AIza OR AQ. (newer format)
valid_prefix = gemini_key.startswith("AIza") or gemini_key.startswith("AQ.")
check("GEMINI_API_KEY format", valid_prefix,
      "Unexpected key format — re-check at aistudio.google.com" if not valid_prefix else "")

svc_path = get("GOOGLE_SERVICE_ACCOUNT_JSON")
svc_full = os.path.join(os.path.dirname(__file__), "..", svc_path.lstrip("./"))
check("service_account.json file exists",
      os.path.isfile(svc_full),
      f"Not found at: {svc_path} — download from Google Cloud Console" if not os.path.isfile(svc_full) else "")

# ── 3. Live API checks ────────────────────────────────────────────────────────
print("\n[3] Live API checks (needs internet)")

# 3a. WhatsApp Cloud API — get phone number info
print("  Checking WhatsApp Cloud API...")
wa_token = get("WHATSAPP_ACCESS_TOKEN")
wa_phone_id = get("WHATSAPP_PHONE_NUMBER_ID")
wa_version = get("WHATSAPP_API_VERSION") or "v19.0"
try:
    url = f"https://graph.facebook.com/{wa_version}/{wa_phone_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {wa_token}"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    check("WhatsApp Cloud API — token valid", True, f"Number: {data.get('display_phone_number','?')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    check("WhatsApp Cloud API — token valid", False, f"HTTP {e.code}: {body[:120]}")
except Exception as e:
    check("WhatsApp Cloud API — reachable", False, str(e)[:80])

# 3b. Gemini API
print("  Checking Gemini API...")
gemini_key = get("GEMINI_API_KEY")
gemini_model = get("GEMINI_MODEL") or "gemini-1.5-flash"
try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
    payload = json.dumps({"contents":[{"parts":[{"text":"Reply with just the word OK"}]}]}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    reply = data.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","?")
    check("Gemini API — key valid & model reachable", True, f"Model replied: {reply.strip()[:40]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    check("Gemini API — key valid", False, f"HTTP {e.code}: {body[:120]}")
except Exception as e:
    check("Gemini API — reachable", False, str(e)[:80])

# 3c. Groq API
print("  Checking Groq API...")
groq_key = get("GROQ_API_KEY")
try:
    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {groq_key}",
        "User-Agent": "MunimAI/1.0"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    models = [m["id"] for m in data.get("data", []) if "whisper" in m["id"].lower()]
    check("Groq API — key valid", True, f"Whisper models: {', '.join(models) or 'none found'}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    check("Groq API — key valid", False, f"HTTP {e.code}: {body[:120]}")
except Exception as e:
    check("Groq API — reachable", False, str(e)[:80])

# 3d. Google Sheets (just checks if service account JSON is valid)
print("  Checking Google service account JSON...")
if os.path.isfile(svc_full):
    try:
        with open(svc_full) as f:
            svc = json.load(f)
        expected_keys = {"type","project_id","private_key","client_email"}
        missing = expected_keys - set(svc.keys())
        check("service_account.json — valid structure", not missing,
              f"Missing keys: {missing}" if missing else f"Account: {svc.get('client_email','?')}")
    except Exception as e:
        check("service_account.json — parseable JSON", False, str(e))
else:
    check("service_account.json — skipped (file not found)", False, "Download from Google Cloud Console")

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(results)
total  = len(results)
print(f"\n{'='*50}")
print(f"  Result: {passed}/{total} checks passed")
if passed == total:
    print("  All good! Ready to start coding.")
else:
    print("  Fix the ✗ items above before proceeding.")
print(f"{'='*50}\n")
