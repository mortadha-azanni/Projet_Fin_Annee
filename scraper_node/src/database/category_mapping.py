import re
from typing import Any
from urllib.parse import unquote, urlparse

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from .base import Base


class CategoryMapping(Base):
    __tablename__ = "category_mapping"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(Text, nullable=False, unique=True)
    source_url = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    category = relationship("Category", back_populates="mappings")

    def __repr__(self):
        return f"<CategoryMapping(source_name='{self.source_name}', category_id={self.category_id})>"


from .category import Category
from .product import Product


def _normalizeCategoryToken(value: str | None) -> str:
    if not value:
        return ""

    token = unquote(value.strip().lower())
    token = re.sub(r"[^a-z0-9]+", "-", token)
    return re.sub(r"-+", "-", token).strip("-")


def normalizeCategoryUrl(url: str | None) -> str:
    if not url:
        return ""

    parsed = urlparse(url.strip())
    raw_path = parsed.path if parsed.scheme or parsed.netloc else url.strip()
    raw_path = raw_path.split("?", 1)[0].split("#", 1)[0]

    segments = [segment for segment in raw_path.split("/") if segment]
    normalized_segments: list[str] = []

    for index, segment in enumerate(segments):
        segment = segment.split("?", 1)[0].split("#", 1)[0]
        if index == len(segments) - 1:
            segment = segment.split(".", 1)[0]

        normalized_segment = _normalizeCategoryToken(segment)
        if normalized_segment:
            normalized_segments.append(normalized_segment)

    return "/".join(normalized_segments)


def _buildLookupKeys(url: str | None) -> list[str]:
    normalized_path = normalizeCategoryUrl(url)
    if not normalized_path:
        return []

    path_segments = [segment for segment in normalized_path.split("/") if segment]
    lookup_keys: list[str] = [normalized_path]

    if path_segments:
        lookup_keys.append(path_segments[-1])

    if len(path_segments) > 1:
        lookup_keys.append("/".join(path_segments[-2:]))

    deduplicated_keys: list[str] = []
    seen_keys: set[str] = set()
    for key in lookup_keys:
        if key and key not in seen_keys:
            seen_keys.add(key)
            deduplicated_keys.append(key)

    return deduplicated_keys


def _buildMappingKeys(mapping: CategoryMapping) -> list[str]:
    lookup_keys: list[str] = []

    for raw_value in (mapping.source_url, mapping.source_name):
        normalized_value = normalizeCategoryUrl(raw_value)
        if normalized_value:
            lookup_keys.append(normalized_value)

        normalized_token = _normalizeCategoryToken(raw_value)
        if normalized_token:
            lookup_keys.append(normalized_token)

    deduplicated_keys: list[str] = []
    seen_keys: set[str] = set()
    for key in lookup_keys:
        if key and key not in seen_keys:
            seen_keys.add(key)
            deduplicated_keys.append(key)

    return deduplicated_keys


def loadCategoryMappings(session) -> list[CategoryMapping]:
    return session.query(CategoryMapping).all()


def getCategoryIdByUrl(url: str | None, session=None, mappings: list[CategoryMapping] | None = None) -> int:
    """Return the best matching database category ID for a category URL."""

    try:
        lookup_keys = _buildLookupKeys(url)
        if not lookup_keys:
            return 1

        best_match = None
        best_score: tuple[int, int] | None = None

        category_mappings = mappings
        if category_mappings is None:
            if session is None:
                return 1
            category_mappings = loadCategoryMappings(session)

        for mapping in category_mappings:
            mapping_keys = _buildMappingKeys(mapping)
            if not mapping_keys:
                continue

            mapping_url = normalizeCategoryUrl(mapping.source_url)
            for candidate in lookup_keys:
                if candidate == mapping_url:
                    score = (0, len(candidate))
                elif candidate in mapping_keys:
                    score = (1, len(candidate))
                elif any(candidate in mapping_key or mapping_key in candidate for mapping_key in mapping_keys):
                    score = (2, len(candidate))
                else:
                    continue

                if best_score is None or score < best_score:
                    best_score = score
                    best_match = mapping

                if score[0] == 0:
                    break

            if best_score is not None and best_score[0] == 0:
                break

        if best_match:
            return best_match.category_id

        return 1
    except Exception:
        return 1


def enrichProductsWithCategoryIds(
    products: list[dict[str, Any]],
    session,
    mappings: list[CategoryMapping] | None = None,
    default_category_id: int = 1,
) -> list[dict[str, Any]]:
    enriched_products: list[dict[str, Any]] = []

    for product in products:
        if not isinstance(product, dict):
            continue

        resolved_category_id = product.get("category_id")
        if not isinstance(resolved_category_id, int) or resolved_category_id <= 0:
            resolved_category_id = getCategoryIdByUrl(product.get("source_category_url"), session, mappings)

        if not isinstance(resolved_category_id, int) or resolved_category_id <= 0:
            resolved_category_id = default_category_id

        product["category_id"] = resolved_category_id
        product.pop("source_category_url", None)
        product.pop("classification_id", None)
        product.pop("classification_source", None)
        product.pop("taxonomy_id", None)
        product.pop("taxonomy_source", None)
        product.pop("classification_category_url", None)
        product.pop("taxonomy_category_url", None)
        product.pop("classification_path", None)
        product.pop("classification_levels", None)
        product.pop("taxonomy_path", None)
        product.pop("taxonomy_levels", None)
        enriched_products.append(product)

    return enriched_products
