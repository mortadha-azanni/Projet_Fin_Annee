"""Embedding and vector retrieval utilities for product catalog search."""

from src.embeddings.builder import (
	CATEGORICAL_FIELDS,
	FEATURE_ORDER,
	NUMERIC_FIELDS,
	NumericVectorBuilder,
	loadProducts,
)
from src.embeddings.retriever import NumericVectorRetriever, SearchResult

__all__ = [
	"FEATURE_ORDER",
	"CATEGORICAL_FIELDS",
	"NUMERIC_FIELDS",
	"NumericVectorBuilder",
	"NumericVectorRetriever",
	"SearchResult",
	"loadProducts",
]
