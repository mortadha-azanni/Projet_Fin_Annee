"""Contracts for ETL pipeline orchestration."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """Shared pipeline context to pass state between ETL stages."""
    data: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
