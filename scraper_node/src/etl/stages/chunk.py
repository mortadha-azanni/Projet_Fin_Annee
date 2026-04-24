"""Chunking stage stub."""

from ..contracts import PipelineContext


def stage_chunk(context: PipelineContext) -> PipelineContext:
    """Split large fields into chunks if needed."""
    return context
