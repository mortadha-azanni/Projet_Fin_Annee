"""Price normalization helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def parsePrice(price_text: str | None, currency: str = "DT") -> float:
    if not price_text:
        return 0.0
    try:
        cleaned = (
            price_text.replace(currency, "")
            .replace("\u202f", "")
            .replace("\u00a0", "")
            .replace(" ", "")
            .replace(",", "")
            .replace(".", "")
            .strip()
        )
        if cleaned.isdigit():
            return float(cleaned) / 1000
    except (AttributeError, TypeError, ValueError) as error:
        logger.error("Failed to parse price '%s': %s", price_text, error)
        return 0.0
    logger.warning("Price text '%s' is not in expected format.", price_text)
    return 0.0