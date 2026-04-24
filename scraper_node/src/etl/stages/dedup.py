"""Deduplication stage stub."""

from ..contracts import PipelineContext


def stage_dedup(context: PipelineContext) -> PipelineContext:
    """Remove duplicate entries and update context.data."""
    return context
