# Security Policy & Privacy Compliance

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

---

## 1. Reporting a Vulnerability

If you discover a security vulnerability in Munim AI, please do **NOT** open a public issue.
Instead, report it via email to the maintainers or security contact with:
- A description of the issue.
- Steps to reproduce or proof-of-concept.
- Potential impact.

We strive to respond within 48 hours and release a patch promptly.

---

## 2. Secrets & Credential Protection

- **Never commit `.env` or Service Account Keys**: All credentials (`GEMINI_API_KEY`, `WHATSAPP_ACCESS_TOKEN`, `service_account.json`) must remain in your local untracked environment.
- Any secrets detected in commits should be revoked and rotated immediately.
- Use `scripts/check_env.py` to validate your environment without leaking keys into logs.

---

## 3. Privacy by Design (DPDP Act India Compliance)

Munim AI is designed for home-based and micro-sellers handling Indian customer data:

- **Strict Privacy Switch (`#private`)**:
  - When `#private` is triggered, customer conversations are discarded on arrival.
  - Private chats are **never** stored in SQLite or Google Sheets, and **never** transmitted to Gemini or third-party AI models.
- **Private Numbers List (`PrivateList`)**:
  - Numbers added to the `PrivateList` sheet (e.g. personal contacts, family) are automatically bypassed by the webhook processor.
- **Data Minimization**:
  - Only customer orders, business transactions, and payment verification IDs are preserved. Casual personal chatter is not stored.

