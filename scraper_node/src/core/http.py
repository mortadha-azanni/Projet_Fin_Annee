"""HTTP session and HTML parsing utilities."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config

logger = logging.getLogger(__name__)


def buildHttpSession() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


HTTP_SESSION = buildHttpSession()


def getSoup(url: str, timeout: int = config.REQUEST_TIMEOUT_SECONDS) -> BeautifulSoup | None:
    try:
        response = HTTP_SESSION.get(url, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.Timeout as error:
        logger.error("Timeout fetching URL %s: %s", url, error)
    except requests.RequestException as error:
        logger.error("Request error fetching URL %s: %s", url, error)
    except (ValueError, TypeError) as error:
        logger.error("Error parsing response for URL %s: %s", url, error)
    except Exception:
        logger.exception("Unexpected error fetching URL %s", url)
    return None


