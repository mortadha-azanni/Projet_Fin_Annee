"""Numeric vector builder for product retrieval artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from src.embeddings.normalize import Normalizer
from src.io import loadJsonFromFile


FEATURE_ORDER = [
    "brand",
    "category_id",
    "os",
    "cpu_family",
    "gpu_family",
    "ram_gb",
    "storage_gb",
    "display_in",
]

CATEGORICAL_FIELDS = ["brand", "category_id", "os", "cpu_family", "gpu_family"]
NUMERIC_FIELDS = ["ram_gb", "storage_gb", "display_in"]
UNKNOWN_TOKEN = "unknown"
SCHEMA_VERSION = "numeric-vector-v1"
logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    matrix: np.ndarray
    metadata: dict[str, Any]


class NumericVectorBuilder:
    def __init__(self, unknown_token: str = UNKNOWN_TOKEN):
        self.unknown_token = unknown_token

    def build(self, products: list[dict[str, Any]]) -> BuildResult:
        normalized_rows = [self.normalizeProduct(product) for product in products]

        numeric_means = self.computeNumericMeans(normalized_rows)
        vocabularies = self.buildCategoricalVocabularies(normalized_rows)

        vectors: list[list[float]] = []
        row_mapping: list[dict[str, Any]] = []

        for row_id, (product, normalized_row) in enumerate(zip(products, normalized_rows)):
            vector = self.encodeRow(normalized_row, vocabularies, numeric_means)
            vectors.append(vector)
            row_mapping.append(
                {
                    "row_id": row_id,
                    "url": product.get("url"),
                    "name": product.get("name"),
                    "source": product.get("source"),
                    "category_id": product.get("category_id"),
                }
            )

        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.size and not np.isfinite(matrix).all():
            raise ValueError("Encoded matrix contains NaN or infinite values.")

        metadata: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "feature_order": FEATURE_ORDER,
            "categorical_fields": CATEGORICAL_FIELDS,
            "numeric_fields": NUMERIC_FIELDS,
            "vector_dim": len(FEATURE_ORDER),
            "dtype": "float32",
            "unknown_token": self.unknown_token,
            "categorical_vocabularies": vocabularies,
            "numeric_means": numeric_means,
            "row_count": int(matrix.shape[0]) if matrix.ndim == 2 else 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rows": row_mapping,
        }

        return BuildResult(matrix=matrix, metadata=metadata)

    def save(self, result: BuildResult, index_path: str, metadata_path: str) -> None:
        try:
            faiss = importlib.import_module("faiss")
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError("faiss is required to save vector indices.") from error

        index = faiss.IndexFlatL2(result.metadata["vector_dim"])
        if result.matrix.size:
            index.add(result.matrix)

        result.metadata["index_type"] = "IndexFlatL2"
        result.metadata["index_ntotal"] = int(index.ntotal)

        index_path_obj = Path(index_path)
        metadata_path_obj = Path(metadata_path)
        index_path_obj.parent.mkdir(parents=True, exist_ok=True)
        metadata_path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            faiss.write_index(index, str(index_path_obj))
            with open(metadata_path_obj, "w", encoding="utf-8") as file:
                json.dump(result.metadata, file, indent=2, ensure_ascii=False)
        except (OSError, ValueError, TypeError) as error:
            logger.error("Failed to persist vector artifacts: %s", error)
            raise

    def normalizeProduct(self, product: dict[str, Any]) -> dict[str, Any]:
        return {
            "brand": self.getTokenValue(Normalizer.normalizeBrand(product.get("brand"))),
            "category_id": self.getTokenValue(
                Normalizer.normalizeCategoryId(product.get("category_id"))
            ),
            "os": self.getTokenValue(Normalizer.normalizeOs(product.get("os"))),
            "cpu_family": self.getTokenValue(Normalizer.normalizeCpuFamily(product.get("cpu"))),
            "gpu_family": self.getTokenValue(Normalizer.normalizeGpuFamily(product.get("gpu"))),
            "ram_gb": Normalizer.ramSizeGb(product.get("ram")),
            "storage_gb": Normalizer.storageSizeGb(product.get("storage")),
            "display_in": Normalizer.displaySizeIn(product.get("display_size")),
        }

    def getTokenValue(self, value: str) -> str:
        return value if value else self.unknown_token

    def computeNumericMeans(self, rows: list[dict[str, Any]]) -> dict[str, float]:
        means: dict[str, float] = {}
        for field in NUMERIC_FIELDS:
            values = [float(row[field]) for row in rows if isinstance(row.get(field), (int, float))]
            means[field] = float(np.mean(values)) if values else 0.0
        return means

    def buildCategoricalVocabularies(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        vocabularies: dict[str, dict[str, int]] = {}
        for field in CATEGORICAL_FIELDS:
            tokens = {self.getTokenValue(str(row.get(field, self.unknown_token))) for row in rows}
            sorted_tokens = sorted(token for token in tokens if token != self.unknown_token)
            ordered_tokens = [self.unknown_token] + sorted_tokens
            vocabularies[field] = {token: idx for idx, token in enumerate(ordered_tokens)}
        return vocabularies

    def encodeRow(
        self,
        normalized_row: dict[str, Any],
        vocabularies: dict[str, dict[str, int]],
        numeric_means: dict[str, float],
    ) -> list[float]:
        vector: list[float] = []

        for field in CATEGORICAL_FIELDS:
            token = self.getTokenValue(str(normalized_row.get(field, self.unknown_token)))
            encoded = vocabularies[field].get(token, vocabularies[field][self.unknown_token])
            vector.append(float(encoded))

        for field in NUMERIC_FIELDS:
            value = normalized_row.get(field)
            if not isinstance(value, (int, float)):
                value = numeric_means[field]
            vector.append(float(value))

        return vector


def loadProducts(input_path: str) -> list[dict[str, Any]]:
    data = loadJsonFromFile(input_path, label="Products")
    if not isinstance(data, list):
        raise ValueError("Input products JSON must be a list.")
    return data
