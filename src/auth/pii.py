"""PII (Personally Identifiable Information) masking utilities.

Financial regulators require that sensitive data is masked in:
  - Audit logs (prevent PII leakage through operational data)
  - LLM prompts (prevent PII from reaching external model providers)
  - UI displays (need-to-know principle; analysts see masked data
    unless explicitly unmasking with audit trail)

Supported patterns:
  - Full names: "Chen Wei Lin" → "Chen ***"
  - Passport numbers: "E12345678" → "E****5678"
  - National ID / NRIC: "S1234567A" → "S****567A"
  - HKID: "A123456(7)" → "A***456(7)"
  - Dates of birth: "1985-03-15" → "1985-**-**"
  - Email addresses: "john@example.com" → "j***@example.com"
  - Phone numbers: "+65 9123 4567" → "+65 **** 4567"

Production notes:
  - This is a rule-based approach suitable for structured fields.
  - For unstructured text, pair with a Named Entity Recognition (NER)
    model to detect PII before masking.
  - Masking is irreversible by design — the original data stays in the
    encrypted source-of-truth database, never in logs or prompts.
"""

from __future__ import annotations

import re
from typing import Any


def mask_name(name: str) -> str:
    """Mask a full name, keeping only the first part (family name)."""
    if not name:
        return name
    parts = name.strip().split()
    if len(parts) <= 1:
        return parts[0][0] + "***" if parts else ""
    return parts[0] + " ***"


def mask_passport(number: str) -> str:
    """Mask a passport number, keeping first and last 4 characters."""
    if not number or len(number) < 5:
        return "****"
    return number[0] + "****" + number[-4:]


def mask_national_id(nric: str) -> str:
    """Mask NRIC/national ID: S1234567A → S****567A."""
    if not nric or len(nric) < 5:
        return "****"
    return nric[0] + "****" + nric[-3:]


def mask_hkid(hkid: str) -> str:
    """Mask Hong Kong ID: A123456(7) → A***456(7)."""
    match = re.match(r"([A-Z]{1,2})(\d+)\((\d)\)", hkid)
    if match:
        prefix, digits, check = match.groups()
        return f"{prefix}***{digits[-3:]}({check})"
    return mask_national_id(hkid)


def mask_date_of_birth(dob: str) -> str:
    """Mask DOB keeping only year: 1985-03-15 → 1985-**-**."""
    match = re.match(r"(\d{4})-\d{2}-\d{2}", dob)
    if match:
        return f"{match.group(1)}-**-**"
    return "****-**-**"


def mask_email(email: str) -> str:
    """Mask email: john.doe@example.com → j***@example.com."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return local[0] + "***@" + domain


def mask_phone(phone: str) -> str:
    """Mask phone number, keeping country code and last 4 digits."""
    digits = re.sub(r"[^\d+]", "", phone)
    if len(digits) < 8:
        return "****"
    return digits[:3] + " **** " + digits[-4:]


def mask_pii(text: str) -> str:
    """Apply pattern-based PII masking to free text.

    Detects and masks common PII patterns in unstructured text.
    For structured fields, use the specific mask_* functions above.
    """
    # Passport-like patterns (letter + 7-9 digits)
    text = re.sub(
        r"\b([A-Z])(\d{3,5})(\d{4})\b",
        lambda m: m.group(1) + "*" * len(m.group(2)) + m.group(3),
        text,
    )
    # Email addresses
    text = re.sub(
        r"\b([a-zA-Z0-9])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
        r"\1***@\2",
        text,
    )
    # Phone numbers with country code
    text = re.sub(
        r"(\+\d{1,3})\s*\d{4,5}\s*(\d{4})",
        r"\1 **** \2",
        text,
    )
    return text


def mask_customer_for_prompt(customer: dict[str, Any]) -> dict[str, Any]:
    """Create a PII-masked copy of customer data safe for LLM prompts.

    This ensures sensitive personal data never leaves the organization's
    boundary when calling external LLM APIs.
    """
    masked = dict(customer)
    if "full_name" in masked:
        masked["full_name"] = mask_name(masked["full_name"])
    if "company_name" in masked:
        pass  # company names are not PII
    if "date_of_birth" in masked:
        masked["date_of_birth"] = mask_date_of_birth(masked["date_of_birth"])
    if "email" in masked:
        masked["email"] = mask_email(masked["email"])
    if "phone" in masked:
        masked["phone"] = mask_phone(masked["phone"])
    if "passport_number" in masked:
        masked["passport_number"] = mask_passport(masked["passport_number"])
    if "national_id" in masked:
        masked["national_id"] = mask_national_id(masked["national_id"])
    return masked


def mask_submission_for_audit(submission: dict[str, Any]) -> dict[str, Any]:
    """Mask PII in a full submission record before writing to audit log."""
    masked = dict(submission)
    if "customer" in masked:
        masked["customer"] = mask_customer_for_prompt(masked["customer"])
    docs = masked.get("identification_documents", [])
    masked_docs = []
    for doc in docs:
        d = dict(doc)
        if "document_number" in d:
            d["document_number"] = mask_passport(d["document_number"])
        masked_docs.append(d)
    masked["identification_documents"] = masked_docs
    return masked
