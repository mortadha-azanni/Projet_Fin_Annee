import time
import logging
import json
from datetime import datetime, timezone

from src.logger import configureLogging
from src.etl import run_pipeline, PipelineContext
from celery_app import app as celery_app
from src.core.control import (
    SCRAPER_CONTROL_STATE_KEY,
    SCRAPER_PROGRESS_CHANNEL,
    StopScrapingException,
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
    start = time.perf_counter()
    
    # Initialize control state
    redis_client.set(SCRAPER_CONTROL_STATE_KEY, "running")
    publish_progress("running", "Starting scrapers (Tunisianet & MyTek)", 0)

    try:
        context = PipelineContext(
            data=[],
            meta={"logger": logger},
            progress_cb=publish_progress,
            error_cb=publish_error,
        )
        context = run_pipeline(context)
    except StopScrapingException as e:
        logger.info("Scraping was manually aborted.")
        publish_progress(
            "idle",
            f"Stopped: {e}",
            len(context.data) if "context" in locals() else 0,
            {
                "pipeline_health": "Stopped",
                "total_records": len(context.data) if "context" in locals() else 0,
            },
        )
        return  # Gracefully stop without crashing container
    except (ValueError, OSError) as error:
        publish_error(
            f"Scraping failed: {error}",
            len(context.data) if "context" in locals() else 0,
            exception=error,
        )
        raise SystemExit(1) from error
    except Exception as error:
        logger.exception("Unexpected scraper failure")
        publish_error(
            "Unexpected scraper failure",
            len(context.data) if "context" in locals() else 0,
            exception=error,
        )
        raise SystemExit(1) from error

    end = time.perf_counter()
    print(f"[INFO] Execution time: {end - start:.4f} seconds")

    if context.data:
        print(f"[INFO] Total products scraped: {len(context.data)}")
        publish_progress(
            "completed",
            "Scraping and DB injection complete",
            len(context.data),
            {
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "total_records": len(context.data),
                "pipeline_health": "Healthy",
                "stage_timings": context.meta.get("stage_timings", {}),
            },
        )

if __name__ == "__main__":
    runScrapers()