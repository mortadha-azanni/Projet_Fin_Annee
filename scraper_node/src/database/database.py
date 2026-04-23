"""Shared database persistence utilities."""

from __future__ import annotations

import logging
from typing import Any

from sentence_transformers import SentenceTransformer  # type: ignore

from .category_mapping import getCategoryIdByUrl
from .category import get_category_path
from .product import Product
from .session import getSession
from src.models import build_bm25_dictionary

_EMBEDDING_MODEL: SentenceTransformer | None = None


def clearProductsTable(logger: logging.Logger | None = None) -> int:
	"""Delete all existing products to support full refresh scrape runs."""

	active_logger = logger or logging.getLogger(__name__)

	with getSession() as session:
		deleted_count = session.query(Product).delete(synchronize_session=False)
		session.commit()

	active_logger.info("Cleared %s existing products before refresh insert", deleted_count)
	return deleted_count


def _getEmbeddingModel() -> SentenceTransformer:
	global _EMBEDDING_MODEL
	if _EMBEDDING_MODEL is None:
		_EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
	return _EMBEDDING_MODEL


def _resolveCategoryId(product: dict[str, Any], session, default_category_id: int) -> int:
	category_id = product.get("category_id")
	if isinstance(category_id, int) and category_id > 0:
		return category_id

	if category_id is not None:
		try:
			parsed_category_id = int(category_id)
			if parsed_category_id > 0:
				return parsed_category_id
		except (TypeError, ValueError):
			pass

	source_category_url = product.get("source_category_url")
	if source_category_url:
		return getCategoryIdByUrl(source_category_url, session)

	return default_category_id


def saveProductsToDB(
	productData: list[dict[str, Any]],
	category_id: int = 1,
	batch_size: int = 100,
	logger: logging.Logger | None = None,
) -> tuple[int, int]:
	"""Persist products with batched commits and rollback-safe behavior."""

	if batch_size < 1:
		raise ValueError("batch_size must be at least 1")

	active_logger = logger or logging.getLogger(__name__)
	committed_count = 0
	skipped_count = 0
	pending_batch_count = 0
	model = _getEmbeddingModel()

	with getSession() as session:
		category_paths = {}
		resolved_category_ids = {}
		for product in productData:
			cat_id = _resolveCategoryId(product, session, category_id)
			resolved_category_ids[id(product)] = cat_id
			if cat_id not in category_paths:
				category_paths[cat_id] = get_category_path(cat_id, session)

		for i, product in enumerate(productData):
			try:
				if not product.get("name") or product.get("price") is None:
					active_logger.warning(
						"Skipping product %s: missing required fields (name or price)",
						i + 1,
					)
					skipped_count += 1
					continue

				cat_id = resolved_category_ids.get(id(product), category_id)
				cat_path = category_paths.get(cat_id, "")
				product["dictionary"] = build_bm25_dictionary(product, cat_path)

				db_product = Product(
					description=product.get("name", "N/A"),
					price=float(product["price"]),
					category_id=cat_id,
					urllink=product.get("url") or product.get("urlLink", ""),
					urlimg=product.get("image") or product.get("imgUrl", ""),
					embedding=model.encode(product.get("name", ""), convert_to_numpy=True).tolist(),
					dictionary=product.get("dictionary", ""),
				)
				session.add(db_product)
				pending_batch_count += 1

				if pending_batch_count >= batch_size:
					try:
						session.commit()
						committed_count += pending_batch_count
						active_logger.info(
							"Batch committed: %s products saved so far...",
							committed_count,
						)
						pending_batch_count = 0
					except Exception:
						session.rollback()
						skipped_count += pending_batch_count
						active_logger.exception(
							"Failed to commit batch ending at product index %s",
							i + 1,
						)
						pending_batch_count = 0

			except ValueError as error:
				active_logger.warning(
					"Skipping product %s: invalid data - %s",
					i + 1,
					error,
				)
				skipped_count += 1
				session.rollback()
				if pending_batch_count > 0:
					skipped_count += pending_batch_count
					pending_batch_count = 0
			except Exception:
				active_logger.exception("Error processing product %s", i + 1)
				skipped_count += 1
				session.rollback()
				if pending_batch_count > 0:
					skipped_count += pending_batch_count
					pending_batch_count = 0

		if pending_batch_count > 0:
			try:
				session.commit()
				committed_count += pending_batch_count
			except Exception:
				session.rollback()
				skipped_count += pending_batch_count
				active_logger.exception("Failed to commit final batch")

	active_logger.info(
		"Successfully saved %s products to database (Skipped: %s)",
		committed_count,
		skipped_count,
	)
	return committed_count, skipped_count