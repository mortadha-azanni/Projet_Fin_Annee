"""Specs extraction package."""

from src.specs.extractors import (
    extractColor,
    extractCpu,
    extractDisplay,
    extractGpu,
    extractOs,
    extractRam,
    extractStorage,
)
from src.specs.pipeline import SpecExtractor

__all__ = [
    "SpecExtractor",
    "extractCpu",
    "extractRam",
    "extractStorage",
    "extractGpu",
    "extractDisplay",
    "extractColor",
    "extractOs",
]
