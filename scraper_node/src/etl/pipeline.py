"""ETL pipeline skeleton for future stage-by-stage execution."""

from time import perf_counter

from .contracts import PipelineContext
from .stages import (
    stage_scrape,
    stage_dedup,
    stage_normalize,
    stage_chunk,
    stage_embed,
    stage_persist,
)


def _run_stage(name: str, fn, context: PipelineContext) -> PipelineContext:
    context.stage = name
    stage_start = perf_counter()
    context.progress("running", f"Stage {name} started", len(context.data), {"stage": name})
    context = fn(context)
    elapsed = perf_counter() - stage_start
    timings = context.meta.setdefault("stage_timings", {})
    timings[name] = round(elapsed, 4)
    context.progress("running", f"Stage {name} completed", len(context.data), {"stage": name, "elapsed": elapsed})
    return context


def run_pipeline(context: PipelineContext) -> PipelineContext:
    """Run ETL stages in order. Each stage returns the updated context."""
    context = _run_stage("scrape", stage_scrape, context)
    context = _run_stage("dedup", stage_dedup, context)
    context = _run_stage("normalize", stage_normalize, context)
    context = _run_stage("chunk", stage_chunk, context)
    context = _run_stage("embed", stage_embed, context)
    context = _run_stage("persist", stage_persist, context)
    return context
