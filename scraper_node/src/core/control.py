import os
import time
import logging
import redis

logger = logging.getLogger(__name__)

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

class StopScrapingException(Exception):
    pass

def check_scraper_state():
    """
    Checks the Redis control state:
    - If 'stopped', raises StopScrapingException to abort immediately.
    - If 'paused', loops and sleeps until state changes to 'running' or 'stopped'.
    """
    while True:
        state = redis_client.get("scraper_control_state") or "running"
        if state == "stopped":
            logger.info("Scraping stopped by admin control.")
            raise StopScrapingException("Scraping was stopped manually.")
        elif state == "paused":
            logger.debug("Scraping paused. Waiting to resume...")
            time.sleep(2)
        else:
            # running
            break
