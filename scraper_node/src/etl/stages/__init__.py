"""ETL stage stubs for future implementations."""

from .scrape import stage_scrape
from .dedup import stage_dedup
from .normalize import stage_normalize
from .chunk import stage_chunk
from .embed import stage_embed
from .persist import stage_persist

__all__ = [
    "stage_scrape",
    "stage_dedup",
    "stage_normalize",
    "stage_chunk",
    "stage_embed",
    "stage_persist",
]
