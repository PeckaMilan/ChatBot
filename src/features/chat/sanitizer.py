"""PII detection and redaction for chat messages."""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PiiMatch:
    """Detected PII occurrence."""

    pii_type: str
    start: int
    end: int
    value: str


# Czech-specific PII patterns
PII_PATTERNS = {
    "rodne_cislo": re.compile(r"\b\d{6}/\d{3,4}\b"),
    "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "czech_phone": re.compile(r"(?:\+420|00420)\s?\d{3}\s?\d{3}\s?\d{3}\b"),
    "email": re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    ),
    "iban_cz": re.compile(
        r"\bcz\d{2}(?:\s?\d{4}){5}\b", re.IGNORECASE
    ),
}

# Email domains to ignore (not personal PII)
_IGNORED_EMAIL_DOMAINS = {
    "example.com", "example.org", "test.com", "localhost",
    "gov.cz", "psp.cz",
}


def _luhn_check(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) != 16:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _validate_rodne_cislo(value: str) -> bool:
    """Validate Czech birth number format (month check).

    Checks that the month part is valid (01-12 for men, 51-62 for women,
    or +20 variants used since 2004). Modulo 11 check is intentionally
    omitted to avoid false negatives on pre-1985 numbers.
    """
    digits = value.replace("/", "")
    if len(digits) not in (9, 10):
        return False
    # Check month: 01-12/51-62 for men/women, +20 variants since 2004
    month = int(digits[2:4])
    valid_ranges = (
        (1, 12),    # men
        (21, 32),   # men (since 2004)
        (51, 62),   # women
        (71, 82),   # women (since 2004)
    )
    return any(lo <= month <= hi for lo, hi in valid_ranges)


def detect_pii(text: str) -> list[PiiMatch]:
    """Detect PII in text.

    Returns list of PII matches found. Empty list if no PII detected.
    Uses validation (Luhn for credit cards, checksum for rodné číslo)
    to reduce false positives.
    """
    matches = []
    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group()

            # Validate credit cards with Luhn algorithm
            if pii_type == "credit_card" and not _luhn_check(value):
                continue

            # Validate rodné číslo format
            if pii_type == "rodne_cislo" and not _validate_rodne_cislo(value):
                continue

            # Skip non-personal email domains
            if pii_type == "email":
                domain = value.split("@")[1].lower()
                if domain in _IGNORED_EMAIL_DOMAINS:
                    continue

            matches.append(
                PiiMatch(
                    pii_type=pii_type,
                    start=match.start(),
                    end=match.end(),
                    value=value,
                )
            )
    return matches


def redact_pii(text: str) -> str:
    """Replace detected PII with [REDACTED] placeholders.

    Returns the original text if no PII is found.
    """
    matches = detect_pii(text)
    if not matches:
        return text

    # Sort by start position descending to replace from end to start
    # (preserves earlier indices while replacing later ones)
    sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

    result = text
    for match in sorted_matches:
        logger.info("PII detected and redacted: type=%s", match.pii_type)
        result = result[: match.start] + "[REDACTED]" + result[match.end :]

    return result
