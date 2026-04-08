"""Category aggregation utilities for enriched product datasets."""

from __future__ import annotations

from src.classification.catalog import CLASSIFICATION_CATALOG, getClassificationRow


def buildCategoryTableFromProducts(products: list[dict]) -> list[dict]:
    counts: dict[int, int] = {}
    for product in products:
        category_id = product.get("category_id") or 1
        if not isinstance(category_id, int):
            try:
                category_id = int(category_id)
            except (TypeError, ValueError):
                category_id = 1
        counts[category_id] = counts.get(category_id, 0) + 1

    category_table: list[dict] = []
    for category_id, count in sorted(counts.items()):
        category_table.append(
            {
                "category_id": category_id,
                "product_count": count,
            }
        )

    for category_id in sorted({1}):
        if category_id in counts:
            continue
        category_table.append({"category_id": category_id, "product_count": 0})

    return category_table


buildClassificationTableFromProducts = buildCategoryTableFromProducts
