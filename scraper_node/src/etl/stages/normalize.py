"""Normalization stage implementation."""

from ..contracts import PipelineContext
from src.models import normalizeText, normalizeBrand


def _normalize_price(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = "".join(ch for ch in value if ch.isdigit() or ch in {".", ","})
        if not cleaned:
            return None
        try:
            return float(cleaned.replace(",", "."))
        except ValueError:
            return None
    return None


def stage_normalize(context: PipelineContext) -> PipelineContext:
    """Normalize and clean raw fields."""
    normalized: list[dict] = []
    invalid_count = 0

    for product in context.data:
        if not isinstance(product, dict):
            continue
        clean = dict(product)
        clean["name"] = normalizeText(clean.get("name"))
        clean["url"] = normalizeText(clean.get("url"))
        clean["image"] = normalizeText(clean.get("image"))
        clean["brand"] = normalizeBrand(clean.get("brand"))
        clean["source_category_url"] = normalizeText(clean.get("source_category_url"))
        clean["price"] = _normalize_price(clean.get("price"))

        if not clean.get("name") or not clean.get("url") or not clean.get("price"):
            invalid_count += 1

        normalized.append(clean)

    context.meta["invalid_records"] = invalid_count
    context.data = normalized
    context.progress(
        "running",
        f"Normalized {len(normalized)} items",
        len(normalized),
        {"stage": "normalize", "invalid": invalid_count},
    )
    return context
