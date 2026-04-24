"""Deduplication stage implementation."""

from ..contracts import PipelineContext
from src.models import normalizeText


def _fingerprint(product: dict) -> str:
    source = normalizeText(str(product.get("source") or "")) or ""
    name = normalizeText(str(product.get("name") or "")) or ""
    url = normalizeText(str(product.get("url") or "")) or ""
    return f"{source}|{name}|{url}".lower()


def stage_dedup(context: PipelineContext) -> PipelineContext:
    """Remove duplicate entries and update context.data."""
    seen: set[str] = set()
    deduped: list[dict] = []

    for product in context.data:
        if not isinstance(product, dict):
            continue
        key = _fingerprint(product)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(product)

    context.meta["dedup_removed"] = len(context.data) - len(deduped)
    context.data = deduped
    context.progress(
        "running",
        f"Dedup removed {context.meta['dedup_removed']} items",
        len(context.data),
        {"stage": "dedup", "removed": context.meta["dedup_removed"]},
    )
    return context
