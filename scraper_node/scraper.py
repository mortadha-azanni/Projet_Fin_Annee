import time
import logging
import json
import redis
import os

from src import config
from src.database import clearProductsTable, enrichProductsWithCategoryIds, saveProductsToDB
from src.io import saveProductsToJson
from src.logger import configureLogging
from src.scrapers import MyTekScraper, TunisianetScraper
from src.database.category_mapping import loadCategoryMappings
from src.database.session import getSession, initDb
from celery_app import app as celery_app
from src.core.control import redis_client, StopScrapingException

configureLogging()
logger = logging.getLogger(__name__)

def publish_progress(state, message, count=0):
    payload = {"state": state, "message": message, "urls_scraped": count}
    redis_client.publish("scraper_progress", json.dumps(payload))

@celery_app.task(bind=True)
def runScrapers(self):
    product_data = []

    start = time.perf_counter()
    
    # Initialize control state
    redis_client.set("scraper_control_state", "running")
    publish_progress("running", "Starting scrapers (Tunisianet & MyTek)", 0)

    try:
        tunisianet_scraper = TunisianetScraper()
        tunisianet_scraper.updateProducts(product_data)
        publish_progress("running", f"Finished Tunisianet... Products found: {len(product_data)}", len(product_data))

        mytek_scraper = MyTekScraper()
        mytek_scraper.updateProducts(product_data)
        publish_progress("running", f"Finished MyTek... Total Products: {len(product_data)}", len(product_data))
        
    except StopScrapingException as e:
        logger.info("Scraping was manually aborted.")
        publish_progress("idle", f"Stopped: {e}", len(product_data))
        return  # Gracefully stop without crashing container
    except (ValueError, OSError) as error:
        logger.error("Scraping failed: %s", error)
        publish_progress("error", f"Scraping failed: {error}", len(product_data))
        raise SystemExit(1) from error
    except Exception as error:
        logger.exception("Unexpected scraper failure")
        publish_progress("error", "Unexpected scraper failure", len(product_data))
        raise SystemExit(1) from error

    end = time.perf_counter()
    print(f"[INFO] Execution time: {end - start:.4f} seconds")

    if product_data:
        saveProductsToJson(product_data, config.DEFAULT_OUTPUT_FILE)
        print(f"[INFO] Total products scraped: {len(product_data)}")
        publish_progress("running", "Refreshing products table...", len(product_data))

        try:
            initDb()
            with getSession() as session:
                category_mappings = loadCategoryMappings(session)
                product_data = enrichProductsWithCategoryIds(product_data, session, category_mappings)

            clearProductsTable(logger=logger)
            publish_progress("running", "Saving refreshed products to database...", len(product_data))
            saveProductsToDB(product_data, logger=logger)
            publish_progress("completed", "Scraping and DB injection complete", len(product_data))
            
        except Exception as e:
            logger.exception("Database persistence failed; JSON output was still saved")
            publish_progress("error", f"DB save failed: {e}", len(product_data))

if __name__ == "__main__":
    runScrapers()