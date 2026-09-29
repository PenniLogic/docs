"""
PenniLogic — deterministic SMS parser spike
===========================================

Purpose
-------
Validate ADR-003: that a *deterministic* parser (no ML, no network, runs on any
device) can extract structured transactions from real Indian bank SMS formats.

This is a research spike, not production code. It exists to answer one question
before we commit to the architecture:

    Can we reliably parse real bank SMS with regex alone?

Why this matters
----------------
The AI research recommended an on-device LLM as the *primary* parser. That model
needs ~8GB RAM flagship hardware, and India — our launch market — is largely
mid-range devices. ADR-003 inverts it: deterministic parser primary, LLM only for
the long tail. This spike tests whether that inversion is justified.

Design rules being validated
----------------------------
1. Money is NEVER a float. Amounts parse to integer minor units (paise).
2. Only structured output leaves the device — the raw SMS body is never
   returned, only a hash for deduplication (ADR-004).
3. Unparseable messages fail CLOSED (return None) so they route to the
   "what was this?" clarification flow rather than silently producing a wrong
   number.

Run:  python docs/research/spikes/sms_parser_spike.py
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

# --------------------------------------------------------------------------
# Domain types
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedTransaction:
    """The ONLY thing permitted to leave the device.

    Note the deliberate absence of a raw-text field: the shape itself makes it
    structurally impossible to transmit the original message (ADR-004).
    """

    amount_minor: int  # paise — never a float
    currency: str
    direction: str  # DEBIT | CREDIT
    merchant: Optional[str]
    account_ref: Optional[str]  # last 4 only, never a full account number
    occurred_on: Optional[date]
    raw_hash: str  # dedupe across SMS / notification channels
    confidence: float
    matched_rule: str


# --------------------------------------------------------------------------
# Amount parsing
# --------------------------------------------------------------------------

# Handles: Rs.1,250.00 | INR 450.00 | Rs 85000.00 | Rs 1,250
_AMOUNT = r"(?:INR|Rs\.?|\u20b9)\s*([\d,]+(?:\.\d{1,2})?)"


def to_minor_units(raw: str) -> int:
    """'1,250.00' -> 125000 paise.

    Integer arithmetic on the decimal string, rather than float(x) * 100 which
    would reintroduce the exact representation error we are avoiding.
    """
    cleaned = raw.replace(",", "").strip()
    if "." in cleaned:
        whole, frac = cleaned.split(".", 1)
        frac = (frac + "00")[:2]  # pad/truncate to exactly 2 digits
    else:
        whole, frac = cleaned, "00"
    return int(whole) * 100 + int(frac)


def _parse_date(raw: str) -> Optional[date]:
    """Indian bank SMS use wildly inconsistent date formats."""
    for fmt in ("%d-%m-%y", "%d/%m/%y", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------
# Rules — ordered, most specific first
# --------------------------------------------------------------------------

_RULES: list[tuple[str, str, "re.Pattern[str]"]] = [
    (
        "upi_debit",
        "DEBIT",
        re.compile(
            _AMOUNT + r".{0,30}?debited.{0,40}?a/c\s*(?P<acct>[X\d]{4,})"
            r".{0,30}?on\s*(?P<date>[\d]{2}[-/][\w]{2,3}[-/][\d]{2,4})"
            r".{0,20}?to\s+(?P<merchant>[A-Z][A-Z0-9 &._-]{1,40}?)\s+via\s+UPI",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "card_spend",
        "DEBIT",
        re.compile(
            _AMOUNT + r"\s*spent.{0,40}?Card\s*(?P<acct>[X\d]{4,})"
            r".{0,20}?on\s*(?P<date>[\d]{2}[-/][\w]{2,3}[-/][\d]{2,4})"
            r".{0,10}?at\s+(?P<merchant>[A-Z][A-Z0-9 &._-]{1,40}?)\.",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "account_credit",
        "CREDIT",
        re.compile(
            _AMOUNT + r".{0,30}?credited.{0,30}?A/c\s*(?P<acct>[X\d]{4,})"
            r".{0,30}?on\s*(?P<date>[\d]{2}[-/][\w]{2,3}[-/][\d]{2,4})"
            r".{0,20}?by\s+(?P<merchant>[A-Z][A-Z0-9 &._-]{1,40}?)\.",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]

# Known transactional sender-ID suffixes (India uses NN-BANKID format).
_SENDER = re.compile(r"^[A-Z]{2}-(HDFCBK|ICICIB|SBIINB|AXISBK|KOTAKB|PNBSMS)$", re.I)


def parse_sms(sender: str, body: str) -> Optional[ParsedTransaction]:
    """Parse a bank SMS into a structured transaction, or None.

    Returns None rather than guessing. An unparsed message routes to the user
    clarification flow — a wrong number is far worse than an absent one.
    """
    raw_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    if not _SENDER.match(sender):
        return None  # ignore non-bank senders entirely

    for name, direction, pattern in _RULES:
        m = pattern.search(body)
        if not m:
            continue
        acct = m.group("acct")
        return ParsedTransaction(
            amount_minor=to_minor_units(m.group(1)),
            currency="INR",
            direction=direction,
            merchant=(m.group("merchant") or "").strip() or None,
            account_ref=acct[-4:] if acct else None,
            occurred_on=_parse_date(m.group("date")),
            raw_hash=raw_hash,
            confidence=0.95,
            matched_rule=name,
        )
    return None


# --------------------------------------------------------------------------
# Tests — formats captured live from the API 31 emulator
# --------------------------------------------------------------------------

CASES: list[tuple[str, str, Optional[dict]]] = [
    (
        "VM-HDFCBK",
        "Rs.1,250.00 debited from a/c XX4523 on 01-09-26 to SWIGGY via UPI Ref 528374619283. Not you? Call 18002586161",
        {"amount_minor": 125000, "direction": "DEBIT", "merchant": "SWIGGY", "account_ref": "4523"},
    ),
    (
        "AD-ICICIB",
        "INR 450.00 spent on ICICI Bank Card XX8891 on 01-Sep-26 at UBER INDIA. Avl Lmt INR 47,550.00",
        {"amount_minor": 45000, "direction": "DEBIT", "merchant": "UBER INDIA", "account_ref": "8891"},
    ),
    (
        "JD-SBIINB",
        "Dear Customer, Rs 85000.00 credited to A/c XX7734 on 01/09/26 by SALARY CREDIT. Avl Bal Rs 92,431.50",
        {"amount_minor": 8500000, "direction": "CREDIT", "merchant": "SALARY CREDIT", "account_ref": "7734"},
    ),
    # Must be ignored — promotional message from a bank sender
    ("VM-HDFCBK", "Get a personal loan up to Rs.5,00,000 at 10.5% interest. Apply now!", None),
    # Must be ignored — not a bank sender
    ("AX-SWIGGY", "Rs.1,250.00 order confirmed. Your food is on the way!", None),
]


def main() -> int:
    passed = failed = 0
    print("=" * 78)
    print("PenniLogic - deterministic SMS parser spike (ADR-003 validation)")
    print("=" * 78)

    for sender, body, expected in CASES:
        got = parse_sms(sender, body)
        label = f"{sender}: {body[:52]}..."

        if expected is None:
            ok = got is None
            detail = "correctly ignored" if ok else f"FALSE POSITIVE -> {got}"
        elif got is None:
            ok = False
            detail = "FAILED TO PARSE (would route to user clarification)"
        else:
            mismatches = [
                f"{k}: expected {v!r}, got {getattr(got, k)!r}"
                for k, v in expected.items()
                if getattr(got, k) != v
            ]
            ok = not mismatches
            detail = (
                f"{got.direction} {got.amount_minor/100:,.2f} INR "
                f"| {got.merchant} | a/c {got.account_ref} "
                f"| {got.occurred_on} | rule={got.matched_rule}"
                if ok
                else "; ".join(mismatches)
            )

        print(f"\n[{'PASS' if ok else 'FAIL'}] {label}")
        print(f"       {detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    # Guard the invariant that motivated integer minor units in the first place.
    assert to_minor_units("0.10") + to_minor_units("0.20") == to_minor_units("0.30")
    assert to_minor_units("1,250.00") == 125000
    assert to_minor_units("85000") == 8500000

    print("\n" + "=" * 78)
    print(f"RESULT: {passed} passed, {failed} failed  ({passed}/{passed + failed})")
    print("Money invariant: 0.10 + 0.20 == 0.30 exactly (integer minor units) OK")
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
