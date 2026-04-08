"""Numeric vector retrieval on top of FAISS artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import Any

import numpy as np

from src.embeddings.builder import CATEGORICAL_FIELDS, FEATURE_ORDER, NUMERIC_FIELDS, loadProducts
from src.embeddings.normalize import Normalizer
from src.io import loadJsonFromFile


CAT_INDEX = {field: idx for idx, field in enumerate(CATEGORICAL_FIELDS)}
NUM_INDEX = {
    "ram_gb": 5,
    "storage_gb": 6,
    "display_in": 7,
}


@dataclass
class SearchResult:
    row_id: int
    l2_distance: float
    product: dict[str, Any] | None


class NumericVectorRetriever:
    def __init__(
        self,
        index_path: str,
        metadata_path: str,
        products_path: str | None = None,
    ):
        try:
            faiss = importlib.import_module("faiss")
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError("faiss is required for vector retrieval.") from error

        self._faiss = faiss
        index_file = Path(index_path)
        if not index_file.exists():
            raise FileNotFoundError(f"FAISS index file not found: {index_path}")
        self.index = faiss.read_index(str(index_file))

        metadata = loadJsonFromFile(metadata_path, label="Vector metadata")
        if not isinstance(metadata, dict):
            raise ValueError(f"Could not load vector metadata from {metadata_path}.")
        self.metadata = metadata

        self.validateSchema()

        self.rows: list[dict[str, Any]] = self.metadata.get("rows", [])
        self.numeric_means: dict[str, float] = self.metadata["numeric_means"]
        self.vocabularies: dict[str, dict[str, int]] = self.metadata["categorical_vocabularies"]
        self.unknown_token: str = self.metadata.get("unknown_token", "unknown")
        self.vocabularies_casefold: dict[str, dict[str, int]] = {
            field: {str(token).casefold(): idx for token, idx in vocab.items()}
            for field, vocab in self.vocabularies.items()
        }

        self.products: list[dict[str, Any]] | None = None
        if products_path and Path(products_path).exists():
            self.products = loadProducts(products_path)

    def search(self, query: dict[str, Any], top_k: int = 10, prefetch: int = 1000) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1.")
        if prefetch < 1:
            raise ValueError("prefetch must be at least 1.")

        color_filter = Normalizer.normalizeColor(query.get("color"))
        query_vector, provided_fields = self.encodeQuery(query)
        if not provided_fields and not color_filter:
            raise ValueError("At least one query field is required for retrieval.")

        if self.index.ntotal == 0:
            return []

        k_prefetch = max(top_k, min(prefetch, self.index.ntotal))
        results = self.searchCandidates(query_vector, provided_fields, color_filter, k_prefetch)

        if len(results) < top_k and k_prefetch < self.index.ntotal:
            # Fallback to a full scan when shortlist misses valid constrained candidates.
            fallback_results = self.searchCandidates(
                query_vector,
                provided_fields,
                color_filter,
                self.index.ntotal,
            )
            seen = {result.row_id for result in results}
            for result in fallback_results:
                if result.row_id not in seen:
                    results.append(result)

        results.sort(key=lambda item: (item.l2_distance))
        return results[:top_k]

    def searchCandidates(
        self,
        query_vector: np.ndarray,
        provided_fields: set[str],
        color_filter: str,
        k: int,
    ) -> list[SearchResult]:
        distances, indices = self.index.search(np.array([query_vector], dtype=np.float32), k)

        results: list[SearchResult] = []
        for l2_distance, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue

            candidate_vector = self.index.reconstruct(int(idx))
            if not self.categorieFilter(query_vector, candidate_vector, provided_fields):
                continue

            product = self.materializeProduct(int(idx))
            if not self.colorFilter(product, color_filter):
                continue

            results.append(
                SearchResult(
                    row_id=int(idx),
                    l2_distance=float(l2_distance),
                    product=product,
                )
            )

        return results

    def encodeQuery(self, query: dict[str, Any]) -> tuple[np.ndarray, set[str]]:
        normalized = self.normalizeQuery(query)

        provided_fields = {
            field for field, value in normalized.items() if value is not None and value != ""
        }

        encoded: list[float] = []
        for field in CATEGORICAL_FIELDS:
            token = normalized.get(field) or self.unknown_token
            encoded.append(float(self.resolveCategoricalToken(field, token)))

        for field in NUMERIC_FIELDS:
            value = normalized.get(field)
            if not isinstance(value, (int, float)):
                value = self.numeric_means[field]
            encoded.append(float(value))

        return np.array(encoded, dtype=np.float32), provided_fields

    def normalizeQuery(self, query: dict[str, Any]) -> dict[str, Any]:
        ram_input = query.get("ram_gb", query.get("ram"))
        storage_input = query.get("storage_gb", query.get("storage"))
        display_input = query.get("display_in", query.get("display_size"))

        return {
            "brand": self.normalizeOrNone(Normalizer.normalizeBrand(query.get("brand"))),
            "category_id": self.normalizeOrNone(
                Normalizer.normalizeCategoryId(query.get("category_id", query.get("category")))
            ),
            "os": self.normalizeOrNone(Normalizer.normalizeOs(query.get("os"))),
            "cpu_family": self.normalizeOrNone(
                Normalizer.normalizeCpuFamily(query.get("cpu_family", query.get("cpu")))
            ),
            "gpu_family": self.normalizeOrNone(
                Normalizer.normalizeGpuFamily(query.get("gpu_family", query.get("gpu")))
            ),
            "color": self.normalizeOrNone(Normalizer.normalizeColor(query.get("color"))),
            "ram_gb": self.normalizeNumericInput("ram_gb", ram_input),
            "storage_gb": self.normalizeNumericInput("storage_gb", storage_input),
            "display_in": self.normalizeNumericInput("display_in", display_input),
        }

    def resolveCategoricalToken(self, field: str, token: Any) -> int:
        field_vocab = self.vocabularies[field]
        unknown_idx = field_vocab.get(
            self.unknown_token,
            self.vocabularies_casefold[field].get(self.unknown_token.casefold(), 0),
        )

        if token is None:
            return unknown_idx

        token_text = str(token)
        if token_text in field_vocab:
            return field_vocab[token_text]

        return self.vocabularies_casefold[field].get(token_text.casefold(), unknown_idx)

    def normalizeNumericInput(self, field: str, value: Any) -> float | None:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if field == "ram_gb":
            return Normalizer.ramSizeGb(value)
        if field == "storage_gb":
            return Normalizer.storageSizeGb(value)
        if field == "display_in":
            return Normalizer.displaySizeIn(value)

        return None

    @staticmethod
    def normalizeOrNone(value: str) -> str | None:
        return value if value else None

    def colorFilter(self, product: dict[str, Any] | None, color_filter: str) -> bool:
        if not color_filter:
            return True
        if not isinstance(product, dict):
            return False

        candidate = Normalizer.normalizeColor(product.get("color"))
        if not candidate:
            return False

        return candidate == color_filter

    def categorieFilter(
        self,
        query_vector: np.ndarray,
        candidate_vector: np.ndarray,
        provided_fields: set[str],
    ) -> bool:
        for field in CATEGORICAL_FIELDS:
            if field not in provided_fields:
                continue
            idx = CAT_INDEX[field]
            if int(round(float(query_vector[idx]))) != int(round(float(candidate_vector[idx]))):
                return False
        return True

    def materializeProduct(self, row_id: int) -> dict[str, Any] | None:
        if self.products is not None and 0 <= row_id < len(self.products):
            return self.products[row_id]

        if 0 <= row_id < len(self.rows):
            return self.rows[row_id]

        return None

    def validateSchema(self) -> None:
        feature_order = self.metadata.get("feature_order")
        if feature_order != FEATURE_ORDER:
            raise ValueError("Metadata feature_order does not match retriever feature contract.")

        if int(self.metadata.get("vector_dim", 0)) != len(FEATURE_ORDER):
            raise ValueError("Metadata vector_dim does not match feature contract.")

        if self.index.d != len(FEATURE_ORDER):
            raise ValueError("FAISS index dimension is incompatible with numeric vector schema.")
