"""Persistence stage stub."""

from ..contracts import PipelineContext


def stage_persist(context: PipelineContext) -> PipelineContext:
    """Persist processed items to storage."""
    return context
