import argparse
import json
import logging
import sys

from src import config
from src.embeddings.retriever import NumericVectorRetriever
from src.logger import configureLogging


def main() -> None:
    configureLogging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Search products using numeric FAISS vectors")
    parser.add_argument("--brand", type=str, default=None)
    parser.add_argument("--classification", type=str, default=None)
    parser.add_argument("--os", type=str, default=None)
    parser.add_argument("--cpu", type=str, default=None)
    parser.add_argument("--gpu", type=str, default=None)
    parser.add_argument("--color", type=str, default=None)
    parser.add_argument("--ram-gb", type=float, default=None)
    parser.add_argument("--storage-gb", type=float, default=None)
    parser.add_argument("--display-in", type=float, default=None)
    parser.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args()

    query = {
        "brand": args.brand,
        "classification": args.classification,
        "os": args.os,
        "cpu": args.cpu,
        "gpu": args.gpu,
        "color": args.color,
        "ram_gb": args.ram_gb,
        "storage_gb": args.storage_gb,
        "display_in": args.display_in,
    }

    try:
        retriever = NumericVectorRetriever(
            index_path=config.DEFAULT_VECTOR_INDEX_FILE,
            metadata_path=config.DEFAULT_VECTOR_METADATA_FILE,
            products_path=config.DEFAULT_ENRICHED_OUTPUT_FILE,
        )

        results = retriever.search(query=query, top_k=max(args.top_k, 1), prefetch=500)
    except (ValueError, OSError, ModuleNotFoundError) as error:
        logger.error("Retrieval failed: %s", error)
        raise SystemExit(1) from error
    except Exception as error:
        logger.exception("Unexpected failure during retrieval")
        raise SystemExit(1) from error

    payload = [
        {
            "row_id": result.row_id,
            "l2_distance": result.l2_distance,
            "product": result.product,
        }
        for result in results
    ]

    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
