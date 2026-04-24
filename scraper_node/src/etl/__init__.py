"""ETL pipeline scaffolding and stage contracts."""

from .pipeline import run_pipeline
from .contracts import PipelineContext

__all__ = [
    "PipelineContext",
    "run_pipeline",
]
