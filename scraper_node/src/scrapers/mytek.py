"""MyTek scraper implementation."""

from __future__ import annotations

import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from src import config
from src.core.http import HTTP_SESSION
from src.io import loadLinesFromFile, saveLinesToFile
from src.models import buildProductRecord
from src.core.control import check_scraper_state

logger = logging.getLogger(__name__)


class MyTekScraper:
    def __init__(self):
        self.apiUrl = config.MYTEK_PRODUCT_API_URL
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.http = HTTP_SESSION
        self.updateCategory()

    def updateCategory(self):
        try:
            response = self.http.get(config.MYTEK_BASE_URL, headers=self.headers, timeout=config.API_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            category_list = soup.select("div.title_normal")
            unique_urls = []
            seen_urls = set()
            for category in category_list:
                link_tag = category.find("a")
                href = link_tag.get("href") if link_tag else None
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    unique_urls.append(href)

            saved = saveLinesToFile(unique_urls, config.MYTEK_CATEGORIES_FILE, label="MyTek categories")
            if not saved:
                logger.error("Failed to persist MyTek categories file.")
                return

            logger.info("Categories updated successfully (%s unique URLs).", len(unique_urls))

        except requests.RequestException as error:
            logger.error("Request error while updating MyTek categories: %s", error)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Unexpected data error while updating MyTek categories: %s", error)
        except Exception:
            logger.exception("Unexpected runtime error while updating MyTek categories")

    def fetchProductsFromHtml(self, html):
        try:
            match = re.search(r"INITIAL_PRODUCTS_DATA\s*=\s*(\[[^\]]+\])", html)
            if not match:
                return {}

            data = json.loads(match.group(1))
            ids = [item["id"] for item in data]
            if not ids:
                return {}

            params = {"ids": ",".join(map(str, ids))}
            response = self.http.get(self.apiUrl, headers=self.headers, params=params, timeout=config.API_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            logger.error("Request error while fetching MyTek products: %s", error)
            return {}
        except json.JSONDecodeError as error:
            logger.error("Failed to parse product data: %s", error)
            return {}
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Unexpected data error while fetching MyTek products: %s", error)
            return {}
        except Exception:
            logger.exception("Unexpected runtime error while fetching MyTek products")
            return {}

    def scrapePage(self, categoryUrl="https://www.mytek.tn/", sourceCategoryUrl=None):
        try:
            response = self.http.get(categoryUrl, headers=self.headers, timeout=config.API_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()

            products_data = self.fetchProductsFromHtml(response.text)
            category_context = sourceCategoryUrl or categoryUrl
            return self.extractProducts(products_data, category_context) if products_data else []

        except requests.RequestException as error:
            logger.error("Request error while scraping MyTek page: %s", error)
            return []
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Unexpected data error while scraping MyTek page: %s", error)
            return []
        except Exception:
            logger.exception("Unexpected runtime error while scraping MyTek page")
            return []

    def scrapeCategory(self, categoryUrl, productData):
        logger.info("Scraping category: %s", categoryUrl)
        try:
            response = self.http.get(categoryUrl, headers=self.headers, timeout=config.API_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            page_index_list = soup.select("a.page-link")
            last_page_index = int(page_index_list[-2].text.strip()) if page_index_list and (page_index_list[-2].text.strip().isnumeric()) else 1

            logger.info("Total pages in category: %s", last_page_index)
            for page in range(1, last_page_index+1):
                check_scraper_state()
                products = self.scrapePage(categoryUrl + f"?p={page}", sourceCategoryUrl=categoryUrl)
                if products:
                    productData.extend(products)
                time.sleep(config.CATEGORY_SLEEP_SECONDS)

        except requests.RequestException as error:
            logger.error("Request error while scraping category %s: %s", categoryUrl, error)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Unexpected data error while scraping category %s: %s", categoryUrl, error)
        except Exception:
            logger.exception("Unexpected runtime error while scraping category %s", categoryUrl)

    def updateProducts(self, productData):
        try:
            unique_urls = loadLinesFromFile(config.MYTEK_CATEGORIES_FILE, label="MyTek categories")

            logger.info("Loaded %s unique category URLs.", len(unique_urls))
            for category_url in unique_urls:
                check_scraper_state()
                self.scrapeCategory(category_url, productData)
            logger.info("Finished updating products from MyTek categories.")
        except (AttributeError, TypeError, ValueError, OSError) as error:
            logger.error("Failed to update products from category file: %s", error)
        except Exception:
            logger.exception("Unexpected runtime error updating MyTek products")

    def extractProducts(self, productsData, sourceCategoryUrl=None):
        products = []
        try:
            for product in productsData.values():
                if not product.get("name"):
                    logger.warning("Product missing 'name' field. Skipping. Product data: %s", product)
                    continue
                products.append(
                    buildProductRecord(
                        source="mytek",
                        name=product.get("name"),
                        price=product.get("price"),
                        url=product.get("url"),
                        image=(
                            "https://mk-media.mytek.tn/media/catalog/product/cache/4635b69058c0dccf0c8109f6ac6742cc" + product.get("image", "")
                            if product.get("image")
                            else None
                        ),
                        brand=product.get("manufacturer", {}).get("label"),
                        sourceCategoryUrl=sourceCategoryUrl,
                    )
                )
            return products
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Failed to extract MyTek products: %s", error)
            return []
        except Exception:
            logger.exception("Unexpected runtime error extracting MyTek products")
            return []
