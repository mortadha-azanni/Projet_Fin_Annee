"""Scrape stage stub."""

from ..contracts import PipelineContext


def stage_scrape(context: PipelineContext) -> PipelineContext:
    """Populate context.data with raw scraped items."""
    return context
