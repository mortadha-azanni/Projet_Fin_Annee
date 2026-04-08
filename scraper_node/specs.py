import time
import logging
from src import config
from src.logger import configureLogging
from src.specs import SpecExtractor

# ---------- Main Script ----------

if __name__ == "__main__":
    configureLogging()
    logger = logging.getLogger(__name__)
    start = time.perf_counter()
    
    # Initialize extractor
    extractor = SpecExtractor()
    
    # Define input and output paths
    input_file = config.DEFAULT_OUTPUT_FILE
    output_file = config.DEFAULT_ENRICHED_OUTPUT_FILE
    category_output_file = config.DEFAULT_CATEGORY_OUTPUT_FILE
    
    # Process all products
    try:
        count = extractor.processAll(input_file, output_file, classificationOutputFilePath=category_output_file)
    except (ValueError, OSError) as error:
        logger.error("Specs enrichment failed: %s", error)
        raise SystemExit(1) from error
    except Exception as error:
        logger.exception("Unexpected specs enrichment failure")
        raise SystemExit(1) from error
    
    end = time.perf_counter()
    print(f"[INFO] Execution time: {end - start:.4f} seconds")
    print(f"[INFO] Total products enriched: {count}")
