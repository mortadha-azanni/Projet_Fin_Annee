"""Contracts for ETL pipeline orchestration."""

from dataclasses import dataclass, field
from typing import Any, Callable


ProgressCallback = Callable[[str, str, int, dict[str, Any] | None], None]
ErrorCallback = Callable[[str, int, Exception | None], None]


@dataclass
class PipelineContext:
    """Shared pipeline context to pass state between ETL stages."""
    data: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    stage: str | None = None
    progress_cb: ProgressCallback | None = None
    error_cb: ErrorCallback | None = None

    def progress(self, state: str, message: str, count: int, meta: dict[str, Any] | None = None) -> None:
        if self.progress_cb:
            self.progress_cb(state, message, count, meta)

    def error(self, message: str, count: int, exception: Exception | None = None) -> None:
        if self.error_cb:
            self.error_cb(message, count, exception)
