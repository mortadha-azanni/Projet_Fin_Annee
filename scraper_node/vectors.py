import time
import logging

from src import config
from src.embeddings import FEATURE_ORDER, NumericVectorBuilder, loadProducts
from src.logger import configureLogging


if __name__ == "__main__":
    configureLogging()
    logger = logging.getLogger(__name__)
    start = time.perf_counter()

    input_file = config.DEFAULT_ENRICHED_OUTPUT_FILE
    index_file = config.DEFAULT_VECTOR_INDEX_FILE
    metadata_file = config.DEFAULT_VECTOR_METADATA_FILE

    try:
        products = loadProducts(input_file)
        builder = NumericVectorBuilder()
        result = builder.build(products)
        builder.save(result, index_file, metadata_file)
    except (ValueError, OSError, ModuleNotFoundError) as error:
        logger.error("Vector generation failed: %s", error)
        raise SystemExit(1) from error
    except Exception as error:
        logger.exception("Unexpected vector generation failure")
        raise SystemExit(1) from error

    end = time.perf_counter()
    print(f"[INFO] Execution time: {end - start:.4f} seconds")
    print(f"[INFO] Total vectors generated: {result.metadata['row_count']}")
    print(f"[INFO] Vector dimension: {len(FEATURE_ORDER)}")
    print(f"[INFO] FAISS index written to: {index_file}")
    print(f"[INFO] Metadata written to: {metadata_file}")
