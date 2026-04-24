"""Chunking stage placeholder."""

from ..contracts import PipelineContext


def stage_chunk(context: PipelineContext) -> PipelineContext:
    """Split large fields into chunks if needed."""
    context.meta["chunked"] = False
    context.progress(
        "running",
        "Chunk stage is a placeholder",
        len(context.data),
        {"stage": "chunk"},
    )
    return context
