"""ETL pipeline skeleton for future stage-by-stage execution."""

from .contracts import PipelineContext
from .stages import (
    stage_scrape,
    stage_dedup,
    stage_normalize,
    stage_chunk,
    stage_embed,
    stage_persist,
)


def run_pipeline(context: PipelineContext) -> PipelineContext:
    """Run ETL stages in order. Each stage returns the updated context."""
    context = stage_scrape(context)
    context = stage_dedup(context)
    context = stage_normalize(context)
    context = stage_chunk(context)
    context = stage_embed(context)
    context = stage_persist(context)
    return context
