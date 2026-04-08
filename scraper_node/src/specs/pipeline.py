"""Specs enrichment pipeline for scraped products."""

from __future__ import annotations

import logging

from src.database.category_mapping import getCategoryIdByUrl, loadCategoryMappings
from src.database.session import getSession
from src.io import loadProductsFromJson, saveJsonToFile, saveProductsToJson
from src.specs.extractors import (
    extractColor,
    extractCpu,
    extractDisplay,
    extractGpu,
    extractOs,
    extractRam,
    extractStorage,
)
from src.classification import buildCategoryTableFromProducts


logger = logging.getLogger(__name__)


class SpecExtractor:
    def __init__(self):
        logger.info("SpecExtractor initialized")

    def extractSpecs(self, product):
        try:
            if not product or not product.get("name"):
                logger.warning("Product missing 'name' field. Skipping. Product data: %s", product)
                return product

            product_name = product["name"]
            specs = {
                "cpu": extractCpu(product_name),
                "ram": extractRam(product_name),
                "storage": extractStorage(product_name),
                "gpu": extractGpu(product_name),
                "display_size": extractDisplay(product_name),
                "color": extractColor(product_name),
                "os": extractOs(product_name),
            }

            product.update(specs)
            return product

        except (AttributeError, TypeError, ValueError, KeyError) as error:
            logger.error(
                "Error extracting specs for product '%s': %s",
                product.get("name", "Unknown") if isinstance(product, dict) else "Unknown",
                error,
            )
            return product

    def normalizeCategoryReference(self, product, category_mappings=None):
        category_id = product.get("category_id")
        if isinstance(category_id, int) and category_id > 0:
            product["category_id"] = category_id
        else:
            source_category_url = (
                product.get("source_category_url")
                or product.get("classification_category_url")
                or product.get("taxonomy_category_url")
            )
            if source_category_url:
                try:
                    if category_mappings is not None:
                        resolved_category_id = getCategoryIdByUrl(source_category_url, mappings=category_mappings)
                    else:
                        with getSession() as session:
                            resolved_category_id = getCategoryIdByUrl(source_category_url, session)
                except Exception:
                    resolved_category_id = 1
            else:
                resolved_category_id = 1

            product["category_id"] = resolved_category_id

        product.pop("source_category_url", None)
        product.pop("classification_id", None)
        product.pop("classification_source", None)
        product.pop("classification_path", None)
        product.pop("classification_levels", None)
        product.pop("classification_category_url", None)
        product.pop("taxonomy_id", None)
        product.pop("taxonomy_path", None)
        product.pop("taxonomy_levels", None)
        product.pop("taxonomy_source", None)
        product.pop("taxonomy_category_url", None)

        return product

    def processAll(self, inputFilePath, outputFilePath, classificationOutputFilePath=None):
        try:
            products = loadProductsFromJson(inputFilePath)
            if products:
                logger.info("Loaded %s products from %s", len(products), inputFilePath)

            if not products:
                logger.warning("No products to process.")
                return 0

            with getSession() as session:
                category_mappings = loadCategoryMappings(session)

            processed_count = 0
            for idx, product in enumerate(products, start=1):
                enriched_product = self.extractSpecs(product)
                enriched_product = self.normalizeCategoryReference(enriched_product, category_mappings)
                products[idx - 1] = enriched_product
                processed_count += 1

                if processed_count % 500 == 0:
                    logger.info("Processed %s/%s products", processed_count, len(products))

            saved = saveProductsToJson(products, outputFilePath)
            if not saved:
                logger.error("Could not save enriched products.")
                return 0

            if classificationOutputFilePath:
                category_table = buildCategoryTableFromProducts(products)
                classification_saved = saveJsonToFile(category_table, classificationOutputFilePath, label="Category table")
                if not classification_saved:
                    logger.error("Could not save category table.")
                    return 0

            logger.info("Successfully processed %s products", processed_count)
            return processed_count

        except (AttributeError, TypeError, ValueError, KeyError, OSError) as error:
            logger.error("Error processing products: %s", error)
            return 0
        except Exception:
            logger.exception("Unexpected error processing products")
            return 0
