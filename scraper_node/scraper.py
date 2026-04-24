import time
import logging
import json
from datetime import datetime, timezone

from src import config
from src.database import clearProductsTable, enrichProductsWithCategoryIds, saveProductsToDB
from src.io import saveProductsToJson
from src.logger import configureLogging
from src.scrapers import MyTekScraper, TunisianetScraper
from src.database.category_mapping import loadCategoryMappings
from src.database.session import getSession, initDb
from celery_app import app as celery_app
from src.core.control import (
    SCRAPER_CONTROL_STATE_KEY,
    SCRAPER_PROGRESS_CHANNEL,
    StopScrapingException,
    check_scraper_state,
    redis_client,
)

configureLogging()
logger = logging.getLogger(__name__)

def publish_progress(state, message, count=0, meta=None):
    payload = {
        "state": state,
        "message": message,
        "urls_scraped": count,
    }
    if meta:
        payload.update(meta)
    redis_client.publish(SCRAPER_PROGRESS_CHANNEL, json.dumps(payload))


def publish_error(message, count, exception=None):
    if exception:
        logger.error(message, exc_info=exception)
    publish_progress(
        "error",
        message,
        count,
        {
            "pipeline_health": "Error",
            "total_records": count,
        },
    )

@celery_app.task(bind=True)
def runScrapers(self):
    product_data = []

    start = time.perf_counter()
    
    # Initialize control state
    redis_client.set(SCRAPER_CONTROL_STATE_KEY, "running")
    publish_progress("running", "Starting scrapers (Tunisianet & MyTek)", 0)

    try:
        check_scraper_state()
        tunisianet_scraper = TunisianetScraper()
        tunisianet_scraper.updateProducts(product_data)
        publish_progress("running", f"Finished Tunisianet... Products found: {len(product_data)}", len(product_data))

        check_scraper_state()
        mytek_scraper = MyTekScraper()
        mytek_scraper.updateProducts(product_data)
        publish_progress("running", f"Finished MyTek... Total Products: {len(product_data)}", len(product_data))
        
    except StopScrapingException as e:
        logger.info("Scraping was manually aborted.")
        publish_progress(
            "idle",
            f"Stopped: {e}",
            len(product_data),
            {
                "pipeline_health": "Stopped",
                "total_records": len(product_data),
            },
        )
        return  # Gracefully stop without crashing container
    except (ValueError, OSError) as error:
        publish_error(f"Scraping failed: {error}", len(product_data), exception=error)
        raise SystemExit(1) from error
    except Exception as error:
        logger.exception("Unexpected scraper failure")
        publish_error("Unexpected scraper failure", len(product_data), exception=error)
        raise SystemExit(1) from error

    end = time.perf_counter()
    print(f"[INFO] Execution time: {end - start:.4f} seconds")

    if product_data:
        saveProductsToJson(product_data, config.DEFAULT_OUTPUT_FILE)
        print(f"[INFO] Total products scraped: {len(product_data)}")
        check_scraper_state()
        publish_progress("running", "Saving products to database...", len(product_data))

        try:
            initDb()
            with getSession() as session:
                category_mappings = loadCategoryMappings(session)
                product_data = enrichProductsWithCategoryIds(product_data, session, category_mappings)

            clearProductsTable(logger=logger)
            publish_progress("running", "Saving refreshed products to database...", len(product_data))
            saveProductsToDB(product_data, logger=logger)
            publish_progress(
                "completed",
                "Scraping and DB injection complete",
                len(product_data),
                {
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "total_records": len(product_data),
                    "pipeline_health": "Healthy",
                },
            )
            
        except Exception as e:
            logger.exception("Database persistence failed; JSON output was still saved")
            publish_error(f"DB save failed: {e}", len(product_data), exception=e)

if __name__ == "__main__":
    runScrapers()