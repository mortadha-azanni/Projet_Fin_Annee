"""Embedding stage placeholder."""

from ..contracts import PipelineContext


def stage_embed(context: PipelineContext) -> PipelineContext:
    """Generate embeddings for items in context.data."""
    context.meta["embedded"] = False
    context.progress(
        "running",
        "Embedding stage is a placeholder",
        len(context.data),
        {"stage": "embed"},
    )
    return context
