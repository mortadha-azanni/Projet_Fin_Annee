"""Classification package compatibility helpers."""

from src.classification.catalog import CLASSIFICATION_CATALOG
from src.classification.resolver import buildCategoryTableFromProducts, buildClassificationTableFromProducts

__all__ = [
    "CLASSIFICATION_CATALOG",
    "buildCategoryTableFromProducts",
    "buildClassificationTableFromProducts",
]
